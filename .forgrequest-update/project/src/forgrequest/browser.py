#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional JavaScript-rendering browser engine for ForgRequest.

This module performs one operator-supplied page navigation. It does not crawl,
discover links, or scan a site. Playwright is loaded lazily so the normal HTTP
client remains usable even when browser support is not installed.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class BrowserSupportError(RuntimeError):
    """Raised when browser execution cannot be started or completed."""


@dataclass
class BrowserHistoryResponse:
    status_code: int
    reason: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes = b""
    history: list[Any] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


@dataclass
class BrowserResponse(BrowserHistoryResponse):
    pass


@dataclass
class BrowserRunResult:
    response: BrowserResponse
    title: str
    browser_name: str
    headless: bool
    wait_until: str
    console_messages: list[dict[str, str]]
    page_errors: list[str]
    cookies: list[dict[str, Any]]
    storage_state: dict[str, Any]
    javascript_enabled: bool = True


def _system_browser_candidates(engine: str) -> list[str]:
    if engine == "chromium":
        return [
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
            "chrome",
            "msedge",
            "microsoft-edge",
        ]
    if engine == "firefox":
        return ["firefox", "firefox-esr"]
    return []


def find_system_browser(engine: str) -> str | None:
    for candidate in _system_browser_candidates(engine):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    if os.name == "nt" and engine == "chromium":
        roots = [os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")]
        suffixes = [
            Path("Google/Chrome/Application/chrome.exe"),
            Path("Microsoft/Edge/Application/msedge.exe"),
        ]
        for root in filter(None, roots):
            for suffix in suffixes:
                candidate = Path(str(root)) / suffix
                if candidate.is_file():
                    return str(candidate)
    return None


def browser_support_info() -> dict[str, Any]:
    try:
        import importlib.metadata
        import playwright  # noqa: F401

        version = importlib.metadata.version("playwright")
        installed = True
    except Exception:
        version = ""
        installed = False
    return {
        "playwright_installed": installed,
        "playwright_version": version,
        "system_chromium": find_system_browser("chromium") or "",
        "system_firefox": find_system_browser("firefox") or "",
    }


def parse_viewport(value: str) -> dict[str, int]:
    text = (value or "1366x768").lower().strip()
    if "x" not in text:
        raise BrowserSupportError("Invalid browser viewport. Use WIDTHxHEIGHT, for example 1366x768.")
    width_text, height_text = text.split("x", 1)
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError as exc:
        raise BrowserSupportError("Invalid browser viewport. Width and height must be integers.") from exc
    if width < 320 or height < 240 or width > 10000 or height > 10000:
        raise BrowserSupportError("Browser viewport must be between 320x240 and 10000x10000.")
    return {"width": width, "height": height}


def _reason(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return ""


def _headers_to_dict(headers: dict[str, str] | None) -> dict[str, str]:
    return {str(k): str(v) for k, v in (headers or {}).items()}


def _build_redirect_history(navigation_response: Any) -> list[BrowserHistoryResponse]:
    if navigation_response is None:
        return []
    requests: list[Any] = []
    current = navigation_response.request
    while current is not None:
        requests.append(current)
        current = current.redirected_from
    requests.reverse()

    history: list[BrowserHistoryResponse] = []
    for request in requests[:-1]:
        try:
            response = request.response()
        except Exception:
            response = None
        if response is None:
            continue
        history.append(
            BrowserHistoryResponse(
                status_code=int(response.status),
                reason=_reason(int(response.status)),
                url=str(response.url),
                headers=_headers_to_dict(response.headers),
            )
        )
    return history


def _cookie_entries(cookies: dict[str, str], url: str) -> list[dict[str, Any]]:
    if not cookies:
        return []
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return [{"name": name, "value": value, "url": origin} for name, value in cookies.items()]


def run_browser_navigation(cfg: Any) -> BrowserRunResult:
    if str(cfg.method).upper() != "GET":
        raise BrowserSupportError(
            "JavaScript browser mode supports GET navigation only. Use the standard HTTP engine for POST, PUT, PATCH, DELETE, HEAD, OPTIONS, or TRACE."
        )
    if not cfg.follow_redirects:
        raise BrowserSupportError("--no-redirects is not supported in JavaScript browser mode because page navigation follows browser redirects.")

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserSupportError(
            "Browser support requires Playwright. Run 'forgrequest browser-install chromium' or install the project requirements."
        ) from exc

    console_messages: list[dict[str, str]] = []
    page_errors: list[str] = []
    viewport = parse_viewport(cfg.browser_viewport)
    storage_state: str | dict[str, Any] | None = None
    if cfg.browser_storage_state:
        path = Path(cfg.browser_storage_state).expanduser()
        if not path.is_file():
            raise BrowserSupportError(f"Browser storage-state file not found: {path}")
        storage_state = str(path)

    extra_headers = {
        key: value
        for key, value in cfg.headers.items()
        if key.lower() not in {"host", "cookie", "content-length", "user-agent"}
    }
    proxy = {"server": cfg.proxy} if cfg.proxy else None
    launch_options: dict[str, Any] = {"headless": cfg.browser_headless}
    browser_args: list[str] = []
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        browser_args.extend(["--no-sandbox", "--disable-setuid-sandbox"])
    if cfg.no_env_proxy and not proxy and cfg.browser_engine == "chromium":
        browser_args.append("--no-proxy-server")
    if browser_args:
        launch_options["args"] = browser_args
    if proxy:
        launch_options["proxy"] = proxy
    if cfg.browser_executable:
        executable = Path(cfg.browser_executable).expanduser()
        if not executable.is_file():
            raise BrowserSupportError(f"Browser executable not found: {executable}")
        launch_options["executable_path"] = str(executable)

    timeout_ms = max(1, int(float(cfg.timeout) * 1000))

    with sync_playwright() as playwright:
        browser_type = getattr(playwright, cfg.browser_engine)
        browser = None
        try:
            try:
                browser = browser_type.launch(**launch_options)
            except PlaywrightError as first_error:
                if "executable_path" in launch_options:
                    raise
                fallback = find_system_browser(cfg.browser_engine)
                if not fallback:
                    raise BrowserSupportError(
                        f"Could not launch the {cfg.browser_engine} browser: {first_error}. "
                        f"Run 'forgrequest browser-install {cfg.browser_engine}'."
                    ) from first_error
                launch_options["executable_path"] = fallback
                browser = browser_type.launch(**launch_options)

            context_options: dict[str, Any] = {
                "ignore_https_errors": not cfg.verify_tls,
                "java_script_enabled": True,
                "viewport": viewport,
                "extra_http_headers": extra_headers,
            }
            if cfg.user_agent:
                context_options["user_agent"] = cfg.user_agent
            if storage_state is not None:
                context_options["storage_state"] = storage_state

            context = browser.new_context(**context_options)
            cookie_entries = _cookie_entries(cfg.cookies, cfg.url)
            if cookie_entries:
                context.add_cookies(cookie_entries)

            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.on(
                "console",
                lambda message: console_messages.append(
                    {"type": str(message.type), "text": str(message.text)}
                ),
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            try:
                navigation_response = page.goto(
                    cfg.url,
                    wait_until=cfg.browser_wait_until,
                    timeout=timeout_ms,
                )
                if cfg.browser_wait_selector:
                    page.wait_for_selector(cfg.browser_wait_selector, timeout=timeout_ms)
                if cfg.browser_wait_ms:
                    page.wait_for_timeout(cfg.browser_wait_ms)
            except PlaywrightTimeoutError as exc:
                raise BrowserSupportError(f"Browser navigation timed out after {cfg.timeout}s: {exc}") from exc
            except PlaywrightError as exc:
                raise BrowserSupportError(f"Browser navigation failed: {exc}") from exc

            rendered_html = page.content().encode("utf-8")
            final_url = page.url
            title = page.title()
            if navigation_response is None:
                status = 0
                headers: dict[str, str] = {}
            else:
                status = int(navigation_response.status)
                headers = _headers_to_dict(navigation_response.headers)
            response = BrowserResponse(
                status_code=status,
                reason=_reason(status),
                url=final_url,
                headers=headers,
                content=rendered_html,
                history=_build_redirect_history(navigation_response),
            )
            cookies = context.cookies()
            state = context.storage_state()
            context.close()
            return BrowserRunResult(
                response=response,
                title=title,
                browser_name=cfg.browser_engine,
                headless=cfg.browser_headless,
                wait_until=cfg.browser_wait_until,
                console_messages=console_messages,
                page_errors=page_errors,
                cookies=cookies,
                storage_state=state,
            )
        finally:
            if browser is not None:
                browser.close()
