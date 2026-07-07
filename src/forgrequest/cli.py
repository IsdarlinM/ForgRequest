#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forgrequest.py - Advanced HTTP client for authorized testing.
Signature: immroa
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    print("[!] Missing dependency: requests", file=sys.stderr)
    print("    Install with: python -m pip install requests", file=sys.stderr)
    raise SystemExit(2)

VERSION = "1.4.0"


def find_default_config_file() -> str:
    """Return the most useful default config path for standalone and src layouts."""
    env_config = os.getenv("FORGREQUEST_CONFIG")
    candidates = []
    if env_config:
        candidates.append(Path(env_config).expanduser())
    candidates.extend(
        [
            Path.cwd() / "forgrequest.config",
            Path(__file__).resolve().parent / "forgrequest.config",
            Path(__file__).resolve().parents[2] / "config" / "forgrequest.config" if len(Path(__file__).resolve().parents) >= 3 else Path("forgrequest.config"),
            Path.home() / ".config" / "forgrequest" / "forgrequest.config",
        ]
    )
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    return "forgrequest.config"


DEFAULT_CONFIG_FILE = find_default_config_file()
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "proxy-authorization",
}
COOKIE_ATTRS = {"path", "domain", "expires", "max-age", "samesite", "secure", "httponly"}
COLOR_MODES = {"auto", "always", "never"}

# Soft Kali-inspired ANSI palette: cyan/blue/violet/green tones, no harsh colors.
ANSI_STYLES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[38;5;80m",
    "blue": "\033[38;5;75m",
    "violet": "\033[38;5;141m",
    "green": "\033[38;5;114m",
    "yellow": "\033[38;5;186m",
    "red": "\033[38;5;174m",
    "gray": "\033[38;5;245m",
}

LOGO = rf"""
        ███████╗ ██████╗ ██████╗  ██████╗ 
        ██╔════╝██╔═══██╗██╔══██╗██╔════╝ 
        █████╗  ██║   ██║██████╔╝██║  ███╗
        ██╔══╝  ██║   ██║██╔══██╗██║   ██║
        ██║     ╚██████╔╝██║  ██║╚██████╔╝
        ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ 

        ██████╗ ███████╗ ██████╗ ██╗   ██╗███████╗███████╗████████╗
        ██╔══██╗██╔════╝██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝
        ██████╔╝█████╗  ██║   ██║██║   ██║█████╗  ███████╗   ██║   
        ██╔══██╗██╔══╝  ██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║   
        ██║  ██║███████╗╚██████╔╝╚██████╔╝███████╗███████║   ██║   
        ╚═╝  ╚═╝╚══════╝ ╚══▀▀═╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝   

             Forgery HTTP Request v{VERSION}  ::  signature: immroa
"""

DEFAULTS: dict[str, Any] = {
    "method": "GET",
    "user_agent": f"ForgeryHTTP/{VERSION} (immroa)",
    "headers": {},
    "cookies": {},
    "headers_file": "",
    "cookies_file": "",
    "payload": "",
    "payload_file": "",
    "timeout": 30.0,
    "follow_redirects": True,
    "verify_tls": True,
    "include_response_headers": False,
    "show_request": False,
    "dry_run": False,
    "output": "",
    "proxy": "",
    "pretty_json": True,
    "show_logo": True,
    "color": "auto",
    "interactive": False,
}

SAMPLE_CONFIG = f'''# forgrequest.config
# INI/.config format read with configparser from the Python standard library.
# The URL must NOT be stored here. Always pass it as an argument: --url https://example.com

[request]
method = GET
user_agent = ForgeryHTTP/{VERSION} (immroa)
timeout = 30
follow_redirects = true
verify_tls = true
include_response_headers = false
show_request = false
dry_run = false
output =
proxy =
pretty_json = true
show_logo = true
color = auto
interactive = false

# Optional defaults for loading values from files.
# If you also pass CLI arguments, CLI values take priority.
headers_file =
cookies_file =
payload_file =

# Default payload. It may be one line or multiline if continuation lines are indented.
payload =

[headers]
Accept = */*

[cookies]
# session = value
'''


