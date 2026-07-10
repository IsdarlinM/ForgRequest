# Forgery HTTP Request

**Forgery HTTP Request** (`forgrequest`) is an advanced Python HTTP client for authorized request replay, request modification, endpoint behavior validation, labs, CTFs, internal audits, and in-scope bug bounty work.

It is intentionally **not a crawler** and **not a vulnerability scanner**. It does not discover URLs, spider applications, fuzz targets, or run aggressive automated tests. Its purpose is to help an operator build, replay, modify, compare, and document individual HTTP requests with high reproducibility.

```text
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

             Forgery HTTP Request v1.5.0  ::  signature: immroa
```

When ANSI color is enabled, the logo is rendered with **one single cyan color** to keep terminal output stable and professional.

> Responsible use: use this tool only on systems you own, controlled labs, authorized audits, CTFs, or bug bounty targets where you have explicit permission.

---

## What changed in v1.5.0

- Raw HTTP/1.1 request import and replay with `--raw-request`.
- Import requests from cURL with `--from-curl`.
- Export prepared requests as cURL or Python `requests` snippets.
- Fast request modifiers: `--set-header`, `--remove-header`, `--set-cookie`, `--remove-cookie`, `--set-query`, `--remove-query`.
- Body helpers: `--json`, `--json-file`, `--form`, `--form-file`, `--binary-file`, `--multipart`, `--replace-body`.
- Cookie jar workflow with `--load-cookies`, `--save-cookies`, and `--cookie-jar`.
- Template variables using `{{NAME}}` with `--var` and `--vars-file`.
- Redirect chain display with `--show-redirect-chain`.
- Environment proxy isolation with `--no-env-proxy`.
- JSON and HTML execution reports with `--report-json` and `--report-html`.
- Evidence/session export with `--save-session`.
- Local file comparison command: `forgrequest diff file-a file-b`.
- Improved redaction in prepared-request previews and reports.
- Improved documentation in English.

---

## Project layout

```text
ForgeryHttpRequest/
├── forgrequest.py                    # Compatibility launcher
├── pyproject.toml                     # Optional package metadata / console script
├── requirements.txt                   # Python dependencies
├── README.md                          # Main documentation
├── config/
│   └── forgrequest.config             # Default .config file
├── docs/
│   └── README.md                      # Documentation copy
├── examples/
│   ├── login_head.example.txt         # Header-file example
│   └── payload.json                   # Payload-file example
├── install/
│   ├── linux/
│   │   └── install_linux.sh           # Linux/macOS installer
│   └── windows/
│       ├── install_windows.ps1        # Windows PowerShell installer
│       └── install_windows.bat        # Windows BAT wrapper
└── src/
    └── forgrequest/
        ├── __init__.py
        └── cli.py                     # Main application code
```

The root `forgrequest.py` keeps this command working from the project directory:

```bash
python forgrequest.py -u https://example.com --dry-run
```

The installers create a global command named:

```bash
forgrequest
```

---

## Requirements

- Python **3.10+**
- Python package: `requests`

Manual dependency installation:

```bash
python -m pip install -r requirements.txt
```

Linux/macOS alternative:

```bash
python3 -m pip install --user -r requirements.txt
```

Windows alternative:

```powershell
py -3 -m pip install --user -r requirements.txt
```

---

## Install as a command

### Linux/macOS

From the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

You can also use the root convenience installer:

```bash
chmod +x install_linux.sh
./install_linux.sh
```

Default Linux/macOS paths:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

If `~/.local/bin` is not in your `PATH`, add it:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

### Windows

From PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install\windows\install_windows.ps1
```

Or use the BAT wrapper:

```cmd
install\windows\install_windows.bat
```

Default Windows paths:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     forgrequest.cmd, available as forgrequest after PATH update
```

Open a new terminal after installation if Windows does not immediately detect the new command.

Uninstall:

```powershell
.\install\windows\install_windows.ps1 -Uninstall
```

---

## Basic usage

Run from source:

```bash
python forgrequest.py -u https://example.com --dry-run
```

Run after installation:

```bash
forgrequest -u https://example.com --dry-run
```

POST with a JSON payload file:

```bash
forgrequest \
  -u "https://example.com/api/login" \
  -X POST \
  --json-file ./examples/payload.json \
  --show-request
```

Use a header file:

```bash
forgrequest \
  -u "https://example.com/api" \
  -X POST \
  --headers-file ./examples/login_head.example.txt \
  --json-file ./examples/payload.json \
  --show-request
```

Header file example:

