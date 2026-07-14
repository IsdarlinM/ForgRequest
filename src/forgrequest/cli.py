#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forgery HTTP Request - advanced HTTP client for authorized request replay.
Signature: imr

Design boundary: this is not a crawler or vulnerability scanner. It prepares,
modifies, replays, compares, and records HTTP requests/responses for manual,
authorized testing.
"""
from __future__ import annotations

import argparse
import configparser
import difflib
import html
import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    import requests
except ImportError:  # pragma: no cover
    print("[!] Missing dependency: requests", file=sys.stderr)
    print("    Install with: python -m pip install requests", file=sys.stderr)
    raise SystemExit(2)

VERSION = "1.7.2"
SIGNATURE = "imr"

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}
COLOR_MODES = {"auto", "always", "never"}
LOGO_COLOR = "cyan"
MAX_PRINT_BODY_CHARS = 20000
MAX_REQUEST_BODY_PREVIEW = 4096

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "proxy-authorization",
    "x-auth-token",
    "x-csrf-token",
    "x-xsrf-token",
}
SENSITIVE_NAME_PATTERNS = re.compile(
    r"(pass(word)?|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|session|jwt|bearer|auth|credential)",
    re.IGNORECASE,
)
COOKIE_ATTRS = {"path", "domain", "expires", "max-age", "samesite", "secure", "httponly"}
HEADER_NAME_RE = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
HEADER_SEPARATOR_RE = re.compile(rf";(?=\s*{HEADER_NAME_RE}\s*:)")
VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

ANSI_STYLES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[38;5;80m",
    "blue": "\033[38;5;75m",
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

             Forgery HTTP Request v{VERSION}  ::  signature: {SIGNATURE}
"""

DEFAULTS: dict[str, Any] = {
    "method": "GET",
    "user_agent": f"ForgeryHTTP/{VERSION} ({SIGNATURE})",
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
    "show_redirect_chain": False,
    "no_env_proxy": False,
    "redact_reports": True,
}

