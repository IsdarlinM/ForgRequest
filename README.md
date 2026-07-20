# Forgery HTTP Request

**Forgery HTTP Request** (`forgrequest`) is a Python HTTP client for authorized request replay, request modification, endpoint behavior validation, labs, CTFs, internal audits, and in-scope bug bounty work.

ForgRequest is intentionally **not a crawler** and **not a vulnerability scanner**. It works with individual URLs and requests supplied by the operator. It does not discover URLs, spider applications, fuzz targets, or classify vulnerabilities automatically.

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

             Forgery HTTP Request v1.8.0  ::  signature: imr
```

> Use this tool only on systems you own, controlled laboratories, authorized audits, CTFs, or bug bounty targets where you have explicit permission.

## Main capabilities

- Build and replay `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, and `TRACE` requests.
- Modify headers, cookies, query parameters, bodies, methods, redirects, TLS verification, proxy settings, and timeouts.
- Import raw HTTP/1.1 requests and cURL commands.
- Export prepared requests as raw HTTP, cURL, Python `requests`, or Playwright code.
- Send JSON, form, binary, multipart, file-based, and arbitrary request bodies.
- Use reusable variables through `{{NAME}}`, `--var`, and `--vars-file`.
- Load and save cookies or use a reusable cookie jar.
- Display redirect chains and preserve partial chunked responses.
- Generate JSON and HTML execution reports.
- Save complete request/response evidence directories.
- Compare two local responses with `forgrequest diff`.
- Operate through the CLI or the local Web Console.
- Render one supplied JavaScript-dependent GET page with Chromium, Firefox, or WebKit.
- Update an installed copy safely with backups through `forgrequest update`.

## Requirements

- Python 3.10 or newer.
- `requests>=2.31.0`.
- `playwright>=1.40.0,<2` for JavaScript browser mode.
- Chromium, Chrome, Edge, Firefox, WebKit, or a Playwright-managed runtime when browser rendering is used.

Install Python dependencies manually:

```bash
python -m pip install -r requirements.txt
```

Install a browser runtime when required:

```bash
forgrequest browser-install chromium
```

Other supported runtime commands:

```bash
forgrequest browser-install firefox
forgrequest browser-install webkit
forgrequest browser-install all
```

Standard HTTP functionality remains available if a browser runtime cannot be installed.

## Installation

Installers are organized only under the `install/` directory.

### Linux and macOS

From the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Default locations:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

The installer:

- installs the application and dependencies;
- creates the `forgrequest` command;
- adds `export PATH="$HOME/.local/bin:$PATH"` to common shell startup files when missing;
- sets `FORGREQUEST_CONFIG` and `FORGREQUEST_INSTALL_DIR` in the installed wrapper;
- detects a system Chromium/Chrome browser or attempts to install Playwright Chromium.

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

### Windows

Run the CMD installer from Command Prompt:

```cmd
install\windows\install_windows.cmd
```

No PowerShell installer is required or included.

Default locations:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     %LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd
```

The installer updates the user `PATH` and sets:

```text
FORGREQUEST_CONFIG
FORGREQUEST_INSTALL_DIR
```

Open a new terminal if an already-open shell does not immediately detect the command.

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```

## Basic usage

Show all commands and organized argument groups:

```bash
forgrequest --help
```

Prepare a request without sending it:

```bash
forgrequest -u https://example.com --dry-run --show-request
```

Send a JSON request:

```bash
forgrequest \
  -u https://example.com/api/login \
  -X POST \
  --json-file examples/payload.json \
  --include
```

Modify a request:

```bash
forgrequest -u "https://example.com/api?id=1" \
  --set-header "X-Test: 1" \
  --remove-header "X-Old" \
  --set-cookie "session=abc" \
  --remove-cookie "tracking" \
  --set-query "debug=true" \
  --remove-query "cachebuster" \
  --show-request
```

Use variables:

```bash
forgrequest -u "{{BASE_URL}}/api/{{RESOURCE}}" \
  -H "Authorization: Bearer {{TOKEN}}" \
  --var BASE_URL=https://example.com \
  --var RESOURCE=profile \
  --var TOKEN=change-me
```

## Raw HTTP replay

Replay a raw HTTP/1.1 request:

```bash
forgrequest \
  --raw-request examples/request.raw.example \
  --raw-scheme https \
  --show-request
```

Override the destination while retaining the imported method, headers, and body:

```bash
forgrequest \
  --raw-request examples/request.raw.example \
  -u https://target.example/api/login
```

## cURL import and request export

Import a cURL command or a file containing one:

```bash
forgrequest --from-curl request.curl --show-request
```

Export a prepared request:

```bash
forgrequest -u https://example.com/api \
  --export-curl \
  --export-python \
  --save-prepared-request prepared-request.raw \
  --dry-run
```

## Request bodies

JSON:

```bash
forgrequest -u https://example.com/api -X POST --json '{"ok":true}'
```

Form data:

```bash
forgrequest -u https://example.com/login -X POST --form "username=a&password=b"
```

Multipart form:

