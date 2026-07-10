#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Professional web interface for ForgRequest.

The web UI is a local operator console. It does not crawl, scan, or discover
URLs. Every action maps to the same CLI engine used by forgrequest.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import os
import tempfile
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from . import cli

DEFAULT_WEB_PORT = 7413
MAX_REQUEST_BYTES = 5 * 1024 * 1024


def _split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.replace("\r", "").split("\n") if line.strip()]


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in name).strip("._")
    return cleaned or "artifact"


class ForgRequestWebApp:
    def __init__(self, host: str, port: int, workspace: str | Path):
        self.host = host
        self.port = port
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def new_job_dir(self) -> Path:
        with self._lock:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            base = self.workspace / f"job-{stamp}-{int(time.time() * 1000) % 100000}"
            base.mkdir(parents=True, exist_ok=False)
            return base

    def artifact_url(self, path: Path) -> str:
        rel = path.resolve().relative_to(self.workspace)
        return "/artifacts/" + quote(str(rel).replace(os.sep, "/"))

    def build_cli_args(self, payload: dict[str, Any], job_dir: Path) -> tuple[list[str], dict[str, Any]]:
        args: list[str] = []
        artifacts: dict[str, Path] = {}

        def add_flag(flag: str, enabled: bool) -> None:
            if enabled:
                args.append(flag)

        def add_value(flag: str, value: Any) -> None:
            if value is not None and str(value).strip() != "":
                args.extend([flag, str(value)])

        def write_temp_file(name: str, content: str | bytes) -> Path:
            path = job_dir / _safe_name(name)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
            return path

        # The web console always keeps CLI output clean and readable.
        args.extend(["--no-logo", "--no-color"])

        if str(payload.get("configPath") or "").strip():
            args.extend(["--config", str(payload.get("configPath")).strip()])
        if bool(payload.get("initConfig")):
            init_path = job_dir / "forgrequest.generated.config"
            artifacts["forgrequest.generated.config"] = init_path
            args.extend(["--init-config", "--config", str(init_path)])

        request_mode = str(payload.get("requestMode") or "builder")
        url = str(payload.get("url") or "").strip()
        method = str(payload.get("method") or "").strip().upper()

        if request_mode == "raw":
            raw_text = str(payload.get("rawRequest") or "")
            if raw_text.strip():
                raw_path = write_temp_file("request.raw", raw_text)
                args.extend(["--raw-request", str(raw_path)])
            add_value("--raw-scheme", payload.get("rawScheme") or "https")
            if url:
                args.extend(["--url", url])
        elif request_mode == "curl":
            curl_text = str(payload.get("curlCommand") or "")
            if curl_text.strip():
                curl_path = write_temp_file("request.curl.input", curl_text)
                args.extend(["--from-curl", str(curl_path)])
            if url:
                args.extend(["--url", url])
            if method:
                args.extend(["--method", method])
        else:
            add_value("--url", url)
            add_value("--method", method)

        add_value("--user-agent", payload.get("userAgent"))
        for line in _split_lines(payload.get("headersText")):
            args.extend(["--headers", line])
        if str(payload.get("headersFileText") or "").strip():
            path = write_temp_file("headers.txt", str(payload.get("headersFileText")))
            args.extend(["--headers-file", str(path)])
        for line in _split_lines(payload.get("setHeaders")):
            args.extend(["--set-header", line])
        for line in _split_lines(payload.get("removeHeaders")):
            args.extend(["--remove-header", line])

        for line in _split_lines(payload.get("cookiesText")):
            args.extend(["--cookies", line])
        if str(payload.get("cookiesFileText") or "").strip():
            path = write_temp_file("cookies.txt", str(payload.get("cookiesFileText")))
            args.extend(["--cookies-file", str(path)])
        if str(payload.get("loadCookiesText") or "").strip():
            path = write_temp_file("load-cookies.txt", str(payload.get("loadCookiesText")))
            args.extend(["--load-cookies", str(path)])
        for line in _split_lines(payload.get("setCookies")):
            args.extend(["--set-cookie", line])
        for line in _split_lines(payload.get("removeCookies")):
            args.extend(["--remove-cookie", line])

        for line in _split_lines(payload.get("setQuery")):
            args.extend(["--set-query", line])
        for line in _split_lines(payload.get("removeQuery")):
            args.extend(["--remove-query", line])

        body_mode = str(payload.get("bodyMode") or "none")
        body_text = str(payload.get("bodyText") or "")
        if body_mode == "payload" and body_text != "":
            args.extend(["--payload", body_text])
        elif body_mode == "json" and body_text != "":
            args.extend(["--json", body_text])
        elif body_mode == "json-file" and body_text != "":
            path = write_temp_file("payload.json", body_text)
            args.extend(["--json-file", str(path)])
        elif body_mode == "form" and body_text != "":
            args.extend(["--form", body_text])
        elif body_mode == "form-file" and body_text != "":
            path = write_temp_file("form.txt", body_text)
            args.extend(["--form-file", str(path)])
        elif body_mode == "payload-file" and body_text != "":
            path = write_temp_file("payload.body", body_text)
            args.extend(["--payload-file", str(path)])
        elif body_mode == "binary-file" and body_text != "":
            path = write_temp_file("payload.bin", body_text.encode("utf-8"))
            args.extend(["--binary-file", str(path)])
        elif body_mode == "multipart":
            for line in _split_lines(body_text):
                args.extend(["--multipart", line])

        for line in _split_lines(payload.get("replaceBody")):
            args.extend(["--replace-body", line])
        for line in _split_lines(payload.get("variables")):
            args.extend(["--var", line])
        if str(payload.get("varsFileText") or "").strip():
            path = write_temp_file("vars.env", str(payload.get("varsFileText")))
            args.extend(["--vars-file", str(path)])

        add_value("--timeout", payload.get("timeout"))
        add_value("--proxy", payload.get("proxy"))
        add_flag("--include", bool(payload.get("include")))
        add_flag("--show-request", bool(payload.get("showRequest")))
        add_flag("--dry-run", bool(payload.get("dryRun")))
        add_flag("--raw", bool(payload.get("rawOutput")))
        add_flag("--no-redirects", bool(payload.get("noRedirects")))
        add_flag("--show-redirect-chain", bool(payload.get("showRedirectChain")))
        add_flag("--insecure", bool(payload.get("insecure")))
        add_flag("--no-env-proxy", bool(payload.get("noEnvProxy")))
        add_flag("--no-redact-reports", bool(payload.get("noRedactReports")))

        if bool(payload.get("exportCurl")):
            args.append("--export-curl")
        if bool(payload.get("exportPython")):
            args.append("--export-python")
        if bool(payload.get("savePreparedRequest")):
            path = job_dir / "prepared-request.raw"
            artifacts["prepared-request.raw"] = path
            args.extend(["--save-prepared-request", str(path)])
        if bool(payload.get("saveOutput")):
            path = job_dir / "response.body"
            artifacts["response.body"] = path
            args.extend(["--output", str(path)])
        if bool(payload.get("saveCookies")):
            path = job_dir / "cookies.txt"
            artifacts["cookies.txt"] = path
            args.extend(["--save-cookies", str(path)])
        if bool(payload.get("cookieJar")):
            path = job_dir / "cookie-jar.txt"
            if str(payload.get("cookieJarText") or "").strip():
                path.write_text(str(payload.get("cookieJarText")), encoding="utf-8")
            artifacts["cookie-jar.txt"] = path
            args.extend(["--cookie-jar", str(path)])
        if bool(payload.get("reportJson")):
            path = job_dir / "report.json"
            artifacts["report.json"] = path
            args.extend(["--report-json", str(path)])
        if bool(payload.get("reportHtml")):
            path = job_dir / "report.html"
            artifacts["report.html"] = path
            args.extend(["--report-html", str(path)])
        if bool(payload.get("saveSession")):
            path = job_dir / "session"
            artifacts["session"] = path
            args.extend(["--save-session", str(path)])

        return args, artifacts

    def run_cli(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_dir = self.new_job_dir()
        args, planned_artifacts = self.build_cli_args(payload, job_dir)
        out = io.StringIO()
        err = io.StringIO()
        exit_code = 0
        started = time.perf_counter()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                exit_code = int(cli.main(args))
            except SystemExit as exc:
                try:
                    exit_code = int(exc.code or 0)
                except (TypeError, ValueError):
                    exit_code = 1
            except Exception as exc:  # defensive guard for web mode
                exit_code = 1
                print(f"[!] Unexpected web execution error: {exc}", file=err)
        elapsed = time.perf_counter() - started
        artifacts = []
        for path in sorted(job_dir.rglob("*")):
            if path.is_file():
                artifacts.append({
                    "name": str(path.relative_to(job_dir)),
                    "url": self.artifact_url(path),
                    "size": path.stat().st_size,
                })
        # Include planned directories even when they only contain files listed above.
        for name, path in planned_artifacts.items():
            if path.is_dir():
                artifacts.append({"name": name + "/", "url": self.artifact_url(path), "size": 0})
        return {
            "exit_code": exit_code,
            "elapsed_seconds": round(elapsed, 4),
            "command": "forgrequest " + " ".join(cli.shlex.quote(part) for part in args),
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
            "artifacts": artifacts,
            "job": job_dir.name,
        }

    def run_diff(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_dir = self.new_job_dir()
        left = job_dir / "left.txt"
        right = job_dir / "right.txt"
        left.write_text(str(payload.get("left") or ""), encoding="utf-8")
        right.write_text(str(payload.get("right") or ""), encoding="utf-8")
        json_path = job_dir / "diff.json"
        args = ["diff", str(left), str(right), "--json", str(json_path)]
        if payload.get("noBodyDiff"):
            args.append("--no-body-diff")
        if payload.get("context"):
            args.extend(["--context", str(payload.get("context"))])
        out = io.StringIO()
        err = io.StringIO()
        exit_code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                exit_code = int(cli.main(args))
            except SystemExit as exc:
                try:
                    exit_code = int(exc.code or 0)
                except (TypeError, ValueError):
                    exit_code = 1
        artifacts = []
        for path in sorted(job_dir.rglob("*")):
            if path.is_file():
                artifacts.append({"name": path.name, "url": self.artifact_url(path), "size": path.stat().st_size})
        return {
            "exit_code": exit_code,
            "command": "forgrequest " + " ".join(cli.shlex.quote(part) for part in args),
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
            "artifacts": artifacts,
            "job": job_dir.name,
        }


INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ForgRequest Web Console</title>
<style>
:root{
  --bg:#07111f; --bg2:#0c182b; --panel:#111e33; --panel2:#0d1728; --line:#203755;
  --text:#e8f3ff; --muted:#95a8be; --soft:#132740; --accent:#35d6d0; --accent2:#78f2d4;
  --danger:#ff6b8a; --warn:#ffd166; --ok:#7bd88f; --shadow:0 22px 60px rgba(0,0,0,.35);
}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 15% -20%,rgba(53,214,208,.22),transparent 34%),radial-gradient(circle at 85% 0,rgba(120,242,212,.12),transparent 30%),linear-gradient(135deg,var(--bg),#040812 60%);color:var(--text);font-family:Inter,Segoe UI,Roboto,Arial,sans-serif;min-height:100vh} 
header{position:sticky;top:0;z-index:8;background:rgba(7,17,31,.86);backdrop-filter:blur(18px);border-bottom:1px solid rgba(53,214,208,.18)}
.nav{max-width:1500px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;gap:18px;justify-content:space-between}.brand{display:flex;align-items:center;gap:14px}.mark{width:48px;height:48px;border-radius:16px;background:linear-gradient(135deg,var(--accent),#1a7989);display:grid;place-items:center;color:#031018;font-weight:900;box-shadow:0 0 36px rgba(53,214,208,.32)}.title h1{font-size:18px;margin:0}.title p{margin:4px 0 0;color:var(--muted);font-size:13px}.pill{border:1px solid rgba(53,214,208,.35);color:var(--accent2);padding:7px 11px;border-radius:999px;font-size:12px;background:rgba(53,214,208,.08)}
.shell{max-width:1500px;margin:0 auto;padding:28px 24px 70px;display:grid;grid-template-columns:300px 1fr;gap:22px}.side{position:sticky;top:92px;align-self:start;background:rgba(17,30,51,.82);border:1px solid var(--line);border-radius:24px;padding:18px;box-shadow:var(--shadow)}.side button{width:100%;text-align:left;border:1px solid transparent;background:transparent;color:var(--muted);border-radius:14px;padding:13px 14px;margin:4px 0;cursor:pointer;font-weight:650}.side button:hover,.side button.active{color:var(--text);border-color:rgba(53,214,208,.28);background:linear-gradient(90deg,rgba(53,214,208,.15),rgba(53,214,208,.03))}.side .hint{font-size:12px;color:var(--muted);line-height:1.55;padding:14px;border-top:1px solid var(--line);margin-top:12px}
.main{display:grid;gap:18px}.hero{border:1px solid rgba(53,214,208,.22);border-radius:28px;padding:24px;background:linear-gradient(135deg,rgba(17,30,51,.9),rgba(9,17,31,.9));box-shadow:var(--shadow);overflow:hidden;position:relative}.hero:after{content:"";position:absolute;inset:auto -80px -160px auto;width:360px;height:360px;background:radial-gradient(circle,rgba(53,214,208,.18),transparent 65%)}.hero h2{margin:0 0 8px;font-size:30px;letter-spacing:-.04em}.hero p{color:var(--muted);line-height:1.6;max-width:920px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:rgba(17,30,51,.88);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 14px 38px rgba(0,0,0,.24)}.card h3{margin:0 0 13px;font-size:15px;color:#cceaff}.span12{grid-column:span 12}.span8{grid-column:span 8}.span6{grid-column:span 6}.span4{grid-column:span 4}.span3{grid-column:span 3}.span2{grid-column:span 2}
label{display:block;color:var(--muted);font-size:12px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;margin:0 0 7px}input,select,textarea{width:100%;background:#071424;border:1px solid #284260;color:var(--text);border-radius:14px;padding:12px 13px;outline:none;font:14px ui-sans-serif,system-ui}textarea{min-height:120px;resize:vertical;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px;line-height:1.45}input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(53,214,208,.12)}.row{display:grid;grid-template-columns:repeat(12,1fr);gap:12px}.checkgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.check{display:flex;align-items:center;gap:9px;border:1px solid #243b59;border-radius:14px;padding:10px 12px;background:rgba(7,20,36,.64);color:#c9d8ea;font-size:13px}.check input{width:auto} .actions{display:flex;gap:12px;flex-wrap:wrap}.btn{border:0;border-radius:15px;padding:12px 16px;cursor:pointer;font-weight:800;letter-spacing:.01em}.primary{background:linear-gradient(135deg,var(--accent),#1ea9b2);color:#031018;box-shadow:0 12px 28px rgba(53,214,208,.25)}.secondary{background:#162940;color:var(--text);border:1px solid #2b4564}.danger{background:rgba(255,107,138,.14);color:#ffc5d0;border:1px solid rgba(255,107,138,.4)}.btn:disabled{opacity:.55;cursor:not-allowed}.panel{display:none}.panel.active{display:block}.terminal{background:#040a13;border:1px solid #1d3554;border-radius:22px;padding:0;overflow:hidden}.termbar{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#08182b;border-bottom:1px solid #1d3554}.lights{display:flex;gap:7px}.dot{width:10px;height:10px;border-radius:50%;background:#56697d}.dot:nth-child(1){background:#ff6b8a}.dot:nth-child(2){background:#ffd166}.dot:nth-child(3){background:#7bd88f}.status{font-size:12px;color:var(--muted)}pre{margin:0;padding:16px;white-space:pre-wrap;overflow:auto;max-height:560px;color:#d9f7ff;font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}.artifacts{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.artifact{display:inline-flex;gap:7px;align-items:center;padding:8px 10px;border:1px solid #2b4564;background:#0d1a2c;border-radius:999px;color:#bdeffd;text-decoration:none;font-size:12px}.mini{font-size:12px;color:var(--muted);line-height:1.5}.kbd{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;color:#a6fff3}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:1050px){.shell{grid-template-columns:1fr}.side{position:relative;top:0}.side button{display:inline-block;width:auto}.span8,.span6,.span4,.span3,.span2{grid-column:span 12}.two{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><div class="nav"><div class="brand"><div class="mark">F&gt;_</div><div class="title"><h1>ForgRequest Web Console</h1><p>Local HTTP request replication, modification, reports and diff UI</p></div></div><div class="pill" id="version-pill">v</div></div></header>
<div class="shell">
  <aside class="side">
    <button class="tab active" data-panel="builder">Request Builder</button>
    <button class="tab" data-panel="replay">Raw / cURL Replay</button>
    <button class="tab" data-panel="modifiers">Modifiers</button>
    <button class="tab" data-panel="execution">Execution & Reports</button>
    <button class="tab" data-panel="diff">Response Diff</button>
    <button class="tab" data-panel="help">Feature Map</button>
    <div class="hint">Every web action maps to the existing CLI engine. ForgRequest remains a manual HTTP client, not a crawler or scanner.</div>
  </aside>
  <main class="main">
    <section class="hero"><h2>Build, replay and document individual HTTP requests.</h2><p>Use the UI to configure methods, headers, cookies, body helpers, raw requests, cURL imports, redirect visibility, cookie jars, JSON/HTML reports and session evidence without leaving the browser.</p></section>
    <form id="request-form">
      <section id="builder" class="panel active"><div class="grid">
        <div class="card span8"><h3>Target</h3><div class="row"><div class="span3"><label>Method</label><select name="method"><option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option><option>HEAD</option><option>OPTIONS</option><option>TRACE</option></select></div><div class="span9"><label>URL</label><input name="url" placeholder="https://example.com/api/resource"></div></div><p class="mini">The URL is never stored in the config file. Use variables like <span class="kbd">{{BASE_URL}}</span> with the Variables panel.</p></div>
        <div class="card span4"><h3>Network</h3><label>Timeout seconds</label><input name="timeout" type="number" min="0.1" step="0.1" placeholder="30"><label>Proxy</label><input name="proxy" placeholder="http://127.0.0.1:8080"></div>
        <div class="card span6"><h3>Headers</h3><textarea name="headersText" placeholder="Accept: application/json&#10;X-Test: 1"></textarea></div>
        <div class="card span6"><h3>Cookies</h3><textarea name="cookiesText" placeholder="session=abc; theme=dark"></textarea></div>
        <div class="card span12"><h3>Body helper</h3><div class="row"><div class="span3"><label>Body mode</label><select name="bodyMode"><option value="none">None</option><option value="payload">Raw payload string</option><option value="json">JSON string</option><option value="json-file">JSON file simulation</option><option value="form">Form string</option><option value="form-file">Form file simulation</option><option value="payload-file">Payload file simulation</option><option value="binary-file">Binary file simulation</option><option value="multipart">Multipart fields</option></select></div><div class="span9"><label>Body content or multipart lines</label><textarea name="bodyText" placeholder='{"username":"test@example.com","password":"change-me"}'></textarea></div></div></div>
      </div></section>
      <section id="replay" class="panel"><div class="grid">
        <div class="card span3"><h3>Mode</h3><label>Request source</label><select name="requestMode"><option value="builder">Builder fields</option><option value="raw">Raw HTTP request</option><option value="curl">cURL command</option></select><label>Raw request scheme</label><select name="rawScheme"><option>https</option><option>http</option></select></div>
        <div class="card span9"><h3>Raw HTTP/1.1 request</h3><textarea name="rawRequest" placeholder="POST /api/login HTTP/1.1&#10;Host: example.com&#10;Content-Type: application/json&#10;&#10;{&quot;a&quot;:1}"></textarea></div>
        <div class="card span12"><h3>Import from cURL</h3><textarea name="curlCommand" placeholder="curl 'https://example.com/api' -X POST -H 'Content-Type: application/json' --data-raw '{&quot;a&quot;:1}'"></textarea></div>
        <div class="card span6"><h3>Header file simulation</h3><textarea name="headersFileText" placeholder="User-Agent: Mozilla/5.0&#10;X-Bug-Bounty: H1-imr"></textarea></div>
        <div class="card span6"><h3>Cookie file simulation</h3><textarea name="cookiesFileText" placeholder="Cookie: session=abc; theme=dark"></textarea></div>
        <div class="card span12"><h3>Load cookies alias</h3><textarea name="loadCookiesText" placeholder="session=abc&#10;csrf=token"></textarea><p class="mini">Maps to <span class="kbd">--load-cookies</span>. Use this when testing cookie-jar style flows from the Web Console.</p></div>
      </div></section>
      <section id="modifiers" class="panel"><div class="grid">
        <div class="card span6"><h3>Set headers</h3><textarea name="setHeaders" placeholder="Authorization: Bearer {{TOKEN}}&#10;X-Test: 1"></textarea></div>
        <div class="card span6"><h3>Remove headers</h3><textarea name="removeHeaders" placeholder="X-Powered-By&#10;Server"></textarea></div>
        <div class="card span6"><h3>Set cookies</h3><textarea name="setCookies" placeholder="session={{SESSION}}&#10;theme=dark"></textarea></div>
        <div class="card span6"><h3>Remove cookies</h3><textarea name="removeCookies" placeholder="tracking_id"></textarea></div>
        <div class="card span6"><h3>Set query params</h3><textarea name="setQuery" placeholder="debug=true&#10;id=123"></textarea></div>
        <div class="card span6"><h3>Remove query params</h3><textarea name="removeQuery" placeholder="utm_source&#10;cachebuster"></textarea></div>
        <div class="card span6"><h3>Body replacements</h3><textarea name="replaceBody" placeholder="old=new&#10;guest=admin"></textarea></div>
        <div class="card span6"><h3>Variables</h3><textarea name="variables" placeholder="BASE_URL=https://example.com&#10;TOKEN=abc123&#10;SESSION=s1"></textarea><label>Vars file simulation</label><textarea name="varsFileText" placeholder="USER_ID=1001"></textarea></div>
      </div></section>
      <section id="execution" class="panel"><div class="grid">
        <div class="card span12"><h3>Execution flags</h3><div class="checkgrid">
          <label class="check"><input type="checkbox" name="include"> Include response headers</label><label class="check"><input type="checkbox" name="showRequest" checked> Show prepared request</label><label class="check"><input type="checkbox" name="dryRun"> Dry-run</label><label class="check"><input type="checkbox" name="rawOutput"> Raw output</label><label class="check"><input type="checkbox" name="noRedirects"> No redirects</label><label class="check"><input type="checkbox" name="showRedirectChain" checked> Redirect chain</label><label class="check"><input type="checkbox" name="insecure"> Insecure TLS</label><label class="check"><input type="checkbox" name="noEnvProxy" checked> Ignore env proxy</label><label class="check"><input type="checkbox" name="exportCurl" checked> Export cURL</label><label class="check"><input type="checkbox" name="exportPython"> Export Python</label><label class="check"><input type="checkbox" name="savePreparedRequest"> Save prepared raw request</label><label class="check"><input type="checkbox" name="saveOutput"> Save response body</label><label class="check"><input type="checkbox" name="saveCookies"> Save cookies</label><label class="check"><input type="checkbox" name="cookieJar"> Use cookie jar</label><label class="check"><input type="checkbox" name="reportJson" checked> JSON report</label><label class="check"><input type="checkbox" name="reportHtml" checked> HTML report</label><label class="check"><input type="checkbox" name="saveSession"> Save session</label><label class="check"><input type="checkbox" name="noRedactReports"> No report redaction</label>
        </div></div>
        <div class="card span6"><h3>Cookie jar seed</h3><textarea name="cookieJarText" placeholder="session=abc"></textarea></div>
        <div class="card span6"><h3>Configuration</h3><label>Config path</label><input name="configPath" placeholder="/path/to/forgrequest.config"><div style="height:10px"></div><label class="check"><input type="checkbox" name="initConfig"> Generate sample config artifact</label><p class="mini">Maps to <span class="kbd">--config</span> and <span class="kbd">--init-config</span>. Generated configs are saved in the web workspace.</p></div>
        <div class="card span12"><div class="actions"><button type="submit" class="btn primary" id="run-btn">Run request</button><button type="button" class="btn secondary" id="dry-btn">Preview dry-run</button><button type="reset" class="btn danger">Reset form</button></div></div>
      </div></section>
    </form>
    <section id="diff" class="panel"><div class="grid"><div class="card span12"><h3>Compare two response bodies or files pasted as text</h3><div class="two"><textarea id="diff-left" placeholder="Left response"></textarea><textarea id="diff-right" placeholder="Right response"></textarea></div><div class="actions" style="margin-top:12px"><button class="btn primary" id="diff-btn">Run diff</button><label class="check"><input type="checkbox" id="diff-nobody"> Summary only</label></div></div></div></section>
    <section id="help" class="panel"><div class="grid"><div class="card span12"><h3>Feature map</h3><p class="mini">CLI parity covered in this console: URL/method, version-backed execution, config path, sample config generation, headers, header files, cookies, cookie files, load/save cookies, raw request replay, cURL import, payload/json/form/file/multipart/binary body helpers, body replace, variables, query modifiers, request exports, reports, session evidence, redirect chain, proxy/TLS/env-proxy controls, cookie jar and diff.</p><p class="mini">The web server binds to localhost by default. Do not expose it publicly because it can send requests and save artifacts on behalf of the local operator.</p></div></div></section>
    <section class="terminal"><div class="termbar"><div class="lights"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div><div class="status" id="run-status">ready</div></div><pre id="output">Use the panels above, then run a request. Output, generated command and artifacts will appear here.</pre><div class="artifacts" id="artifacts"></div></section>
  </main>
</div>
<script>
const $ = (s, root=document) => root.querySelector(s); const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
$$('.tab').forEach(btn=>btn.addEventListener('click',()=>{ $$('.tab').forEach(b=>b.classList.remove('active')); $$('.panel').forEach(p=>p.classList.remove('active')); btn.classList.add('active'); $('#'+btn.dataset.panel).classList.add('active'); }));
function collectForm(dryOverride=false){ const f=$('#request-form'); const data={}; new FormData(f).forEach((v,k)=>{ if(data[k]) data[k]+='\n'+v; else data[k]=v; }); $$('input[type=checkbox]', f).forEach(i=>data[i.name]=i.checked); if(dryOverride) data.dryRun=true; return data; }
function renderResult(r){ $('#run-status').textContent = `exit ${r.exit_code} · ${r.elapsed_seconds||''}s · ${r.job||''}`; let text=`$ ${r.command}\n\n[exit_code] ${r.exit_code}\n\n`; if(r.stdout) text += `[stdout]\n${r.stdout}\n`; if(r.stderr) text += `[stderr]\n${r.stderr}\n`; $('#output').textContent=text; const a=$('#artifacts'); a.innerHTML=''; (r.artifacts||[]).forEach(item=>{ const link=document.createElement('a'); link.className='artifact'; link.href=item.url; link.target='_blank'; link.textContent=`⬇ ${item.name} (${item.size} bytes)`; a.appendChild(link); }); }
async function postJSON(url, payload){ $('#run-status').textContent='running...'; const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const data=await res.json(); renderResult(data); }
$('#request-form').addEventListener('submit',e=>{ e.preventDefault(); postJSON('/api/run', collectForm(false)); });
$('#dry-btn').addEventListener('click',()=>postJSON('/api/run', collectForm(true)));
$('#diff-btn').addEventListener('click',()=>postJSON('/api/diff',{left:$('#diff-left').value,right:$('#diff-right').value,noBodyDiff:$('#diff-nobody').checked,context:3}));
fetch('/api/info').then(r=>r.json()).then(info=>{$('#version-pill').textContent=`v${info.version} :: ${info.signature}`});
</script>
</body>
</html>'''


class ForgRequestHandler(BaseHTTPRequestHandler):
    server_version = "ForgRequestWeb/1.6"

    @property
    def app(self) -> ForgRequestWebApp:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {fmt % args}")

    def _send(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        self._send(status, json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length > MAX_REQUEST_BYTES:
            raise ValueError("Request too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/info":
            self._json(200, {"version": cli.VERSION, "signature": cli.SIGNATURE, "workspace": str(self.app.workspace)})
            return
        if parsed.path.startswith("/artifacts/"):
            rel = unquote(parsed.path[len("/artifacts/"):])
            try:
                target = (self.app.workspace / rel).resolve()
                target.relative_to(self.app.workspace)
            except Exception:
                self._json(403, {"error": "Forbidden path"})
                return
            if target.is_dir():
                items = []
                for item in sorted(target.rglob("*")):
                    if item.is_file():
                        items.append(f'<li><a href="{html.escape(self.app.artifact_url(item))}">{html.escape(str(item.relative_to(target)))}</a> ({item.stat().st_size} bytes)</li>')
                page = "<!doctype html><meta charset='utf-8'><title>Artifacts</title><body style='font-family:Arial;background:#07111f;color:#e8f3ff'><h1>Artifacts</h1><ul>" + "".join(items) + "</ul></body>"
                self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
                return
            if not target.is_file():
                self._json(404, {"error": "Artifact not found"})
                return
            content_type = "application/octet-stream"
            if target.suffix.lower() in {".html", ".htm"}:
                content_type = "text/html; charset=utf-8"
            elif target.suffix.lower() in {".json"}:
                content_type = "application/json; charset=utf-8"
            elif target.suffix.lower() in {".txt", ".raw", ".curl", ".py", ".headers"}:
                content_type = "text/plain; charset=utf-8"
            self._send(200, target.read_bytes(), content_type)
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/api/run":
                self._json(200, self.app.run_cli(payload))
                return
            if self.path == "/api/diff":
                self._json(200, self.app.run_diff(payload))
                return
            self._json(404, {"error": "Not found"})
        except json.JSONDecodeError as exc:
            self._json(400, {"error": f"Invalid JSON: {exc}"})
        except ValueError as exc:
            self._json(413, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": f"Unexpected web error: {exc}"})


class ForgRequestHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], app: ForgRequestWebApp):
        super().__init__(server_address, handler_cls)
        self.app = app


def build_web_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgrequest web",
        description="Launch the local ForgRequest Web Console.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Web interface bind host. Keep localhost unless you understand the risk.")
    parser.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help="Web interface TCP port.")
    parser.add_argument("--workspace", default=str(Path.home() / ".forgrequest" / "web-artifacts"), help="Directory for web-generated temporary files and artifacts.")
    parser.add_argument("--open", action="store_true", help="Open the web UI in the default browser.")
    return parser


def run_web(argv: list[str] | None = None) -> int:
    parser = build_web_parser()
    args = parser.parse_args(argv)
    app = ForgRequestWebApp(args.host, args.port, args.workspace)
    server = ForgRequestHTTPServer((args.host, args.port), ForgRequestHandler, app)
    url = f"http://{args.host}:{args.port}/"
    print(f"[+] ForgRequest Web Console v{cli.VERSION} started")
    print(f"[+] URL: {url}")
    print(f"[+] Workspace: {app.workspace}")
    print("[!] Keep this interface bound to localhost. It can send HTTP requests from your machine.")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Web Console stopped")
    finally:
        server.server_close()
    return 0