SAMPLE_CONFIG = f'''# forgrequest.config
# INI/.config format read with configparser from the Python standard library.
# The URL must NOT be stored here. Always pass it as an argument: --url https://example.com

[request]
method = GET
user_agent = ForgeryHTTP/{VERSION} ({SIGNATURE})
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
show_redirect_chain = false
no_env_proxy = false
redact_reports = true

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
class RawRequestData:
    method: str = ""
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass
class MultipartPart:
    name: str
    value: str | bytes
    filename: str | None = None
    content_type: str | None = None


@dataclass
class RequestConfig:
    method: str = DEFAULTS["method"]
    url: str = ""
    user_agent: str = DEFAULTS["user_agent"]
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    payload: bytes | str | None = DEFAULTS["payload"]
    multipart: list[MultipartPart] = field(default_factory=list)
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
    show_redirect_chain: bool = DEFAULTS["show_redirect_chain"]
    no_env_proxy: bool = DEFAULTS["no_env_proxy"]
    save_cookies: str = ""
    save_prepared_request: str = ""
    export_curl: bool = False
    export_python: bool = False
    report_json: str = ""
    report_html: str = ""
    save_session: str = ""
    redact_reports: bool = DEFAULTS["redact_reports"]


@dataclass
class ExecutionResult:
    response: requests.Response | None
    elapsed: float
    body_complete: bool
    warning: str | None
    prepared: requests.PreparedRequest
    request_raw: str
    request_curl: str
    request_python: str




class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Show default values while preserving explicit help layout and examples."""

def die(message: str, code: int = 1) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(code)


def find_default_config_file() -> str:
    env_config = os.getenv("FORGREQUEST_CONFIG")
    candidates: list[Path] = []
    if env_config:
        candidates.append(Path(env_config).expanduser())
    current = Path(__file__).resolve()
    candidates.extend(
        [
            Path.cwd() / "forgrequest.config",
            current.parent / "forgrequest.config",
            current.parents[2] / "config" / "forgrequest.config" if len(current.parents) >= 3 else Path("forgrequest.config"),
            Path.home() / ".config" / "forgrequest" / "forgrequest.config",
        ]
    )
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    return "forgrequest.config"


DEFAULT_CONFIG_FILE = find_default_config_file()


def enable_windows_ansi() -> None:
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
    return f"{codes}{value}{ANSI_STYLES['reset']}" if codes else value


def render_logo(color_enabled: bool) -> str:
    if not color_enabled:
        return LOGO
    return "\n".join(style(line, LOGO_COLOR, "bold", enabled=True) if line.strip() else line for line in LOGO.splitlines())


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


def write_text(path: str | Path, content: str) -> None:
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except OSError as exc:
        die(f"Could not write {p}: {exc}")


def write_bytes(path: str | Path, content: bytes) -> None:
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    except OSError as exc:
        die(f"Could not write {p}: {exc}")


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


def split_header_candidates(line: str) -> list[str]:
    return [part.strip() for part in HEADER_SEPARATOR_RE.split(line.replace("\r", "")) if part.strip()]


def parse_headers(raw: str) -> dict[str, str]:
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

    text = re.sub(r"(?:^|\s)-H\s+", "\n", text)
    candidates: list[str] = []
    for line in text.splitlines():
        line = line.strip().strip("'\"")
        if line:
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
    if len(parts) >= 7:
        return parts[5].strip(), parts[6].strip()
    return None


def parse_cookies(raw: str) -> dict[str, str]:
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
        if not line or line.startswith("#"):
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
            if k is not None:
                merged[str(k)] = str(v)
    return merged


def is_sensitive_name(name: str) -> bool:
    return name.lower() in SENSITIVE_KEYS or bool(SENSITIVE_NAME_PATTERNS.search(name))


def redact_value(value: Any) -> str:
    text = str(value)
    if len(text) <= 8:
        return "<redacted>"
    return f"{text[:3]}***{text[-4:]}"


def redact_mapping(mapping: dict[str, str]) -> dict[str, str]:
    return {k: ("<redacted>" if is_sensitive_name(k) else v) for k, v in mapping.items()}


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [(k, "<redacted>" if is_sensitive_name(k) else v) for k, v in pairs]
    return urlunparse(parsed._replace(query=urlencode(redacted, doseq=True)))


def redact_text(text: str) -> str:
    masked = text
    masked = re.sub(r"(?i)(Authorization\s*:\s*Bearer\s+)[^\s\r\n]+", r"\1<redacted>", masked)
    masked = re.sub(r"(?i)(Authorization\s*:\s*Basic\s+)[^\s\r\n]+", r"\1<redacted>", masked)
    masked = re.sub(r"(?i)(Cookie\s*:\s*)[^\r\n]+", r"\1<redacted>", masked)
    masked = re.sub(r"(?i)(Set-Cookie\s*:\s*)[^\r\n]+", r"\1<redacted>", masked)
    masked = re.sub(r"(?i)((?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\s*[=:]\s*)[^&\s,\"'}]+", r"\1<redacted>", masked)
    return masked


def has_header(headers: dict[str, str], name: str) -> bool:
    wanted = name.lower()
    return any(key.lower() == wanted for key in headers)


def remove_header_case_insensitive(headers: dict[str, str], name: str) -> None:
    wanted = name.lower()
    for key in list(headers.keys()):
        if key.lower() == wanted:
            headers.pop(key, None)


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        die("Invalid URL. It must start with http:// or https://")
    if not parsed.netloc:
        die("Invalid URL. Missing host.")


def update_query(url: str, set_items: list[str], remove_items: list[str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for name in remove_items:
        query.pop(name, None)
    for item in set_items:
        if "=" not in item:
            die(f"Invalid query modifier, use name=value: {item!r}")
        name, value = item.split("=", 1)
        if not name:
            die("Query parameter name cannot be empty")
        query[name] = value
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def new_config_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
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
    write_text(p, SAMPLE_CONFIG)
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


def load_vars_file(path: str | Path) -> dict[str, str]:
    values: dict[str, str] = {}
    text = read_text_file(path)
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[len("export ") :].strip()
        if "=" not in raw:
            die(f"Invalid vars line, use KEY=value: {line!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            die(f"Invalid variable name: {key!r}")
        values[key] = value
    return values


def parse_var_args(items: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            die(f"Invalid variable, use KEY=value: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            die(f"Invalid variable name: {key!r}")
        values[key] = value
    return values


def apply_vars_text(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            die(f"Missing variable {key!r}. Provide it with --var {key}=value or --vars-file.")
        return variables[key]

    return VARIABLE_RE.sub(replace, text)


def apply_vars_mapping(mapping: dict[str, str], variables: dict[str, str]) -> dict[str, str]:
    if not variables:
        return mapping
    return {apply_vars_text(k, variables): apply_vars_text(v, variables) for k, v in mapping.items()}


def parse_raw_http_request_bytes(raw: bytes, scheme: str = "https", url_override: str = "") -> RawRequestData:
    separator = b"\r\n\r\n" if b"\r\n\r\n" in raw else b"\n\n"
    if separator in raw:
        head, body = raw.split(separator, 1)
    else:
        head, body = raw, b""
    try:
        lines = head.decode("latin-1").splitlines()
    except UnicodeDecodeError as exc:
        die(f"Raw request headers are not decodable as latin-1: {exc}")
    if not lines:
        die("Raw request is empty")
    request_line = lines[0].strip()
    parts = request_line.split()
    if len(parts) < 2:
        die("Invalid raw request line. Expected: METHOD /path HTTP/1.1")
    method = parts[0].upper()
    target = parts[1]
    if method not in ALLOWED_METHODS:
        die(f"Unsupported method in raw request: {method}")

    headers: dict[str, str] = {}
    current_name: str | None = None
    for line in lines[1:]:
        if not line:
            continue
        if line[0] in " \t" and current_name:
            headers[current_name] += " " + line.strip()
            continue
        if ":" not in line:
            die(f"Invalid raw header line: {line!r}")
        name, value = line.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not re.fullmatch(HEADER_NAME_RE, name):
            die(f"Invalid raw header name: {name!r}")
        headers[name] = value
        current_name = name

    if url_override:
        url = url_override
    elif target.startswith("http://") or target.startswith("https://"):
        url = target
    else:
        host = next((v for k, v in headers.items() if k.lower() == "host"), "")
        if not host:
            die("Raw request with relative path requires a Host header or --url override")
        if not target.startswith("/"):
            target = "/" + target
        url = f"{scheme}://{host}{target}"
    validate_url(url)
    return RawRequestData(method=method, url=url, headers=headers, body=body)


def parse_raw_http_request_file(path: str, scheme: str, url_override: str = "") -> RawRequestData:
    return parse_raw_http_request_bytes(read_bytes_file(path), scheme=scheme, url_override=url_override)


def parse_curl_command(command: str) -> dict[str, Any]:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        die(f"Could not parse curl command: {exc}")
    if tokens and tokens[0].lower() == "curl":
        tokens = tokens[1:]
    result: dict[str, Any] = {
        "headers": [],
        "cookies": [],
        "payload_parts": [],
        "url": "",
        "method": "",
        "insecure": False,
        "follow_redirects": False,
        "user_agent": "",
    }
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in {"-X", "--request"}:
            i += 1
            if i >= len(tokens):
                die("curl parser: missing method after -X/--request")
            result["method"] = tokens[i].upper()
        elif token.startswith("-X") and len(token) > 2:
            result["method"] = token[2:].upper()
        elif token in {"-H", "--header"}:
            i += 1
            if i >= len(tokens):
                die("curl parser: missing header after -H/--header")
            result["headers"].append(tokens[i])
        elif token in {"-b", "--cookie", "--cookie-raw"}:
            i += 1
            if i >= len(tokens):
                die("curl parser: missing cookie after -b/--cookie")
            result["cookies"].append(tokens[i])
        elif token in {"-A", "--user-agent"}:
            i += 1
            if i >= len(tokens):
                die("curl parser: missing user-agent after -A/--user-agent")
            result["user_agent"] = tokens[i]
        elif token in {"-d", "--data", "--data-raw", "--data-binary", "--data-ascii", "--data-urlencode"}:
            i += 1
            if i >= len(tokens):
                die(f"curl parser: missing data after {token}")
            value = tokens[i]
            if value.startswith("@") and token == "--data-binary":
                result["payload_parts"].append(read_bytes_file(value[1:]))
            else:
                result["payload_parts"].append(value)
            if not result["method"]:
                result["method"] = "POST"
        elif token in {"-k", "--insecure"}:
            result["insecure"] = True
        elif token in {"-L", "--location"}:
            result["follow_redirects"] = True
        elif token == "--url":
            i += 1
            if i >= len(tokens):
                die("curl parser: missing URL after --url")
            result["url"] = tokens[i]
        elif token in {"-o", "--output", "--connect-timeout", "--max-time"}:
            i += 1  # accepted but ignored here; CLI has native options
        elif token.startswith("-"):
            # Non-fatal: many curl flags have no direct requests equivalent.
            pass
        else:
            if token.startswith("http://") or token.startswith("https://"):
                result["url"] = token
        i += 1

    if result["payload_parts"]:
        if all(isinstance(part, bytes) for part in result["payload_parts"]):
            result["payload"] = b"&".join(result["payload_parts"])
        else:
            result["payload"] = "&".join(part.decode("utf-8", errors="replace") if isinstance(part, bytes) else str(part) for part in result["payload_parts"])
    return result


def apply_curl_to_args(args: argparse.Namespace) -> argparse.Namespace:
    if not args.from_curl:
        return args
    raw = args.from_curl
    if Path(raw).expanduser().is_file():
        raw = read_text_file(raw)
    parsed = parse_curl_command(raw)
    if not args.url and parsed.get("url"):
        args.url = parsed["url"]
    if not args.method and parsed.get("method"):
        args.method = parsed["method"]
    if not args.user_agent and parsed.get("user_agent"):
        args.user_agent = parsed["user_agent"]
    if parsed.get("headers"):
        args.headers = (args.headers or []) + list(parsed["headers"])
    if parsed.get("cookies"):
        args.cookies = (args.cookies or []) + list(parsed["cookies"])
    if args.payload is None and not args.payload_file and parsed.get("payload") is not None:
        args.payload = parsed["payload"]
    if parsed.get("insecure"):
        args.insecure = True
    if parsed.get("follow_redirects"):
        args.no_redirects = False
    return args


def parse_multipart_item(item: str) -> MultipartPart:
    if "=" not in item:
        die(f"Invalid multipart value. Use name=value or name=@file: {item!r}")
    name, raw_value = item.split("=", 1)
    name = name.strip()
    if not name:
        die("Multipart field name cannot be empty")
    content_type = None
    value_part = raw_value
    if ";type=" in raw_value:
        value_part, content_type = raw_value.split(";type=", 1)
        content_type = content_type.strip() or None
    if value_part.startswith("@"):
        file_path = value_part[1:]
        data = read_bytes_file(file_path)
        return MultipartPart(name=name, value=data, filename=Path(file_path).name, content_type=content_type)
    return MultipartPart(name=name, value=value_part)


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
    if not args.url and not args.raw_request:
        args.url = prompt_text("Target URL", required=True)
    if args.url:
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
    overrides["show_redirect_chain"] = prompt_yes_no("Show redirect chain", bool(args.show_redirect_chain) or parse_bool(cfg.get("show_redirect_chain", False)))

    color_default = normalize_color_mode(getattr(args, "color", None) or ("never" if getattr(args, "no_color", False) else cfg.get("color", DEFAULTS["color"])))
    color_mode = prompt_text("Color ANSI (auto/always/never)", color_default).lower()
    setattr(args, "_interactive_color_mode", normalize_color_mode(color_mode))
    setattr(args, "_interactive_overrides", overrides)
    return args


def build_diff_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgrequest diff",
        description="Compare two saved HTTP responses or arbitrary files. This does not send network requests.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Special commands: forgrequest web --help | forgrequest diff --help | forgrequest update --help",
    )
    parser.add_argument("left", help="First file")
    parser.add_argument("right", help="Second file")
    parser.add_argument("--context", type=int, default=3, help="Unified diff context lines")
    parser.add_argument("--json", dest="json_output", help="Save diff summary to JSON file")
    parser.add_argument("--no-body-diff", action="store_true", help="Only print summary, not unified textual diff")
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgrequest",
        description=(
            "Forgery HTTP Request: HTTP client for authorized request replay, "
            "request modification, response viewing, local diffing, web operation, and safe updates.\n\n"
            "Boundary: ForgRequest is not a crawler and not a vulnerability scanner. "
            "It works on individual operator-supplied requests."
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Command-specific help:\n"
            "  forgrequest web --help       Start and configure the local Web Console\n"
            "  forgrequest diff --help      Compare two saved responses or arbitrary files\n"
            "  forgrequest update --help    Safely update an installed/source-tree copy\n\n"
            "Common examples:\n"
            "  forgrequest -u https://example.com --dry-run --show-request\n"
            "  forgrequest -u https://example.com/api -X POST --json-file payload.json --include\n"
            "  forgrequest --raw-request request.raw --show-request\n"
            "  forgrequest --from-curl curl.txt --export-python\n"
            "  forgrequest -u https://example.com --save-session case-001/ --report-html report.html\n"
            "  forgrequest web --open\n"
            "  forgrequest diff response-a.txt response-b.txt --json diff.json\n"
            "  forgrequest update --dry-run\n        "
        ),
    )

    subparsers = parser.add_subparsers(
        title="commands",
        metavar="<command>",
        dest="command",
        help="Run 'forgrequest <command> --help' for command-specific options.",
    )
    subparsers.add_parser("web", help="Start the local Web Console with full CLI workflow coverage.", add_help=False)
    subparsers.add_parser("diff", help="Compare two saved HTTP responses or arbitrary files.", add_help=False)
    subparsers.add_parser("update", help="Safely update ForgRequest from GitHub or a local ZIP.", add_help=False)

    general = parser.add_argument_group("general")
    general.add_argument("--version", action="store_true", help="Print version and exit.")
    general.add_argument("-c", "--config", default=DEFAULT_CONFIG_FILE, help="Default .config configuration file.")
    general.add_argument("--init-config", action="store_true", help="Create a base configuration file and exit.")

    target = parser.add_argument_group("target and method")
    target.add_argument("-u", "--url", required=False, help="Target URL. Required unless --init-config, --raw-request, or --from-curl provides it.")
    target.add_argument("-X", "--method", help="HTTP method: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, TRACE.")
    target.add_argument("-A", "--user-agent", dest="user_agent", help="Custom User-Agent.")

    import_group = parser.add_argument_group("request import and replay")
    import_group.add_argument("--raw-request", help="Load a raw HTTP/1.1 request from file and replay it.")
    import_group.add_argument("--raw-scheme", choices=["http", "https"], default="https", help="Scheme used when --raw-request has a relative target.")
    import_group.add_argument("--from-curl", help="Import a curl command string or a file containing a curl command.")

    headers_group = parser.add_argument_group("headers")
    headers_group.add_argument("-H", "--headers", action="append", help="Headers as string. Repeatable. Example: -H 'X-Test: 1'")
    headers_group.add_argument("--headers-file", help="Headers file: JSON, lines like 'Header: value', or curl -H fragments.")
    headers_group.add_argument("--set-header", action="append", default=[], help="Set/replace a header after all other sources. Repeatable.")
    headers_group.add_argument("--remove-header", action="append", default=[], help="Remove a header by name after all other sources. Repeatable.")

    cookies_group = parser.add_argument_group("cookies")
    cookies_group.add_argument("-b", "--cookies", action="append", help="Cookies as string. Repeatable. Example: -b 'a=b; c=d'")
    cookies_group.add_argument("--cookies-file", help="Cookies file: Netscape, JSON, Cookie header, Set-Cookie lines, or name=value lines.")
    cookies_group.add_argument("--load-cookies", help="Alias for --cookies-file, useful with --save-cookies/--cookie-jar flows.")
    cookies_group.add_argument("--save-cookies", help="Save response/session cookies to a simple reusable cookie file.")
    cookies_group.add_argument("--cookie-jar", help="Load cookies before the request and save updated cookies after the response.")
    cookies_group.add_argument("--set-cookie", action="append", default=[], help="Set/replace a cookie after all other sources. Repeatable.")
    cookies_group.add_argument("--remove-cookie", action="append", default=[], help="Remove a cookie by name after all other sources. Repeatable.")

    query_group = parser.add_argument_group("query parameters")
    query_group.add_argument("--set-query", action="append", default=[], help="Set/replace URL query parameter name=value. Repeatable.")
    query_group.add_argument("--remove-query", action="append", default=[], help="Remove URL query parameter by name. Repeatable.")

    body_group = parser.add_argument_group("payload and body helpers")
    body_group.add_argument("-d", "--payload", help="Payload/body as string.")
    body_group.add_argument("--payload-file", help="File to send as body bytes.")
    body_group.add_argument("--json", dest="json_body", help="JSON body string. Sets Content-Type when absent.")
    body_group.add_argument("--json-file", help="JSON body file. Validates JSON and sets Content-Type when absent.")
    body_group.add_argument("--form", help="Form body string, for example 'a=1&b=2'. Sets Content-Type when absent.")
    body_group.add_argument("--form-file", help="Form body file. Sets Content-Type when absent.")
    body_group.add_argument("--binary-file", help="Binary file to send as body bytes. Alias specialized for non-text payloads.")
    body_group.add_argument("--multipart", action="append", default=[], help="Multipart field. Use name=value or name=@file[;type=mime]. Repeatable.")
    body_group.add_argument("--replace-body", action="append", default=[], help="Replace text in string/UTF-8 body using old=new. Repeatable.")

    variables_group = parser.add_argument_group("template variables")
    variables_group.add_argument("--var", action="append", default=[], help="Template variable KEY=value for {{KEY}} placeholders. Repeatable.")
    variables_group.add_argument("--vars-file", help="File with KEY=value variables for {{KEY}} placeholders.")

    network_group = parser.add_argument_group("network, redirects, proxy and TLS")
    network_group.add_argument("--timeout", type=float, help="Approximate total request timeout in seconds.")
    network_group.add_argument("--no-redirects", action="store_true", help="Do not follow HTTP redirects.")
    network_group.add_argument("--show-redirect-chain", action="store_true", help="Print the redirect chain when redirects are followed.")
    network_group.add_argument("--insecure", action="store_true", help="Do not verify TLS. Use only in lab environments.")
    network_group.add_argument("--proxy", help="HTTP/HTTPS proxy. Example: http://127.0.0.1:8080")
    network_group.add_argument("--no-env-proxy", action="store_true", help="Ignore proxy/CA settings from environment variables.")

    output_group = parser.add_argument_group("output, display and exports")
    output_group.add_argument("--include", action="store_true", help="Show response headers along with the body.")
    output_group.add_argument("--show-request", action="store_true", help="Show the prepared request with secrets redacted.")
    output_group.add_argument("--dry-run", action="store_true", help="Prepare and show the request without sending it.")
    output_group.add_argument("-o", "--output", help="Save response body to file.")
    output_group.add_argument("--raw", action="store_true", help="Do not pretty-print JSON responses.")
    output_group.add_argument("--no-logo", action="store_true", help="Do not show the logo.")
    output_group.add_argument("--save-prepared-request", help="Save the prepared HTTP request as raw HTTP/1.1 text.")
    output_group.add_argument("--export-curl", action="store_true", help="Print an equivalent curl command for the prepared request.")
    output_group.add_argument("--export-python", action="store_true", help="Print a minimal Python requests snippet for the prepared request.")

    reports_group = parser.add_argument_group("reports and session evidence")
    reports_group.add_argument("--report-json", help="Save an execution report as JSON metadata.")
    reports_group.add_argument("--report-html", help="Save an execution report as a self-contained HTML file.")
    reports_group.add_argument("--save-session", help="Save request, curl, response headers/body, and metadata in a directory.")
    reports_group.add_argument("--no-redact-reports", action="store_true", help="Do not redact sensitive metadata in JSON/HTML reports.")

    ux_group = parser.add_argument_group("color and interactive mode")
    color_group = ux_group.add_mutually_exclusive_group()
    color_group.add_argument("--color", nargs="?", const="always", choices=sorted(COLOR_MODES), help="ANSI color mode: auto, always, or never. Using --color without a value equals always.")
    color_group.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    ux_group.add_argument("-i", "--interactive", action="store_true", help="Interactive mode to build the request step by step.")
    return parser


def resolve_body_from_args(args: argparse.Namespace, cfg: dict[str, Any], raw_data: RawRequestData, headers: dict[str, str]) -> tuple[bytes | str | None, list[MultipartPart]]:
    multipart = [parse_multipart_item(item) for item in args.multipart]
    if multipart:
        return None, multipart

    payload_file_path = args.payload_file or get_config_str(cfg, "payload_file")
    body: bytes | str | None
    if args.json_file:
        text = read_text_file(args.json_file)
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            die(f"Invalid JSON file {args.json_file}: {exc}")
        body = text
        if not has_header(headers, "Content-Type"):
            headers["Content-Type"] = "application/json"
    elif args.json_body is not None:
        try:
            json.loads(args.json_body)
        except json.JSONDecodeError as exc:
            die(f"Invalid JSON body: {exc}")
        body = args.json_body
        if not has_header(headers, "Content-Type"):
            headers["Content-Type"] = "application/json"
    elif args.form_file:
        body = read_text_file(args.form_file)
        if not has_header(headers, "Content-Type"):
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif args.form is not None:
        body = args.form
        if not has_header(headers, "Content-Type"):
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif args.binary_file:
        body = read_bytes_file(args.binary_file)
    elif args.payload_file:
        body = read_bytes_file(args.payload_file)
    elif args.payload is not None:
        body = args.payload
    elif raw_data.body:
        body = raw_data.body
    elif payload_file_path:
        body = read_bytes_file(payload_file_path)
    else:
        body = get_config_str(cfg, "payload", "")

    if args.replace_body:
        if isinstance(body, bytes):
            try:
                body_text = body.decode("utf-8")
            except UnicodeDecodeError:
                die("--replace-body can only be used with UTF-8/text bodies")
        else:
            body_text = "" if body is None else str(body)
        for item in args.replace_body:
            if "=" not in item:
                die(f"Invalid --replace-body value, use old=new: {item!r}")
            old, new = item.split("=", 1)
            body_text = body_text.replace(old, new)
        body = body_text
    return body, multipart


def resolve_config(args: argparse.Namespace) -> RequestConfig:
    cfg_file = load_config(args.config)
    cfg = {**DEFAULTS, **cfg_file}

    variables: dict[str, str] = {}
    if args.vars_file:
        variables.update(load_vars_file(args.vars_file))
    variables.update(parse_var_args(args.var))

    raw_data = RawRequestData()
    if args.raw_request:
        raw_data = parse_raw_http_request_file(args.raw_request, args.raw_scheme, url_override=args.url or "")

    headers_from_config = cfg.get("headers") if isinstance(cfg.get("headers"), dict) else {}
    cookies_from_config = cfg.get("cookies") if isinstance(cfg.get("cookies"), dict) else {}

    headers_file_path = args.headers_file or get_config_str(cfg, "headers_file")
    explicit_cookies_file = args.load_cookies or args.cookies_file or get_config_str(cfg, "cookies_file")
    if args.cookie_jar and Path(args.cookie_jar).expanduser().is_file():
        cookies_file_path = args.cookie_jar
    else:
        cookies_file_path = explicit_cookies_file

    headers_from_file = parse_headers(read_text_file(headers_file_path)) if headers_file_path else {}
    headers_from_args = [parse_headers(chunk) for chunk in collect_argument_chunks(args.headers)]
    cookies_from_file = parse_cookies(read_text_file(cookies_file_path)) if cookies_file_path else {}
    cookies_from_args = [parse_cookies(chunk) for chunk in collect_argument_chunks(args.cookies)]

    headers = merge_dicts(headers_from_config, raw_data.headers, headers_from_file, *headers_from_args)

    # Normalize an explicit Cookie header into the cookie jar so --set-cookie and
    # --remove-cookie can modify raw/cURL/imported requests predictably.
    cookie_header_value = ""
    for key in list(headers.keys()):
        if key.lower() == "cookie":
            cookie_header_value = headers.pop(key)
            break
    cookies_from_header = parse_cookies(cookie_header_value) if cookie_header_value else {}
    cookies = merge_dicts(cookies_from_config, cookies_from_header, cookies_from_file, *cookies_from_args)

    for name in args.remove_header:
        remove_header_case_insensitive(headers, name)
    for chunk in args.set_header:
        headers.update(parse_headers(chunk))

    for name in args.remove_cookie:
        cookies.pop(name, None)
    for chunk in args.set_cookie:
        cookies.update(parse_cookies(chunk))

    user_agent = args.user_agent if args.user_agent is not None else get_config_str(cfg, "user_agent", DEFAULTS["user_agent"])
    if args.user_agent is not None and user_agent:
        headers["User-Agent"] = user_agent
    elif user_agent and not has_header(headers, "User-Agent"):
        headers["User-Agent"] = user_agent

    method = (args.method or raw_data.method or get_config_str(cfg, "method", "GET")).upper()
    if method not in ALLOWED_METHODS:
        die(f"Unsupported method: {method}. Allowed: {', '.join(sorted(ALLOWED_METHODS))}")

    url = args.url or raw_data.url or ""
    if variables and url:
        url = apply_vars_text(url, variables)
    if args.set_query or args.remove_query:
        url = update_query(url, args.set_query, args.remove_query)
    if not url:
        die("Missing --url. The URL is not defined in the config for operational safety.")
    validate_url(url)

    headers = apply_vars_mapping(headers, variables)
    cookies = apply_vars_mapping(cookies, variables)
    payload, multipart = resolve_body_from_args(args, cfg, raw_data, headers)
    if variables and isinstance(payload, str):
        payload = apply_vars_text(payload, variables)

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
    show_redirect_chain = overrides.get("show_redirect_chain", True if args.show_redirect_chain else parse_bool(cfg.get("show_redirect_chain", False)))
    no_env_proxy = True if args.no_env_proxy else parse_bool(cfg.get("no_env_proxy", False))
    color_mode = normalize_color_mode(getattr(args, "_interactive_color_mode", None) or ("never" if getattr(args, "no_color", False) else None) or getattr(args, "color", None) or cfg.get("color", DEFAULTS["color"]))
    color_enabled = should_use_color(color_mode)

    save_cookies = args.save_cookies or args.cookie_jar or ""
    return RequestConfig(
        method=method,
        url=url,
        user_agent=user_agent,
        headers=headers,
        cookies=cookies,
        payload=payload,
        multipart=multipart,
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
        show_redirect_chain=show_redirect_chain,
        no_env_proxy=no_env_proxy,
        save_cookies=save_cookies,
        save_prepared_request=args.save_prepared_request or "",
        export_curl=bool(args.export_curl),
        export_python=bool(args.export_python),
        report_json=args.report_json or "",
        report_html=args.report_html or "",
        save_session=args.save_session or "",
        redact_reports=not bool(args.no_redact_reports),
    )


def build_session(cfg: RequestConfig) -> requests.Session:
    session = requests.Session()
    session.trust_env = not cfg.no_env_proxy
    if cfg.cookies:
        session.cookies.update(cfg.cookies)
    return session


def make_files_and_data(cfg: RequestConfig) -> tuple[Any, Any]:
    if not cfg.multipart:
        return None, None
    files: list[tuple[str, Any]] = []
    data: dict[str, str] = {}
    for part in cfg.multipart:
        if part.filename:
            if part.content_type:
                files.append((part.name, (part.filename, part.value, part.content_type)))
            else:
                files.append((part.name, (part.filename, part.value)))
        else:
            data[part.name] = part.value.decode("utf-8", errors="replace") if isinstance(part.value, bytes) else str(part.value)
    return files or None, data or None


def prepare_request(session: requests.Session, cfg: RequestConfig) -> requests.PreparedRequest:
    body_is_empty = cfg.payload in (None, "", b"")
    files, data = make_files_and_data(cfg)
    req = requests.Request(
        method=cfg.method,
        url=cfg.url,
        headers=cfg.headers,
        cookies=cfg.cookies,
        data=data if data is not None else (None if body_is_empty else cfg.payload),
        files=files,
    )
    try:
        return session.prepare_request(req)
    except requests.exceptions.RequestException as exc:
        die(f"Could not prepare the request: {exc}")


def make_proxies(proxy: str) -> Optional[dict[str, str]]:
    return {"http": proxy, "https": proxy} if proxy else None


def status_color(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "green"
    if 300 <= status_code < 400:
        return "yellow"
    return "red"


def body_to_bytes(body: Any) -> bytes:
    if body is None:
        return b""
    if isinstance(body, bytes):
        return body
    if isinstance(body, bytearray):
        return bytes(body)
    return str(body).encode("utf-8")


def prepared_to_raw(prepared: requests.PreparedRequest, redact: bool = False) -> str:
    parsed = urlparse(prepared.url or "")
    path = urlunparse(("", "", parsed.path or "/", parsed.params, parsed.query, ""))
    lines = [f"{prepared.method} {path} HTTP/1.1"]
    headers = dict(prepared.headers)
    if "Host" not in {k.title(): v for k, v in headers.items()}:
        netloc = parsed.netloc
        if netloc:
            lines.append(f"Host: {netloc}")
    printable = redact_mapping(headers) if redact else headers
    for key, value in printable.items():
        lines.append(f"{key}: {value}")
    body = body_to_bytes(prepared.body)
    if body:
        lines.append("")
        lines.append(body.decode("utf-8", errors="replace"))
    return "\r\n".join(lines) + "\r\n"


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def prepared_to_curl(prepared: requests.PreparedRequest, redact: bool = False) -> str:
    url = redact_url(prepared.url or "") if redact else (prepared.url or "")
    parts = ["curl", "-X", shell_quote(prepared.method or "GET"), shell_quote(url)]
    headers = redact_mapping(dict(prepared.headers)) if redact else dict(prepared.headers)
    for key, value in headers.items():
        parts.extend(["-H", shell_quote(f"{key}: {value}")])
    body = body_to_bytes(prepared.body)
    if body:
        try:
            text = body.decode("utf-8")
            parts.extend(["--data-binary", shell_quote(text)])
        except UnicodeDecodeError:
            parts.extend(["--data-binary", "@<binary-body-file>"])
    return " ".join(parts)


def prepared_to_python(prepared: requests.PreparedRequest, cfg: RequestConfig, redact: bool = False) -> str:
    headers = redact_mapping(dict(prepared.headers)) if redact else dict(prepared.headers)
    url = redact_url(prepared.url or "") if redact else (prepared.url or "")
    body = body_to_bytes(prepared.body)
    data_expr = "None"
    if body:
        try:
            data_expr = repr(body.decode("utf-8"))
        except UnicodeDecodeError:
            data_expr = repr(body)
    return (
        "import requests\n\n"
        f"url = {url!r}\n"
        f"headers = {headers!r}\n"
        f"data = {data_expr}\n\n"
        "response = requests.request(\n"
        f"    {prepared.method!r},\n"
        "    url,\n"
        "    headers=headers,\n"
        "    data=data,\n"
        f"    timeout={cfg.timeout!r},\n"
        f"    allow_redirects={cfg.follow_redirects!r},\n"
        f"    verify={cfg.verify_tls!r},\n"
        ")\n"
        "print(response.status_code)\n"
        "print(response.text)\n"
    )


def print_prepared_request(prepared: requests.PreparedRequest, cfg: RequestConfig) -> None:
    print("\n" + style("[Prepared request]", "cyan", "bold", enabled=cfg.color_enabled))
    print(f"{style(prepared.method, 'green', 'bold', enabled=cfg.color_enabled)} {style(redact_url(prepared.url or ''), 'cyan', enabled=cfg.color_enabled)}")
    for k, v in redact_mapping(dict(prepared.headers)).items():
        header_name = style(k, "blue", enabled=cfg.color_enabled)
        header_value = style(v, "red", enabled=cfg.color_enabled) if v == "<redacted>" else v
        print(f"{header_name}: {header_value}")
    body = prepared.body
    if body:
        body_bytes = body_to_bytes(body)
        print("\n" + style(f"[Body] {len(body_bytes)} bytes", "cyan", enabled=cfg.color_enabled))
        if len(body_bytes) <= MAX_REQUEST_BODY_PREVIEW:
            print(redact_text(body_bytes.decode("utf-8", errors="replace")))
        else:
            print(style("<body omitted due to size>", "gray", enabled=cfg.color_enabled))


def extract_partial_bytes(exc: BaseException) -> bytes:
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


def print_redirect_chain(resp: requests.Response, cfg: RequestConfig) -> None:
    chain = list(resp.history) + [resp]
    if len(chain) <= 1:
        return
    print("\n" + style("[Redirect chain]", "cyan", "bold", enabled=cfg.color_enabled))
    for item in chain:
        code = style(str(item.status_code), status_color(item.status_code), "bold", enabled=cfg.color_enabled)
        location = item.headers.get("Location")
        line = f"HTTP {code} {item.url}"
        if location:
            line += f" -> {location}"
        print(line)


def print_response(resp: requests.Response, cfg: RequestConfig, elapsed: float, warning: str | None = None) -> None:
    code = style(str(resp.status_code), status_color(resp.status_code), "bold", enabled=cfg.color_enabled)
    reason = style(resp.reason, status_color(resp.status_code), enabled=cfg.color_enabled)
    label = style("[Response]", "cyan", "bold", enabled=cfg.color_enabled)
    print(f"\n{label} HTTP {code} {reason} | {elapsed:.3f}s | {len(resp.content)} bytes")
    print(f"{style('[Final URL]', 'blue', enabled=cfg.color_enabled)} {style(resp.url, 'cyan', enabled=cfg.color_enabled)}")

    if warning:
        print(style(f"[!] Warning: {warning}", "yellow", enabled=cfg.color_enabled))
        print(style("[!] Partial response body was preserved when possible.", "yellow", enabled=cfg.color_enabled))

    if cfg.show_redirect_chain:
        print_redirect_chain(resp, cfg)

    if cfg.include_response_headers:
        print("\n" + style("[Response headers]", "cyan", enabled=cfg.color_enabled))
        for k, v in resp.headers.items():
            print(f"{style(k, 'blue', enabled=cfg.color_enabled)}: {v}")

    if cfg.output:
        out = Path(cfg.output).expanduser()
        write_bytes(out, resp.content)
        print("\n" + style(f"[+] Body saved to: {out}", "green", enabled=cfg.color_enabled))
        return

    if cfg.method == "HEAD":
        return

    content_type = resp.headers.get("Content-Type", "")
    print("\n" + style("[Body]", "cyan", enabled=cfg.color_enabled))
    if cfg.pretty_json and "json" in content_type.lower():
        try:
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            return
        except ValueError:
            pass
    text = resp.text
    if len(text) > MAX_PRINT_BODY_CHARS:
        print(text[:MAX_PRINT_BODY_CHARS])
        print("\n" + style(f"<output truncated to {MAX_PRINT_BODY_CHARS} characters; use -o file to save everything>", "gray", enabled=cfg.color_enabled))
    else:
        print(text)


def save_cookie_file(path: str | Path, session: requests.Session) -> None:
    lines = ["# forgrequest cookie file", "# Format: name=value"]
    for cookie in session.cookies:
        lines.append(f"{cookie.name}={cookie.value}")
    write_text(path, "\n".join(lines) + "\n")


def response_headers_text(resp: requests.Response) -> str:
    lines = [f"HTTP {resp.status_code} {resp.reason}"]
    for k, v in resp.headers.items():
        lines.append(f"{k}: {v}")
    return "\r\n".join(lines) + "\r\n"


def build_report(result: ExecutionResult, cfg: RequestConfig) -> dict[str, Any]:
    resp = result.response
    request_headers = dict(result.prepared.headers)
    body_preview = body_to_bytes(result.prepared.body).decode("utf-8", errors="replace")[:MAX_REQUEST_BODY_PREVIEW]
    if cfg.redact_reports:
        request_headers = redact_mapping(request_headers)
        url = redact_url(result.prepared.url or "")
        body_preview = redact_text(body_preview)
    else:
        url = result.prepared.url or ""
    report: dict[str, Any] = {
        "tool": "forgrequest",
        "version": VERSION,
        "signature": SIGNATURE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "method": result.prepared.method,
            "url": url,
            "headers": request_headers,
            "body_bytes": len(body_to_bytes(result.prepared.body)),
            "body_preview": body_preview,
            "follow_redirects": cfg.follow_redirects,
            "verify_tls": cfg.verify_tls,
            "proxy_enabled": bool(cfg.proxy),
            "env_proxy_enabled": not cfg.no_env_proxy,
        },
        "execution": {
            "dry_run": cfg.dry_run,
            "elapsed_seconds": result.elapsed,
            "body_complete": result.body_complete,
            "warning": result.warning,
        },
    }
    if resp is not None:
        response_headers = dict(resp.headers)
        report["response"] = {
            "status_code": resp.status_code,
            "reason": resp.reason,
            "url": redact_url(resp.url) if cfg.redact_reports else resp.url,
            "headers": response_headers,
            "body_bytes": len(resp.content),
            "content_type": resp.headers.get("Content-Type", ""),
            "redirects": [
                {
                    "status_code": item.status_code,
                    "url": redact_url(item.url) if cfg.redact_reports else item.url,
                    "location": item.headers.get("Location", ""),
                }
                for item in resp.history
            ],
        }
    return report


def save_json_report(path: str | Path, report: dict[str, Any]) -> None:
    write_text(path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def save_html_report(path: str | Path, report: dict[str, Any]) -> None:
    title = "Forgery HTTP Request Report"
    request = report.get("request", {})
    response = report.get("response", {})
    execution = report.get("execution", {})
    status = response.get("status_code", "dry-run")
    json_report = html.escape(json.dumps(report, indent=2, ensure_ascii=False))
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#0b1020; --panel:#111a2e; --line:#233454; --text:#d8e6f3; --muted:#8fa7c2; --accent:#4dd4d7; --ok:#91d18b; --warn:#f3c969; }}
body {{ margin:0; font-family:Segoe UI, Roboto, Arial, sans-serif; background:var(--bg); color:var(--text); }}
main {{ max-width:1100px; margin:0 auto; padding:32px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:20px; margin:18px 0; box-shadow:0 16px 32px rgba(0,0,0,.25); }}
h1,h2 {{ margin-top:0; }}
h1 {{ color:var(--accent); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
.kv {{ border:1px solid var(--line); border-radius:12px; padding:12px; }}
.kv b {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
pre {{ overflow:auto; background:#07101f; border:1px solid var(--line); border-radius:12px; padding:16px; }}
.badge {{ display:inline-block; border:1px solid var(--accent); color:var(--accent); border-radius:999px; padding:4px 10px; }}
</style>
</head>
<body>
<main>
<h1>Forgery HTTP Request Report</h1>
<p class="badge">forgrequest v{html.escape(str(report.get('version', '')))} :: signature {html.escape(str(report.get('signature', '')))}</p>
<div class="card grid">
  <div class="kv"><b>Method</b>{html.escape(str(request.get('method', '')))}</div>
  <div class="kv"><b>Status</b>{html.escape(str(status))}</div>
  <div class="kv"><b>Elapsed</b>{html.escape(str(execution.get('elapsed_seconds', '')))}s</div>
  <div class="kv"><b>Body complete</b>{html.escape(str(execution.get('body_complete', '')))}</div>
</div>
<div class="card"><h2>Request URL</h2><pre>{html.escape(str(request.get('url', '')))}</pre></div>
<div class="card"><h2>Response URL</h2><pre>{html.escape(str(response.get('url', '')))}</pre></div>
<div class="card"><h2>Full metadata</h2><pre>{json_report}</pre></div>
</main>
</body>
</html>
"""
    write_text(path, document)


def save_session_artifacts(directory: str | Path, result: ExecutionResult, cfg: RequestConfig, report: dict[str, Any]) -> None:
    root = Path(directory).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        die(f"Could not create session directory {root}: {exc}")
    write_text(root / "request.raw", result.request_raw)
    write_text(root / "request.curl", result.request_curl + "\n")
    write_text(root / "request.py", result.request_python)
    save_json_report(root / "metadata.json", report)
    if result.response is not None:
        write_text(root / "response.headers", response_headers_text(result.response))
        write_bytes(root / "response.body", result.response.content)
    write_text(root / "README.txt", "Saved by forgrequest. This directory may contain sensitive request/response data.\n")


def handle_output_artifacts(result: ExecutionResult, cfg: RequestConfig, session: requests.Session) -> None:
    if cfg.save_prepared_request:
        write_text(cfg.save_prepared_request, result.request_raw)
        print(style(f"[+] Prepared request saved to: {cfg.save_prepared_request}", "green", enabled=cfg.color_enabled))
    if cfg.export_curl:
        print("\n" + style("[cURL]", "cyan", "bold", enabled=cfg.color_enabled))
        print(result.request_curl)
    if cfg.export_python:
        print("\n" + style("[Python requests]", "cyan", "bold", enabled=cfg.color_enabled))
        print(result.request_python)
    if cfg.save_cookies and result.response is not None:
        save_cookie_file(cfg.save_cookies, session)
        print(style(f"[+] Cookies saved to: {cfg.save_cookies}", "green", enabled=cfg.color_enabled))

    if cfg.report_json or cfg.report_html or cfg.save_session:
        report = build_report(result, cfg)
        if cfg.report_json:
            save_json_report(cfg.report_json, report)
            print(style(f"[+] JSON report saved to: {cfg.report_json}", "green", enabled=cfg.color_enabled))
        if cfg.report_html:
            save_html_report(cfg.report_html, report)
            print(style(f"[+] HTML report saved to: {cfg.report_html}", "green", enabled=cfg.color_enabled))
        if cfg.save_session:
            save_session_artifacts(cfg.save_session, result, cfg, report)
            print(style(f"[+] Session artifacts saved to: {cfg.save_session}", "green", enabled=cfg.color_enabled))


def send_request(cfg: RequestConfig) -> int:
    session = build_session(cfg)
    prepared = prepare_request(session, cfg)
    request_raw = prepared_to_raw(prepared, redact=False)
    request_curl = prepared_to_curl(prepared, redact=False)
    request_python = prepared_to_python(prepared, cfg, redact=False)

    if cfg.show_request or cfg.dry_run:
        print_prepared_request(prepared, cfg)

    if cfg.dry_run:
        result = ExecutionResult(None, 0.0, True, None, prepared, request_raw, request_curl, request_python)
        handle_output_artifacts(result, cfg, session)
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
        resp = session.send(prepared, timeout=cfg.timeout, allow_redirects=cfg.follow_redirects, **settings)
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
    result = ExecutionResult(resp, elapsed, body_complete, body_warning, prepared, request_raw, request_curl, request_python)
    handle_output_artifacts(result, cfg, session)
    if not body_complete:
        return 4
    return 0 if 200 <= resp.status_code < 400 else 3


def diff_files(argv: list[str]) -> int:
    parser = build_diff_parser()
    args = parser.parse_args(argv)
    left_path = Path(args.left).expanduser()
    right_path = Path(args.right).expanduser()
    if not left_path.is_file():
        die(f"File not found: {left_path}")
    if not right_path.is_file():
        die(f"File not found: {right_path}")
    left_bytes = left_path.read_bytes()
    right_bytes = right_path.read_bytes()
    left_text = left_bytes.decode("utf-8", errors="replace").splitlines()
    right_text = right_bytes.decode("utf-8", errors="replace").splitlines()
    same = left_bytes == right_bytes
    summary = {
        "left": str(left_path),
        "right": str(right_path),
        "same": same,
        "left_bytes": len(left_bytes),
        "right_bytes": len(right_bytes),
        "left_lines": len(left_text),
        "right_lines": len(right_text),
    }
    print("[Diff summary]")
    for key, value in summary.items():
        print(f"{key}: {value}")
    if not same and not args.no_body_diff:
        print("\n[Unified diff]")
        for line in difflib.unified_diff(left_text, right_text, fromfile=str(left_path), tofile=str(right_path), lineterm="", n=args.context):
            print(line)
    if args.json_output:
        save_json_report(args.json_output, summary)
        print(f"[+] Diff JSON saved to: {args.json_output}")
    return 0 if same else 3


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "diff":
        return diff_files(argv[1:])
    if argv and argv[0] == "web":
        from .webui import run_web
        return run_web(argv[1:])
    if argv and argv[0] == "update":
        from .updater import run_update
        return run_update(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"forgrequest {VERSION} :: signature {SIGNATURE}")
        return 0

    if args.init_config:
        write_sample_config(args.config)
        return 0

    args = apply_curl_to_args(args)
    cfg_file = load_config(args.config)
    if args.interactive or parse_bool(cfg_file.get("interactive", False)):
        args = interactive_collect(args, cfg_file)

    cfg = resolve_config(args)
    if cfg.show_logo:
        print(render_logo(cfg.color_enabled))
    return send_request(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