@dataclass
class RequestConfig:
    method: str = DEFAULTS["method"]
    url: str = ""
    user_agent: str = DEFAULTS["user_agent"]
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    payload: bytes | str | None = DEFAULTS["payload"]
    timeout: float = DEFAULTS["timeout"]
    follow_redirects: bool = DEFAULTS["follow_redirects"]
    verify_tls: bool = DEFAULTS["verify_tls"]
    include_response_headers: bool = DEFAULTS["include_response_headers"]
    show_request: bool = DEFAULTS["show_request"]
    dry_run: bool = DEFAULTS["dry_run"]
    output: str = DEFAULTS["output"]
    proxy: str = DEFAULTS["proxy"]
    pretty_json: bool = DEFAULTS["pretty_json"]
    show_logo: bool = DEFAULTS["show_logo"]
    color_mode: str = DEFAULTS["color"]
    color_enabled: bool = False


def enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on modern Windows consoles when possible."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        # If this fails, do not block the tool; escapes will only show when color is forced.
        return


def normalize_color_mode(value: Any) -> str:
    val = str(value or "auto").strip().lower()
    aliases = {
        "1": "always",
        "true": "always",
        "yes": "always",
        "y": "always",
        "on": "always",
        "si": "always",
        "0": "never",
        "false": "never",
        "no": "never",
        "n": "never",
        "off": "never",
        "none": "never",
    }
    val = aliases.get(val, val)
    if val not in COLOR_MODES:
        die(f"Invalid color mode: {value!r}. Use auto, always, or never.")
    return val


def should_use_color(mode: str) -> bool:
    mode = normalize_color_mode(mode)
    if mode == "never":
        return False
    if mode == "always":
        enable_windows_ansi()
        return True
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        enable_windows_ansi()
        return True
    enabled = sys.stdout.isatty()
    if enabled:
        enable_windows_ansi()
    return enabled


def style(text: Any, *names: str, enabled: bool = False) -> str:
    value = str(text)
    if not enabled:
        return value
    codes = "".join(ANSI_STYLES[name] for name in names if name in ANSI_STYLES)
    if not codes:
        return value
    return f"{codes}{value}{ANSI_STYLES['reset']}"


def render_logo(color_enabled: bool) -> str:
    if not color_enabled:
        return LOGO
    palette = ["cyan", "blue", "violet", "blue", "cyan", "green"]
    rendered: list[str] = []
    color_index = 0
    for line in LOGO.splitlines():
        if not line.strip():
            rendered.append(line)
            continue
        if "Forgery HTTP Request" in line:
            rendered.append(style(line, "green", "bold", enabled=True))
            continue
        rendered.append(style(line, palette[color_index % len(palette)], enabled=True))
        color_index += 1
    return "\n".join(rendered)


def die(message: str, code: int = 1) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(code)


def read_text_file(path: str | Path) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        die(f"File not found: {p}")
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1")
    except OSError as exc:
        die(f"Could not read {p}: {exc}")


def read_bytes_file(path: str | Path) -> bytes:
    p = Path(path).expanduser()
    if not p.is_file():
        die(f"File not found: {p}")
    try:
        return p.read_bytes()
    except OSError as exc:
        die(f"Could not read {p}: {exc}")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    val = str(value).strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    die(f"Invalid boolean value: {value!r}")