```text
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
X-Bug-Bounty: H1-immroa
```

The header parser safely supports semicolons inside values such as `User-Agent` and only splits semicolon-separated headers when the next segment looks like another valid header name.

---

## Raw request replay

Replay a raw HTTP/1.1 request captured from a proxy, browser, log, or lab:

```bash
forgrequest --raw-request ./request.raw --show-request
```

Example raw request:

```http
POST /api/login HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0
Content-Type: application/json
Cookie: session=abc

{"username":"test","password":"test"}
```

If the raw request uses a relative path, `Host` is required. By default, the URL is built with HTTPS. Override this with:

```bash
forgrequest --raw-request ./request.raw --raw-scheme http
```

You can also override the URL explicitly:

```bash
forgrequest --raw-request ./request.raw -u https://staging.example.com/api/login
```

---

## Import from cURL

Import a cURL command directly:

```bash
forgrequest --from-curl "curl 'https://example.com/api' -H 'X-Test: 1' --data-raw '{\"a\":1}'" --show-request
```

Or from a file:

```bash
forgrequest --from-curl ./request.curl --show-request
```

The parser supports common cURL flags such as `-X`, `-H`, `-b`, `-A`, `-d`, `--data-raw`, `--data-binary`, `-k`, `-L`, and `--url`.

---

## Request modifiers

Set or remove headers after loading config/files/raw/cURL sources:

```bash
forgrequest -u https://example.com \
  --set-header "X-Test: 1" \
  --remove-header "X-Powered-By" \
  --show-request
```

Set or remove cookies:

```bash
forgrequest -u https://example.com \
  --set-cookie "session=abc" \
  --remove-cookie "tracking_id" \
  --show-request
```

Set or remove query parameters:

```bash
forgrequest -u "https://example.com/api/user?id=1&utm_source=x" \
  --set-query "debug=true" \
  --remove-query "utm_source" \
  --show-request
```

Replace text inside a text/UTF-8 body:

```bash
forgrequest -u https://example.com/api -X POST \
  --json '{"role":"user"}' \
  --replace-body '"user"="admin"' \
  --show-request
```

---

## Body helpers

JSON body:

```bash
forgrequest -u https://example.com/api -X POST --json '{"test":true}'
```

JSON file:

```bash
forgrequest -u https://example.com/api -X POST --json-file ./examples/payload.json
```

Form body:

```bash
forgrequest -u https://example.com/login -X POST --form 'username=a&password=b'
```

Binary body:

```bash
forgrequest -u https://example.com/upload -X POST --binary-file ./sample.bin
```

Multipart body:

```bash
forgrequest -u https://example.com/upload -X POST \
  --multipart "description=test" \
  --multipart "file=@./sample.txt;type=text/plain"
```

`--json`, `--json-file`, `--form`, and `--form-file` automatically set `Content-Type` only when the user did not already provide it.

---

## Variables and templates

Use `{{NAME}}` placeholders in URLs, headers, cookies, and string bodies:

```bash
forgrequest -u "{{BASE_URL}}/api/user/{{USER_ID}}" \
  -H "Authorization: Bearer {{TOKEN}}" \
  --var BASE_URL=https://example.com \
  --var USER_ID=123 \
  --var TOKEN=abc
```

Load variables from a file:

```bash
forgrequest -u "{{BASE_URL}}/api" -H "Authorization: Bearer {{TOKEN}}" --vars-file ./vars.env
```

Example `vars.env`:

```env
BASE_URL=https://example.com
TOKEN=abc123
```

---

## Cookie jar workflow

Load cookies from a file:

```bash
forgrequest -u https://example.com/profile --load-cookies ./cookies.txt
```

Save cookies from the response/session:

```bash
forgrequest -u https://example.com/login -X POST --json-file login.json --save-cookies ./cookies.txt
```

Load and save the same file:

```bash
forgrequest -u https://example.com/profile --cookie-jar ./cookies.txt
```

Supported input cookie formats include Netscape cookie files, JSON object, `Cookie:` header, `Set-Cookie:` lines, and simple `name=value` lines.

---

## Redirect visibility

Show the redirect chain:

```bash
forgrequest -u https://example.com --show-redirect-chain
```

Disable redirects:

```bash
forgrequest -u https://example.com --no-redirects
```

---

## Export and evidence

Show the prepared request:

```bash
forgrequest -u https://example.com --show-request --dry-run
```

Save the prepared raw HTTP request:

```bash
forgrequest -u https://example.com --save-prepared-request ./prepared.raw --dry-run
```