```bash
forgrequest -u https://example.com/upload -X POST \
  --multipart "name=test" \
  --multipart "file=@examples/payload.json;type=application/json"
```

Binary body:

```bash
forgrequest -u https://example.com/upload -X POST --binary-file sample.bin
```

## Cookie workflow

Save cookies from a response:

```bash
forgrequest -u https://example.com/login \
  -X POST \
  --json-file examples/payload.json \
  --save-cookies session.cookies
```

Reuse them:

```bash
forgrequest -u https://example.com/profile --load-cookies session.cookies
```

Load and save through the same jar:

```bash
forgrequest -u https://example.com/profile --cookie-jar session.cookies
```

## JavaScript browser mode

Use browser mode only when the supplied page requires JavaScript rendering:

```bash
forgrequest -u https://example.com/app \
  --browser \
  --browser-engine chromium \
  --browser-wait-until networkidle \
  --browser-wait-selector '#app' \
  -o rendered.html
```

Browser mode:

- navigates to one operator-supplied URL;
- supports Chromium, Firefox, and WebKit;
- captures rendered HTML, final URL, title, headers, redirects, console messages, page errors, cookies, and storage state;
- supports headed and headless execution;
- is restricted to GET page navigation;
- does not crawl links or discover additional targets.

Use the standard HTTP engine for non-GET methods, request bodies, multipart data, or requests requiring `--no-redirects`.

## Web Console

Start the local interface:

```bash
forgrequest web
```

Default address:

```text
http://127.0.0.1:7413/
```

Open it automatically:

```bash
forgrequest web --open
```

The Web Console exposes the same request builder, raw/cURL import, modifiers, HTTP/browser engine selection, cookies, variables, network settings, exports, reports, session evidence, and response diff workflow available in the CLI.

Keep the console bound to localhost. It can send requests and launch a browser from the local workstation.

## Reports and evidence

Create reports:

```bash
forgrequest -u https://example.com/api \
  --report-json report.json \
  --report-html report.html
```

Save a complete session:

```bash
forgrequest -u https://example.com/api --save-session case-001
```

A saved session can include:

```text
request.raw
request.curl
request.py
response.headers
response.body
metadata.json
browser-console.json
browser-page-errors.json
browser-storage-state.json
README.txt
```

Sensitive request metadata is redacted in reports by default. Use `--no-redact-reports` only when full local evidence is intentionally required.

## Response comparison

Compare two local files:

```bash
forgrequest diff response-a.json response-b.json
```

Generate a JSON summary:

```bash
forgrequest diff response-a.json response-b.json --json diff.json
```

## Configuration

Generate a sample configuration:

```bash
forgrequest --init-config -c ./config/forgrequest.config
```

Default installed paths:

```text
Linux/macOS: ~/.config/forgrequest/forgrequest.config
Windows:     %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
```

The target URL is intentionally not stored in the default configuration. Always provide it with `-u` or `--url`, or through a raw/cURL import.

Configuration priority:

1. Built-in defaults.
2. `.config` values.
3. Raw request or cURL import values.
4. Referenced headers, cookies, variables, and body files.
5. CLI arguments.
6. Explicit set/remove modifiers.
7. Interactive-mode answers.

## Update command

Preview an update:

```bash
forgrequest update --dry-run
```

Update from the official repository:

```bash
forgrequest update --yes
```

Update from a local release archive:

```bash
forgrequest update --from-zip ForgRequest-latest.zip --yes
```

The updater validates the archive, creates a full backup, preserves configuration and common local artifact directories, restores the previous installation on failure, and can retain the backup with `--keep-backup`.

## Command reference

Use command-specific help for the authoritative list of options:

```bash
forgrequest --help
forgrequest web --help
forgrequest diff --help
forgrequest update --help
forgrequest browser-install --help
```

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Successful request, dry-run, installation-related command, or 2xx/3xx response. |
| `1` | Configuration, validation, file, TLS, connection, request, update, or Web Console error. |
| `2` | Missing dependency, browser runtime, or startup problem. |
| `3` | HTTP response outside 2xx/3xx, or compared files differ. |
| `4` | Incomplete or partially read response body. |

## Security guidance

- Use only within explicit authorization and scope.
- Do not store production credentials in configuration files or repository examples.
- Keep request previews and exported artifacts protected; they may contain sensitive data.
- Avoid `--insecure` outside controlled laboratories.
- Keep the Web Console bound to `127.0.0.1`.
- Review `forgrequest update --dry-run` before changing an important installation.
- Keep proof-of-concept traffic minimal, traceable, and within program rules.

## Troubleshooting

### Command not found

Open a new terminal after installation. Linux/macOS installers add:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows installers add `%LOCALAPPDATA%\Programs\forgrequest` to the user `PATH`.

### Missing Python dependencies

```bash
python -m pip install -r requirements.txt
```

### Missing browser runtime

```bash
forgrequest browser-install chromium
```

### Config is not being loaded

```bash
forgrequest -c ./config/forgrequest.config -u https://example.com --dry-run
```

Or set `FORGREQUEST_CONFIG` to the intended `.config` file.