def split_semicolon_aware(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\r", "").split(";") if part.strip()]


HEADER_NAME_RE = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
HEADER_SEPARATOR_RE = re.compile(rf";(?=\s*{HEADER_NAME_RE}\s*:)")


def split_header_candidates(line: str) -> list[str]:
    """
    Split compact headers only when the semicolon appears to separate another header.

    Important: legitimate values such as User-Agent may contain ';', for example:
    Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...

    This is why line.split(';') is NOT used for headers. Splitting happens only for cases like:
    "Accept: */*; X-Test: 1"
    """
    return [part.strip() for part in HEADER_SEPARATOR_RE.split(line.replace("\r", "")) if part.strip()]


def parse_headers(raw: str) -> dict[str, str]:
    """
    Supported formats:
      - JSON object: {"X-Test":"1"}
      - Lines: Header: value
      - String: "Header: value; Header2: value2"
      - curl fragments: -H 'Header: value'

    Semicolons inside values do not break the header. Valid example:
      User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
    """
    headers: dict[str, str] = {}
    text = raw.strip()
    if not text:
        return headers

    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            die(f"Invalid headers JSON: {exc}")
        if not isinstance(obj, dict):
            die('Headers JSON must be an object: {"Header": "value"}')
        return {str(k): str(v) for k, v in obj.items()}

    # Allow pasted curl fragments: -H 'A: 1' -H 'B: 2'
    text = re.sub(r"(?:^|\s)-H\s+", "\n", text)
    candidates: list[str] = []
    for line in text.splitlines():
        line = line.strip().strip("'\"")
        if not line:
            continue
        candidates.extend(split_header_candidates(line))

    for item in candidates:
        item = item.strip().strip("'\"")
        if not item:
            continue
        if ":" not in item:
            die(f"Invalid header, use 'Name: value': {item!r}")
        name, value = item.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            die(f"Header with empty name: {item!r}")
        if not re.fullmatch(HEADER_NAME_RE, name):
            die(f"Invalid header name: {name!r}")
        headers[name] = value
    return headers


def parse_netscape_cookie_line(line: str) -> Optional[tuple[str, str]]:
    if not line or line.startswith("#"):
        return None
    parts = line.split("\t")
    # domain flag path secure expires name value
    if len(parts) >= 7:
        return parts[5].strip(), parts[6].strip()
    return None


def parse_cookies(raw: str) -> dict[str, str]:
    """
    Supported formats:
      - Cookie header: "a=b; c=d"
      - JSON object: {"a":"b"}
      - Lines: a=b
      - Set-Cookie lines: Set-Cookie: a=b; Path=/; HttpOnly
      - Netscape cookie file
    """
    cookies: dict[str, str] = {}
    text = raw.strip()
    if not text:
        return cookies

    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            die(f"Invalid cookies JSON: {exc}")
        if not isinstance(obj, dict):
            die('Cookies JSON must be an object: {"name": "value"}')
        return {str(k): str(v) for k, v in obj.items()}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        ns = parse_netscape_cookie_line(line)
        if ns:
            name, value = ns
            if name:
                cookies[name] = value
            continue

        if line.lower().startswith("cookie:"):
            line = line.split(":", 1)[1].strip()
        elif line.lower().startswith("set-cookie:"):
            line = line.split(":", 1)[1].strip()

        for part in split_semicolon_aware(line):
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name or name.lower() in COOKIE_ATTRS:
                continue
            cookies[name] = value
    return cookies


def merge_dicts(*dicts: Optional[dict[str, Any]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for dct in dicts:
        if not dct:
            continue
        for k, v in dct.items():
            if k is None:
                continue
            merged[str(k)] = str(v)
    return merged


def redact(mapping: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for k, v in mapping.items():
        redacted[k] = "<redacted>" if k.lower() in SENSITIVE_KEYS else v
    return redacted


def has_header(headers: dict[str, str], name: str) -> bool:
    wanted = name.lower()
    return any(key.lower() == wanted for key in headers)


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        die("Invalid URL. It must start with http:// or https://")
    if not parsed.netloc:
        die("Invalid URL. Missing host.")


def new_config_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    # Preserve header case, e.g. Content-Type, X-Test, etc.
    parser.optionxform = str
    return parser


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        return {}
    if p.suffix.lower() != ".config":
        die("The configuration file must use the .config extension, for example: forgrequest.config")

    parser = new_config_parser()
    try:
        read_files = parser.read(p, encoding="utf-8")
    except configparser.Error as exc:
        die(f"Invalid .config file at {p}: {exc}")
    except OSError as exc:
        die(f"Could not read config {p}: {exc}")

    if not read_files:
        die(f"Could not load config: {p}")

    if parser.has_option("request", "url") and parser.get("request", "url").strip():
        die("For operational safety, the URL must not be stored in the configuration file. Use --url.")

    cfg: dict[str, Any] = {}
    if parser.has_section("request"):
        cfg.update({k: v for k, v in parser.items("request")})
    if parser.has_section("headers"):
        cfg["headers"] = {k: v for k, v in parser.items("headers")}
    if parser.has_section("cookies"):
        cfg["cookies"] = {k: v for k, v in parser.items("cookies")}
    return cfg


def write_sample_config(path: str | Path) -> None:
    p = Path(path).expanduser()
    if p.suffix.lower() != ".config":
        die("Use a path with the .config extension, for example: forgrequest.config")
    if p.exists():
        die(f"Already exists: {p}. I will not overwrite it.")
    try:
        p.write_text(SAMPLE_CONFIG, encoding="utf-8")
    except OSError as exc:
        die(f"Could not create {p}: {exc}")
    print(f"[+] Config created: {p}")


def get_config_str(cfg: dict[str, Any], key: str, default: str = "") -> str:
    value = cfg.get(key, default)
    return default if value is None else str(value)


def collect_argument_chunks(value: Optional[list[str] | str]) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if item]


def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        die("Interactive input cancelled")


def prompt_text(label: str, default: str = "", required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = safe_input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("[!] Required value")


def prompt_yes_no(label: str, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        value = safe_input(f"{label} [{default_text}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes", "1", "true"}:
            return True
        if value in {"n", "no", "0", "false"}:
            return False
        print("[!] Answer y/n")


def prompt_float(label: str, default: float) -> float:
    while True:
        value = safe_input(f"{label} [{default}]: ").strip()
        if not value:
            return default
        try:
            result = float(value)
        except ValueError:
            print("[!] Must be a number")
            continue
        if result <= 0:
            print("[!] Must be greater than 0")
            continue
        return result


def interactive_collect(args: argparse.Namespace, cfg_file: dict[str, Any]) -> argparse.Namespace:
    cfg = {**DEFAULTS, **cfg_file}
    print("\n[Interactive mode] Press Enter to accept the default value.")

    if not args.url:
        args.url = prompt_text("Target URL", required=True)
    validate_url(args.url)

    method_default = args.method or get_config_str(cfg, "method", "GET")
    args.method = prompt_text("HTTP method", method_default).upper()
    if args.method not in ALLOWED_METHODS:
        die(f"Unsupported method: {args.method}. Allowed: {', '.join(sorted(ALLOWED_METHODS))}")

    ua_default = args.user_agent or get_config_str(cfg, "user_agent", DEFAULTS["user_agent"])
    args.user_agent = prompt_text("User-Agent", ua_default)

    print("\n[Headers] Enter headers as 'Name: value'. Leave empty to finish.")
    header_chunks = collect_argument_chunks(args.headers)
    while True:
        item = safe_input("Header: ").strip()
        if not item:
            break
        header_chunks.append(item)
    args.headers = header_chunks or args.headers

    header_file_default = args.headers_file or get_config_str(cfg, "headers_file")
    header_file = prompt_text("Headers from file", header_file_default)
    if header_file:
        args.headers_file = header_file

    print("\n[Cookies] Enter cookies as 'a=b; c=d' or 'name=value'. Leave empty to finish.")
    cookie_chunks = collect_argument_chunks(args.cookies)
    while True:
        item = safe_input("Cookies: ").strip()
        if not item:
            break
        cookie_chunks.append(item)
    args.cookies = cookie_chunks or args.cookies

    cookie_file_default = args.cookies_file or get_config_str(cfg, "cookies_file")
    cookie_file = prompt_text("Cookies from file", cookie_file_default)
    if cookie_file:
        args.cookies_file = cookie_file

    payload_file_default = args.payload_file or get_config_str(cfg, "payload_file")
    if payload_file_default:
        args.payload_file = prompt_text("Payload from file", payload_file_default)
    else:
        payload_choice = prompt_text("Payload: [enter]=unchanged, s=string, f=file", "").lower()
        if payload_choice in {"s", "string"}:
            args.payload = prompt_text("Payload/body", args.payload or get_config_str(cfg, "payload"))
        elif payload_choice in {"f", "file"}:
            args.payload_file = prompt_text("Payload file path", required=True)

    timeout_default = args.timeout if args.timeout is not None else float(get_config_str(cfg, "timeout", str(DEFAULTS["timeout"])))
    args.timeout = prompt_float("Timeout in seconds", timeout_default)

    proxy_default = args.proxy or get_config_str(cfg, "proxy")
    proxy = prompt_text("Proxy HTTP/HTTPS", proxy_default)
    if proxy:
        args.proxy = proxy

    overrides: dict[str, bool] = {}
    overrides["follow_redirects"] = prompt_yes_no("Follow redirects", parse_bool(cfg.get("follow_redirects", True)) and not args.no_redirects)
    overrides["verify_tls"] = prompt_yes_no("Verify TLS", parse_bool(cfg.get("verify_tls", True)) and not args.insecure)
    overrides["include_response_headers"] = prompt_yes_no("Show response headers", bool(args.include) or parse_bool(cfg.get("include_response_headers", False)))
    overrides["show_request"] = prompt_yes_no("Show prepared request", bool(args.show_request) or parse_bool(cfg.get("show_request", False)))
    overrides["dry_run"] = prompt_yes_no("Dry-run without sending", bool(args.dry_run) or parse_bool(cfg.get("dry_run", False)))
    overrides["pretty_json"] = prompt_yes_no("Pretty-print JSON", (not args.raw) and parse_bool(cfg.get("pretty_json", True)))
    overrides["show_logo"] = prompt_yes_no("Show logo", (not args.no_logo) and parse_bool(cfg.get("show_logo", True)))

    color_default = normalize_color_mode(
        getattr(args, "color", None)
        or ("never" if getattr(args, "no_color", False) else cfg.get("color", DEFAULTS["color"]))
    )
    color_mode = prompt_text("Color ANSI (auto/always/never)", color_default).lower()
    setattr(args, "_interactive_color_mode", normalize_color_mode(color_mode))
    setattr(args, "_interactive_overrides", overrides)

    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgrequest.py",
        description="Forgery HTTP Request: HTTP client for authorized testing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("-u", "--url", required=False, help="Target URL. Required unless --init-config is used.")
    parser.add_argument("-X", "--method", help="HTTP method: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, TRACE.")
    parser.add_argument("-A", "--user-agent", dest="user_agent", help="Custom User-Agent.")

    parser.add_argument("-H", "--headers", action="append", help="Headers as string. Repeatable. Example: -H 'X-Test: 1'")
    parser.add_argument("--headers-file", help="Headers file: JSON, lines like 'Header: value', or curl -H fragments.")

    parser.add_argument("-b", "--cookies", action="append", help="Cookies as string. Repeatable. Example: -b 'a=b; c=d'")
    parser.add_argument("--cookies-file", help="Cookies file: Netscape, JSON, Cookie header, or name=value lines.")

    parser.add_argument("-d", "--payload", help="Payload/body as string.")
    parser.add_argument("--payload-file", help="File to send as body bytes.")

    parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_FILE, help="Default .config configuration file.")
    parser.add_argument("--init-config", action="store_true", help="Create a base configuration file and exit.")

    parser.add_argument("--timeout", type=float, help="Approximate total request timeout in seconds.")
    parser.add_argument("--no-redirects", action="store_true", help="Do not follow HTTP redirects.")
    parser.add_argument("--insecure", action="store_true", help="Do not verify TLS. Use only in lab environments.")
    parser.add_argument("--include", action="store_true", help="Show response headers along with the body.")
    parser.add_argument("--show-request", action="store_true", help="Show the prepared request with secrets redacted.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and show the request without sending it.")
    parser.add_argument("-o", "--output", help="Save response body to file.")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy. Example: http://127.0.0.1:8080")
    parser.add_argument("--raw", action="store_true", help="Do not pretty-print JSON responses.")
    parser.add_argument("--no-logo", action="store_true", help="Do not show the logo.")
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument(
        "--color",
        nargs="?",
        const="always",
        choices=sorted(COLOR_MODES),
        help="ANSI color mode: auto, always, or never. Using --color without a value equals always.",
    )
    color_group.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode to build the request step by step.")

    return parser


def resolve_config(args: argparse.Namespace) -> RequestConfig:
    cfg_file = load_config(args.config)
    cfg = {**DEFAULTS, **cfg_file}

    headers_from_config = cfg.get("headers") if isinstance(cfg.get("headers"), dict) else {}
    cookies_from_config = cfg.get("cookies") if isinstance(cfg.get("cookies"), dict) else {}

    headers_file_path = args.headers_file or get_config_str(cfg, "headers_file")
    cookies_file_path = args.cookies_file or get_config_str(cfg, "cookies_file")
    payload_file_path = args.payload_file or get_config_str(cfg, "payload_file")

    headers_from_file = parse_headers(read_text_file(headers_file_path)) if headers_file_path else {}
    headers_from_args = [parse_headers(chunk) for chunk in collect_argument_chunks(args.headers)]

    cookies_from_file = parse_cookies(read_text_file(cookies_file_path)) if cookies_file_path else {}
    cookies_from_args = [parse_cookies(chunk) for chunk in collect_argument_chunks(args.cookies)]

    headers = merge_dicts(headers_from_config, headers_from_file, *headers_from_args)
    cookies = merge_dicts(cookies_from_config, cookies_from_file, *cookies_from_args)

    user_agent = args.user_agent if args.user_agent is not None else get_config_str(cfg, "user_agent", DEFAULTS["user_agent"])
    if args.user_agent is not None and user_agent:
        # Explicit CLI value has the highest priority.
        headers["User-Agent"] = user_agent
    elif user_agent and not has_header(headers, "User-Agent"):
        # The .config default is only used if User-Agent was not provided in headers/files.
        headers["User-Agent"] = user_agent

    if args.payload_file:
        payload: bytes | str | None = read_bytes_file(args.payload_file)
    elif args.payload is not None:
        payload = args.payload
    elif payload_file_path:
        payload = read_bytes_file(payload_file_path)
    else:
        payload = get_config_str(cfg, "payload", "")

    method = (args.method if args.method is not None else get_config_str(cfg, "method", "GET")).upper()
    if method not in ALLOWED_METHODS:
        die(f"Unsupported method: {method}. Allowed: {', '.join(sorted(ALLOWED_METHODS))}")

    url = args.url or ""
    if not url:
        die("Missing --url. The URL is not defined in the config for operational safety.")
    validate_url(url)

    try:
        timeout = args.timeout if args.timeout is not None else float(get_config_str(cfg, "timeout", str(DEFAULTS["timeout"])))
    except ValueError:
        die("timeout must be numeric")
    if timeout <= 0:
        die("--timeout must be greater than 0")

    overrides: dict[str, bool] = getattr(args, "_interactive_overrides", {})
    follow_redirects = overrides.get("follow_redirects", False if args.no_redirects else parse_bool(cfg.get("follow_redirects", True)))
    verify_tls = overrides.get("verify_tls", False if args.insecure else parse_bool(cfg.get("verify_tls", True)))
    include_response_headers = overrides.get("include_response_headers", True if args.include else parse_bool(cfg.get("include_response_headers", False)))
    show_request = overrides.get("show_request", True if args.show_request else parse_bool(cfg.get("show_request", False)))
    dry_run = overrides.get("dry_run", True if args.dry_run else parse_bool(cfg.get("dry_run", False)))
    output = args.output if args.output is not None else get_config_str(cfg, "output")
    proxy = args.proxy if args.proxy is not None else get_config_str(cfg, "proxy")
    pretty_json = overrides.get("pretty_json", False if args.raw else parse_bool(cfg.get("pretty_json", True)))
    show_logo = overrides.get("show_logo", False if args.no_logo else parse_bool(cfg.get("show_logo", True)))
    color_mode = normalize_color_mode(
        getattr(args, "_interactive_color_mode", None)
        or ("never" if getattr(args, "no_color", False) else None)
        or getattr(args, "color", None)
        or cfg.get("color", DEFAULTS["color"])
    )
    color_enabled = should_use_color(color_mode)

    return RequestConfig(
        method=method,
        url=url,
        user_agent=user_agent,
        headers=headers,
        cookies=cookies,
        payload=payload,
        timeout=timeout,
        follow_redirects=follow_redirects,
        verify_tls=verify_tls,
        include_response_headers=include_response_headers,
        show_request=show_request,
        dry_run=dry_run,
        output=output,
        proxy=proxy,
        pretty_json=pretty_json,
        show_logo=show_logo,
        color_mode=color_mode,
        color_enabled=color_enabled,
    )


def build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = True
    return session


def prepare_request(session: requests.Session, cfg: RequestConfig) -> requests.PreparedRequest:
    body_is_empty = cfg.payload in (None, "", b"")
    req = requests.Request(
        method=cfg.method,
        url=cfg.url,
        headers=cfg.headers,
        cookies=cfg.cookies,
        data=None if body_is_empty else cfg.payload,
    )
    try:
        return session.prepare_request(req)
    except requests.exceptions.RequestException as exc:
        die(f"Could not prepare the request: {exc}")


def print_prepared_request(prepared: requests.PreparedRequest, cfg: RequestConfig) -> None:
    print("\n" + style("[Prepared request]", "violet", "bold", enabled=cfg.color_enabled))
    print(f"{style(cfg.method, 'green', 'bold', enabled=cfg.color_enabled)} {style(prepared.url, 'cyan', enabled=cfg.color_enabled)}")
    for k, v in redact(dict(prepared.headers)).items():
        header_name = style(k, "blue", enabled=cfg.color_enabled)
        header_value = style(v, "red", enabled=cfg.color_enabled) if v == "<redacted>" else v
        print(f"{header_name}: {header_value}")

    body = prepared.body
    if body:
        body_len = len(body) if isinstance(body, (bytes, bytearray)) else len(str(body).encode())
        print("\n" + style(f"[Body] {body_len} bytes", "violet", enabled=cfg.color_enabled))
        if body_len <= 4096:
            if isinstance(body, bytes):
                print(body.decode("utf-8", errors="replace"))
            else:
                print(body)
        else:
            print(style("<body omitted due to size>", "gray", enabled=cfg.color_enabled))


def make_proxies(proxy: str) -> Optional[dict[str, str]]:
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def status_color(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "green"
    if 300 <= status_code < 400:
        return "yellow"
    return "red"


def extract_partial_bytes(exc: BaseException) -> bytes:
    """Best-effort extraction of partial bytes from nested IncompleteRead errors."""
    seen: set[int] = set()

    def walk(obj: Any) -> bytes:
        oid = id(obj)
        if oid in seen:
            return b""
        seen.add(oid)

        partial = getattr(obj, "partial", None)
        if isinstance(partial, bytes):
            return partial

        for arg in getattr(obj, "args", ()):
            found = walk(arg)
            if found:
                return found
        return b""

    return walk(exc)


def read_response_body(resp: requests.Response) -> tuple[bool, str | None]:
    """
    Read the response body safely, preserving partial data when the server closes
    a chunked response early. This avoids raw tracebacks for IncompleteRead /
    ChunkedEncodingError and still lets the operator inspect what was received.
    """
    chunks: list[bytes] = []
    try:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
    except requests.exceptions.ChunkedEncodingError as exc:
        partial = extract_partial_bytes(exc)
        if partial:
            chunks.append(partial)
        resp._content = b"".join(chunks)
        resp._content_consumed = True
        resp.close()
        return False, f"Incomplete chunked response: {exc}"
    except requests.exceptions.ContentDecodingError as exc:
        partial = extract_partial_bytes(exc)
        if partial:
            chunks.append(partial)
        resp._content = b"".join(chunks)
        resp._content_consumed = True
        resp.close()
        return False, f"Response decoding error: {exc}"
    except requests.exceptions.RequestException as exc:
        partial = extract_partial_bytes(exc)
        if partial:
            chunks.append(partial)
        resp._content = b"".join(chunks)
        resp._content_consumed = True
        resp.close()
        return False, f"Response read error: {exc}"

    resp._content = b"".join(chunks)
    resp._content_consumed = True
    resp.close()
    return True, None


def print_response(resp: requests.Response, cfg: RequestConfig, elapsed: float, warning: str | None = None) -> None:
    code = style(str(resp.status_code), status_color(resp.status_code), "bold", enabled=cfg.color_enabled)
    reason = style(resp.reason, status_color(resp.status_code), enabled=cfg.color_enabled)
    label = style("[Response]", "violet", "bold", enabled=cfg.color_enabled)
    print(f"\n{label} HTTP {code} {reason} | {elapsed:.3f}s | {len(resp.content)} bytes")
    print(f"{style('[Final URL]', 'blue', enabled=cfg.color_enabled)} {style(resp.url, 'cyan', enabled=cfg.color_enabled)}")

    if warning:
        print(style(f"[!] Warning: {warning}", "yellow", enabled=cfg.color_enabled))
        print(style("[!] Partial response body was preserved when possible.", "yellow", enabled=cfg.color_enabled))

    if cfg.include_response_headers:
        print("\n" + style("[Response headers]", "violet", enabled=cfg.color_enabled))
        for k, v in resp.headers.items():
            print(f"{style(k, 'blue', enabled=cfg.color_enabled)}: {v}")

    if cfg.output:
        out = Path(cfg.output).expanduser()
        try:
            out.write_bytes(resp.content)
        except OSError as exc:
            die(f"Could not save response to {out}: {exc}")
        print("\n" + style(f"[+] Body saved to: {out}", "green", enabled=cfg.color_enabled))
        return

    if cfg.method == "HEAD":
        return

    content_type = resp.headers.get("Content-Type", "")
    print("\n" + style("[Body]", "violet", enabled=cfg.color_enabled))
    if cfg.pretty_json and "json" in content_type.lower():
        try:
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            return
        except ValueError:
            pass

    text = resp.text
    if len(text) > 20000:
        print(text[:20000])
        print("\n" + style("<output truncated to 20000 characters; use -o file to save everything>", "gray", enabled=cfg.color_enabled))
    else:
        print(text)


def send_request(cfg: RequestConfig) -> int:
    session = build_session()
    prepared = prepare_request(session, cfg)

    if cfg.show_request or cfg.dry_run:
        print_prepared_request(prepared, cfg)

    if cfg.dry_run:
        print("\n" + style("[+] Dry-run active: request was not sent.", "green", enabled=cfg.color_enabled))
        return 0

    settings = session.merge_environment_settings(
        prepared.url,
        proxies=make_proxies(cfg.proxy),
        stream=True,
        verify=cfg.verify_tls,
        cert=None,
    )

    body_complete = True
    body_warning: str | None = None
    start = time.perf_counter()
    try:
        resp = session.send(
            prepared,
            timeout=cfg.timeout,
            allow_redirects=cfg.follow_redirects,
            **settings,
        )
        body_complete, body_warning = read_response_body(resp)
    except requests.exceptions.SSLError as exc:
        die(f"TLS error: {exc}. In lab environments you can use --insecure.")
    except requests.exceptions.Timeout:
        die(f"Timeout after {cfg.timeout}s")
    except requests.exceptions.ConnectionError as exc:
        die(f"Connection error: {exc}")
    except requests.exceptions.RequestException as exc:
        die(f"HTTP error: {exc}")

    elapsed = time.perf_counter() - start
    print_response(resp, cfg, elapsed, body_warning)
    if not body_complete:
        return 4
    return 0 if 200 <= resp.status_code < 400 else 3


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.init_config:
        write_sample_config(args.config)
        return 0

    cfg_file = load_config(args.config)
    if args.interactive or parse_bool(cfg_file.get("interactive", False)):
        args = interactive_collect(args, cfg_file)

    cfg = resolve_config(args)
    if cfg.show_logo:
        print(render_logo(cfg.color_enabled))

    return send_request(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