Export cURL:

```bash
forgrequest -u https://example.com/api -H "X-Test: 1" --export-curl --dry-run
```

Export Python `requests` code:

```bash
forgrequest -u https://example.com/api -H "X-Test: 1" --export-python --dry-run
```

Save a complete execution directory:

```bash
forgrequest -u https://example.com/api --save-session ./case-001
```

The session directory includes:

```text
case-001/
├── request.raw
├── request.curl
├── request.py
├── response.headers
├── response.body
├── metadata.json
└── README.txt
```

These files may contain sensitive data. Store and share them carefully.

---

## Execution reports

Save a JSON execution report:

```bash
forgrequest -u https://example.com/api --report-json ./report.json
```

Save an HTML execution report:

```bash
forgrequest -u https://example.com/api --report-html ./report.html
```

Reports include request metadata, response metadata, timings, redirect metadata, body size, and execution settings. Sensitive metadata is redacted by default. Disable report redaction only when you intentionally need exact values in a controlled environment:

```bash
forgrequest -u https://example.com/api --report-json ./report.json --no-redact-reports
```

---

## Compare responses or files

`forgrequest diff` compares two local files. It does not send network requests.

```bash
forgrequest diff response-a.txt response-b.txt
```

Save diff metadata as JSON:

```bash
forgrequest diff response-a.txt response-b.txt --json diff.json
```

Only print the summary:

```bash
forgrequest diff response-a.txt response-b.txt --no-body-diff
```

---

## Configuration file

The tool uses `.config` / INI format through Python's standard `configparser` library. It does **not** use TOML, `tomli`, or `tomllib` for runtime config.

Default config path when installed:

```text
Linux/macOS: ~/.config/forgrequest/forgrequest.config
Windows:     %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
```

Create a sample config manually:

```bash
forgrequest --init-config -c ./config/forgrequest.config
```

Sample config:

```ini
[request]
method = GET
user_agent = ForgeryHTTP/1.5.0 (immroa)
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
headers_file =
cookies_file =
payload_file =
payload =

[headers]
Accept = */*

[cookies]
# session = value
```

The URL is intentionally not allowed in the config file. Always pass it using `-u` or `--url`.

Priority order:

1. Built-in defaults
2. `.config` file values
3. Raw request or cURL import values
4. Files referenced by config or CLI, such as `headers_file`, `cookies_file`, `payload_file`
5. CLI arguments
6. Explicit modifiers such as `--set-header`, `--remove-header`, `--set-query`, and `--remove-query`
7. Interactive mode answers

---

## Main arguments

### Target and method

| Argument | Description |
|---|---|
| `-u`, `--url` | Target URL. Required unless `--init-config`, `--raw-request`, or `--from-curl` provides it. Must start with `http://` or `https://`. |
| `-X`, `--method` | HTTP method. Supported: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE`. |
| `--raw-request` | Load a raw HTTP/1.1 request from file. |
| `--raw-scheme` | Scheme used for raw requests with relative targets. |
| `--from-curl` | Import a cURL command string or file. |

### Headers, cookies, and query

| Argument | Description |
|---|---|
| `-H`, `--headers` | Headers as a string. Repeatable. Supports `Name: value`, JSON object, or curl-style `-H` fragments. |
| `--headers-file` | File containing headers. Supports JSON object, `Header: value` lines, or curl-style fragments. |
| `--set-header` | Set or replace a header after all other sources. |
| `--remove-header` | Remove a header by name after all other sources. |
| `-b`, `--cookies` | Cookies as a string. Repeatable. Supports `a=b; c=d` or JSON object. |
| `--cookies-file` | Cookie file. Supports Netscape, JSON, `Cookie:`, `Set-Cookie:`, or `name=value`. |
| `--load-cookies` | Load cookies from a reusable cookie file. |
| `--save-cookies` | Save cookies after the response. |
| `--cookie-jar` | Load and save cookies using the same file. |
| `--set-cookie` | Set or replace a cookie after all other sources. |
| `--remove-cookie` | Remove a cookie by name after all other sources. |
| `--set-query` | Set or replace a query parameter. |
| `--remove-query` | Remove a query parameter. |

### Payload/body

| Argument | Description |
|---|---|
| `-d`, `--payload` | Request body as a string. |
| `--payload-file` | Binary-safe file to send as the request body. |
| `--json` | JSON body string. Validates JSON. |
| `--json-file` | JSON body file. Validates JSON. |
| `--form` | URL-encoded form body string. |
| `--form-file` | URL-encoded form body file. |
| `--binary-file` | Binary file body. |
| `--multipart` | Multipart field `name=value` or `name=@file[;type=mime]`. Repeatable. |
| `--replace-body` | Replace text inside string/UTF-8 body using `old=new`. Repeatable. |

### Network and TLS

| Argument | Description |
|---|---|
| `--timeout` | Request timeout in seconds. |
| `--no-redirects` | Do not follow HTTP redirects. |
| `--show-redirect-chain` | Print redirect chain when redirects are followed. |
| `--insecure` | Disable TLS certificate verification. Use only in labs or controlled testing. |
| `--proxy` | Proxy URL for HTTP and HTTPS, for example `http://127.0.0.1:8080`. |
| `--no-env-proxy` | Ignore proxy/CA settings from environment variables. |

