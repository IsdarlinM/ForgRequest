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

             Forgery HTTP Request v1.7.2  ::  signature: imr
```

When ANSI color is enabled, the logo is rendered with **one single cyan color** to keep terminal output stable and professional.

> Responsible use: use this tool only on systems you own, controlled labs, authorized audits, CTFs, or bug bounty targets where you have explicit permission.

---

## What changed in v1.7.2

- Keep a single persistent **Run request** button in the sticky top navigation, next to the version indicator.
- Redesigned the execution action card with stronger visual hierarchy and clearer Preview/Reset secondary actions.
- Added `Ctrl+Enter` and `Cmd+Enter` keyboard shortcuts to run the current request from any input field.
- Added a running/disabled state to the persistent Run request control to prevent duplicate submissions.
- Improved responsive behavior so the primary action remains easy to reach on desktop, tablet, and mobile layouts.
- Automatically brings the execution console into view after a request finishes or a Web Console error occurs.

## Previous v1.7.1 highlights

- Reworked the main `forgrequest --help` output so every top-level command is visible.
- Added the `web`, `diff`, and `update` commands to the main help screen.
- Organized CLI help into clear sections: general, target/method, request import, headers, cookies, query parameters, body helpers, variables, network/TLS, output/exports, reports/session evidence, color, and interactive mode.
- Added command-specific help pointers and practical examples directly to `forgrequest --help`.
- Updated documentation to match the organized help output.

## Previous v1.7.0 highlights

- Added `forgrequest update`, a safe updater for installed or source-tree deployments.
- The update mechanism can pull the official GitHub ZIP archive or use a local ZIP with `--from-zip` for offline validation.
- Updates create a full backup before replacing application files.
- Local configuration and operator-generated directories are preserved, including `forgrequest.config`, `reports`, `sessions`, `cases`, `outputs`, `artifacts`, `web-artifacts`, `workspace`, `workspaces`, `projects`, and `data` when present.
- Linux and Windows wrappers now expose `FORGREQUEST_INSTALL_DIR` so the updater can identify the active installation reliably.
- Documentation and installer notes were refreshed for the update workflow.

## Capabilities

- Standard request builder: URL, method, headers, cookies, payload, proxy, redirects, TLS verification, timeout, output file.
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
- Local Web Console: `forgrequest web`.
- Safe update command: `forgrequest update`.
- Improved redaction in prepared-request previews and reports.

---

## Project layout

```text
ForgeryHttpRequest/
├── forgrequest.py                    # Compatibility launcher
├── pyproject.toml                     # Optional package metadata / console script
├── requirements.txt                   # Python dependencies
├── README.md                          # Main documentation
├── TEST_RESULTS.md                    # Local validation notes
├── config/
│   └── forgrequest.config             # Default .config file
├── docs/
│   └── README.md                      # Documentation copy
├── examples/
│   ├── login_head.example.txt         # Header-file example
│   ├── payload.json                   # JSON payload example
│   ├── request.raw.example            # Raw HTTP request replay example
│   └── vars.env.example               # Template variable example
├── install/
│   ├── README.md                      # Installer overview
│   ├── linux/
│   │   ├── README.md                  # Linux/macOS install notes
│   │   └── install_linux.sh           # Linux/macOS installer
│   └── windows/
│       ├── README.md                  # Windows install notes
│       └── install_windows.cmd        # Windows CMD installer
└── src/
    └── forgrequest/
        ├── __init__.py
        ├── cli.py                     # Main CLI application code
        ├── updater.py                 # Safe update command implementation
        └── webui.py                   # Local Web Console server and UI
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

```cmd
py -3 -m pip install --user -r requirements.txt
```

---

## Install as a command

Installers are stored only under the `install/` directory to avoid duplicate entry points.

### Linux/macOS

From the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Default Linux/macOS paths:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

The installer automatically appends the required PATH export to common shell startup files when it is missing:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The installed wrapper also exports:

```bash
FORGREQUEST_CONFIG="$HOME/.config/forgrequest/forgrequest.config"
FORGREQUEST_INSTALL_DIR="$HOME/.local/share/forgrequest"
```

Open a new terminal if your current parent shell does not immediately recognize `forgrequest`.

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

### Windows

From CMD in the project root, run the Windows CMD installer:

```cmd
install\windows\install_windows.cmd
```

No PowerShell installer is required or shipped. The `.cmd` installer performs the installation and updates the user environment variables.

Default Windows paths:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     forgrequest.cmd, available as forgrequest after PATH update
```

The installer updates the user PATH and sets:

```text
FORGREQUEST_CONFIG
FORGREQUEST_INSTALL_DIR
```

Open a new terminal after installation if an already-open terminal does not immediately detect the new command.

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```