### Output, reports, and exports

| Argument | Description |
|---|---|
| `--include` | Print response headers before the body. |
| `--show-request` | Print the prepared request with sensitive values redacted. |
| `--dry-run` | Prepare and print the request without sending it. |
| `-o`, `--output` | Save response body to a file. |
| `--raw` | Do not pretty-print JSON responses. |
| `--save-prepared-request` | Save prepared request as raw HTTP/1.1 text. |
| `--export-curl` | Print equivalent cURL command. |
| `--export-python` | Print equivalent Python `requests` code. |
| `--report-json` | Save JSON execution report. |
| `--report-html` | Save HTML execution report. |
| `--save-session` | Save request/response evidence in a directory. |
| `--no-redact-reports` | Disable redaction in JSON/HTML reports. |
| `--no-logo` | Hide the banner/logo. |

### Color mode

| Argument | Description |
|---|---|
| `--color` | Enable color using default mode `always`. |
| `--color auto` | Use color only when stdout is a terminal. |
| `--color always` | Always print ANSI colors. |
| `--color never` | Disable colors. |
| `--no-color` | Disable colors. Equivalent to `--color never`. |

The body is not colorized. This avoids corrupting JSON, HTML, XML, binary output, or redirected output.

### Interactive mode

| Argument | Description |
|---|---|
| `-i`, `--interactive` | Build the request step by step from prompts. |

Example:

```bash
forgrequest --interactive
```

---

## Handling incomplete chunked responses

Some servers or edge/CDN layers can close a chunked response early. Python may report this as:

```text
IncompleteRead
ChunkedEncodingError
Connection broken
```

ForgRequest handles that condition safely:

- No raw Python traceback is printed.
- The partial body received so far is preserved when possible.
- A warning is printed.
- The process exits with code `4` to indicate that the HTTP response body was incomplete.

If you need the partial body for analysis, save it:

```bash
forgrequest -u https://example.com/api -o partial-response.bin
```

---

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Success, or dry-run completed. HTTP status was 2xx or 3xx. `forgrequest diff` also returns `0` when files are equal. |
| `1` | General configuration, validation, file, TLS, connection, or request error. |
| `2` | Missing dependency or startup problem. |
| `3` | HTTP response status was outside 2xx/3xx, or `forgrequest diff` found differences. |
| `4` | Response body was incomplete or partially read due to chunked/decoding/read error. |

---

## Security notes

- Use only on systems where you have authorization.
- Do not store production credentials in config files.
- Use `--show-request` carefully. Sensitive headers and common sensitive query/body names are redacted in previews/reports.
- Raw request saves, cURL exports, Python exports, saved sessions, and response bodies may still contain sensitive data when exact reproduction is required.
- Avoid `--insecure` outside controlled labs.
- Prefer payload/header/cookie files for repeatable testing.
- Use `--no-env-proxy` when you need predictable behavior independent of environment proxy variables.
- Keep bug bounty proof-of-concept requests minimal, traceable, and within scope.

---

## Troubleshooting

### `forgrequest: command not found`

Linux/macOS:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows: open a new terminal after installation, or check that this directory is in the user PATH:

```text
%LOCALAPPDATA%\Programs\forgrequest
```

### `ModuleNotFoundError: No module named requests`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

### Header parsing fails with User-Agent

Use one header per line in a file:

```text
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
X-Bug-Bounty: H1-immroa
```

This format is supported and semicolons inside the `User-Agent` value are preserved.

### Config is ignored

Pass it explicitly:

```bash
forgrequest -c ./config/forgrequest.config -u https://example.com --dry-run
```

Or set the environment variable:

```bash
export FORGREQUEST_CONFIG="$HOME/.config/forgrequest/forgrequest.config"
```