---

## Update ForgRequest

Update the active installation from the official GitHub ZIP archive:

```bash
forgrequest update --yes
```

Dry-run the update plan without changing files:

```bash
forgrequest update --dry-run
```

Update from a local ZIP file, useful for offline validation or testing a packaged release:

```bash
forgrequest update --from-zip ./ForgRequest-latest.zip --yes
```

Keep the backup after a successful update:

```bash
forgrequest update --yes --keep-backup
```

Update a specific installation directory:

```bash
forgrequest update --install-dir ~/.local/share/forgrequest --yes
```

The updater:

1. Validates the current installation/project directory.
2. Downloads or loads the update ZIP.
3. Validates that the archive contains `forgrequest.py` and `src/forgrequest/cli.py`.
4. Creates a full backup before replacing files.
5. Preserves local configuration and operator-generated artifacts.
6. Restores the previous installation automatically if the update fails.
7. Optionally installs/refreshes Python dependencies from `requirements.txt`.

Use `forgrequest update --help` for all options.

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
X-Bug-Bounty: H1-imr
```

The header parser safely supports semicolons inside values such as `User-Agent` and only splits semicolon-separated headers when the next segment looks like another valid header name.

---

## Web Console

Launch the local browser-based interface:

```bash
forgrequest web
```

Default URL:

```text
http://127.0.0.1:7413/
```

Run from source:

```bash
python forgrequest.py web
```

Custom host, port, and artifact workspace:

```bash
forgrequest web --host 127.0.0.1 --port 7413 --workspace ~/.forgrequest/web-artifacts
```

Open the default browser automatically:

```bash
forgrequest web --open
```

The Web Console is a local operator UI for the same CLI engine. It includes panels for:

- Request Builder: method, URL, headers, cookies, proxy, timeout, and body helpers.
- Raw / cURL Replay: raw HTTP/1.1 request replay, cURL import, header-file simulation, and cookie-file simulation.
- Modifiers: set/remove headers, cookies, query parameters, body replacements, and template variables.
- Execution & Reports: dry-run, prepared request preview, redirect chain, cURL/Python export, config generation, config path selection, cookie jar, JSON report, HTML report, response body save, and session evidence export.
- Response Diff: browser UI for the same `forgrequest diff` command.

The primary **Run request** action is available as a single persistent button in the sticky top navigation, next to the version indicator. Press `Ctrl+Enter` on Windows/Linux or `Cmd+Enter` on macOS to execute the current request from any input field. The button enters a busy state to prevent accidental duplicate submissions.

Security note: keep the Web Console bound to localhost. It can send HTTP requests from your machine and save artifacts to the configured workspace. Do not expose it on a public interface.

---

## Configuration file

The tool uses `.config` / INI format through Python's standard `configparser` library. It does **not** use TOML, `tomli`, or `tomllib` for runtime configuration.

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
user_agent = ForgeryHTTP/1.7.2 (imr)
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

## Main CLI arguments


The main help screen is organized by workflow and now lists every top-level command:

```bash
forgrequest --help
forgrequest web --help
forgrequest diff --help
forgrequest update --help
```

### Special commands

| Command | Description |
|---|---|
| `forgrequest web` | Start the local Web Console. |
| `forgrequest diff LEFT RIGHT` | Compare two local response/body files. |
| `forgrequest update` | Safely update ForgRequest from GitHub or a local ZIP. |

### Target and method

| Argument | Description |
|---|---|
| `-u`, `--url` | Target URL. Required unless `--init-config`, `--raw-request`, or `--from-curl` provides it. Must start with `http://` or `https://`. |
| `-X`, `--method` | HTTP method. Supported: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE`. |
| `--raw-request` | Load a raw HTTP/1.1 request from file. |
| `--raw-scheme` | Scheme used for raw requests with relative targets. |
| `--from-curl` | Import a cURL command string or file. |
| `--version` | Print the current version and exit. |

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

### Variables

| Argument | Description |
|---|---|
| `--var` | Template variable `KEY=value` for `{{KEY}}` placeholders. Repeatable. |
| `--vars-file` | File with `KEY=value` variables for `{{KEY}}` placeholders. |

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

## Raw HTTP request replay

Example file:

```http
POST /api/login HTTP/1.1
Host: example.com
User-Agent: ForgRequest-lab
Content-Type: application/json
Cookie: session=abc

{"username":"test@example.com","password":"change-me"}
```

Replay it:

```bash
forgrequest --raw-request ./examples/request.raw.example --raw-scheme https --show-request
```

Override the URL while reusing the raw method, headers, and body:

```bash
forgrequest --raw-request ./examples/request.raw.example -u https://target.example/api/login
```

---

## cURL import and exports

Import from a cURL command:

```bash
forgrequest --from-curl "curl 'https://example.com/api' -H 'Accept: application/json' --data-raw '{\"a\":1}'" --show-request
```

Import from a cURL file:

```bash
forgrequest --from-curl ./request.curl --show-request
```

Export a prepared request:

```bash
forgrequest -u https://example.com/api -H "X-Test: 1" --export-curl --export-python --dry-run
```

---

## Modifiers

```bash
forgrequest -u "https://example.com/api?debug=false" \
  --set-header "X-Test: 1" \
  --remove-header "X-Old" \
  --set-cookie "session=abc" \
  --remove-cookie "tracking" \
  --set-query "debug=true" \
  --remove-query "utm_source" \
  --show-request
```

---

## Body helpers

JSON string:

```bash
forgrequest -u https://example.com/api -X POST --json '{"ok":true}'
```

JSON file:

```bash
forgrequest -u https://example.com/api -X POST --json-file ./examples/payload.json
```

Form body:

```bash
forgrequest -u https://example.com/login -X POST --form "username=a&password=b"
```

Multipart:

```bash
forgrequest -u https://example.com/upload -X POST --multipart "name=test" --multipart "file=@./payload.json;type=application/json"
```

Replace text inside a text/UTF-8 body:

```bash
forgrequest -u https://example.com/api -X POST -d 'role=user' --replace-body 'user=admin'
```

---

## Variables

Variables can be used in URL, headers, cookies, and text bodies.

```bash
forgrequest -u "{{BASE_URL}}/api/user/{{USER_ID}}" \
  -H "Authorization: Bearer {{TOKEN}}" \
  --var BASE_URL=https://example.com \
  --var USER_ID=123 \
  --var TOKEN=change-me \
  --show-request
```

From file:

```bash
forgrequest -u "{{BASE_URL}}/api" --vars-file ./examples/vars.env.example --show-request
```

---

## Cookie jar workflow

```bash
forgrequest -u https://example.com/login \
  -X POST \
  --json-file ./examples/payload.json \
  --save-cookies ./session.cookies

forgrequest -u https://example.com/profile \
  --load-cookies ./session.cookies
```

Single jar file for load and save:

```bash
forgrequest -u https://example.com/profile --cookie-jar ./session.cookies
```

---

## Execution reports

JSON report:

```bash
forgrequest -u https://example.com/api --report-json ./report.json
```

HTML report:

```bash
forgrequest -u https://example.com/api --report-html ./report.html
```

Disable report redaction only when you intentionally need full local evidence:

```bash
forgrequest -u https://example.com/api --report-json ./report.json --no-redact-reports
```

Save a complete local evidence directory:

```bash
forgrequest -u https://example.com/api --save-session ./case-001
```

`--save-session` creates:

```text
request.raw
request.curl
request.py
response.headers
response.body
metadata.json
README.txt
```

---

## Response diff

Compare two saved files:

```bash
forgrequest diff response-a.json response-b.json
```

Save diff summary:

```bash
forgrequest diff response-a.json response-b.json --json diff.json
```

Hide the unified body diff:

```bash
forgrequest diff response-a.json response-b.json --no-body-diff
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
| `0` | Success, dry-run completed, update completed, or HTTP status was 2xx/3xx. |
| `1` | General configuration, validation, file, TLS, connection, request, update, or web error. |
| `2` | Missing dependency or startup problem. |
| `3` | HTTP response status was outside 2xx/3xx, or compared files differ. |
| `4` | Response body was incomplete or partially read due to chunked/decoding/read error. |

---

## Security notes

- Use only on systems where you have authorization.
- Do not store production credentials in config files.
- Use `--show-request` carefully. Sensitive headers and common sensitive query/body names are redacted in previews/reports.
- Avoid `--insecure` outside controlled labs.
- Prefer payload/header/cookie files for repeatable testing.
- Keep bug bounty proof-of-concept requests minimal, traceable, and within scope.
- Keep the Web Console bound to `127.0.0.1` unless you fully understand the risk.
- Use `forgrequest update --dry-run` before updating production workstations.
- Use `forgrequest update --keep-backup` when you want a retained rollback copy.

---

## Troubleshooting

### `forgrequest: command not found`

Linux/macOS: open a new terminal after installation. The installer adds:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

to common shell startup files.

Windows: open a new terminal after installation, or verify that this directory is in the user PATH:

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
X-Bug-Bounty: H1-imr
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

### Update fails or is interrupted

Use a dry-run first:

```bash
forgrequest update --dry-run
```

Keep a rollback backup:

```bash
forgrequest update --yes --keep-backup
```

If an update fails, the updater automatically attempts to restore the previous installation from backup.
