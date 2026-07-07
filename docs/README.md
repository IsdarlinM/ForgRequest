# Forgery HTTP Request

**Forgery HTTP Request** (`forgrequest`) is an advanced Python HTTP client for authorized testing, endpoint behavior validation, labs, CTFs, internal audits, and in-scope bug bounty work.

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

             Forgery HTTP Request v1.4.0  ::  signature: immroa
```

> Responsible use: use this tool only on systems you own, controlled labs, authorized audits, CTFs, or bug bounty targets where you have explicit permission.

---

## Project layout

```text
ForgeryHttpRequest/
├── forgrequest.py                    # Compatibility launcher
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

Make it permanent in Bash:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Make it permanent in Zsh:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
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

You can also use the root convenience installer:

```powershell
.\install_windows.ps1
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

POST with a payload file:

```bash
forgrequest \
  -u "https://example.com/api/login" \
  -X POST \
  --payload-file ./examples/payload.json \
  -H "Content-Type: application/json" \
  --show-request
```

PowerShell equivalent:

```powershell
forgrequest `
  -u "https://example.com/api/login" `
  -X POST `
  --payload-file .\examples\payload.json `
  -H "Content-Type: application/json" `
  --show-request
```

Use a header file:

```bash
forgrequest \
  -u "https://example.com/api" \
  -X POST \
  --headers-file ./examples/login_head.example.txt \
  --payload-file ./examples/payload.json \
  --show-request
```

Header file example:

```text
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
X-Bug-Bounty: H1-immroa
```

The header parser safely supports semicolons inside values such as `User-Agent` and only splits semicolon-separated headers when the next segment looks like another valid header name.

---

## Configuration file

The tool uses `.config` / INI format through Python's standard `configparser` library. It does **not** use TOML, `tomli`, or `tomllib`.

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
user_agent = ForgeryHTTP/1.4.0 (immroa)
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
3. Files referenced by config or CLI, such as `headers_file`, `cookies_file`, `payload_file`
4. CLI arguments
5. Interactive mode answers

---

## Arguments

### Target and method

| Argument | Description |
|---|---|
| `-u`, `--url` | Target URL. Required unless `--init-config` is used. Must start with `http://` or `https://`. |
| `-X`, `--method` | HTTP method. Supported: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE`. |

### Headers

| Argument | Description |
|---|---|
| `-H`, `--headers` | Headers as a string. Repeatable. Supports `Name: value`, JSON object, or curl-style `-H` fragments. |
| `--headers-file` | File containing headers. Supports JSON object, `Header: value` lines, or curl-style fragments. |
| `-A`, `--user-agent` | Explicit User-Agent. Highest priority. |

Examples:

```bash
forgrequest -u https://example.com -H "X-Test: 1" -H "Accept: application/json"
```

```bash
forgrequest -u https://example.com --headers '{"X-Test":"1","Accept":"application/json"}'
```

```bash
forgrequest -u https://example.com --headers-file ./headers.txt
```

### Cookies

| Argument | Description |
|---|---|
| `-b`, `--cookies` | Cookies as a string. Repeatable. Supports `a=b; c=d` or JSON object. |
| `--cookies-file` | Cookie file. Supports Netscape cookie files, JSON object, `Cookie:` header, `Set-Cookie:` lines, or `name=value` lines. |

Examples:

```bash
forgrequest -u https://example.com -b "session=abc; theme=dark"
```

```bash
forgrequest -u https://example.com --cookies-file ./cookies.txt
```

### Payload/body

| Argument | Description |
|---|---|
| `-d`, `--payload` | Request body as a string. |
| `--payload-file` | Binary-safe file to send as the request body. |

Examples:

```bash
forgrequest -u https://example.com/api -X POST -d '{"test":true}' -H "Content-Type: application/json"
```

```bash
forgrequest -u https://example.com/api -X POST --payload-file ./payload.json -H "Content-Type: application/json"
```

### Network and TLS

| Argument | Description |
|---|---|
| `--timeout` | Request timeout in seconds. |
| `--no-redirects` | Do not follow HTTP redirects. |
| `--insecure` | Disable TLS certificate verification. Use only in labs or controlled testing. |
| `--proxy` | Proxy URL for HTTP and HTTPS, for example `http://127.0.0.1:8080`. |

Examples:

```bash
forgrequest -u https://example.com --timeout 10
```

```bash
forgrequest -u https://example.com --proxy http://127.0.0.1:8080 --insecure
```

### Output and display

| Argument | Description |
|---|---|
| `--include` | Print response headers before the body. |
| `--show-request` | Print the prepared request with sensitive values redacted. |
| `--dry-run` | Prepare and print the request without sending it. |
| `-o`, `--output` | Save response body to a file. |
| `--raw` | Do not pretty-print JSON responses. |
| `--no-logo` | Hide the banner/logo. |

Examples:

```bash
forgrequest -u https://example.com --include
```

```bash
forgrequest -u https://example.com -o response.bin
```

### Color mode

| Argument | Description |
|---|---|
| `--color` | Enable color using default mode `always`. |
| `--color auto` | Use color only when stdout is a terminal. |
| `--color always` | Always print ANSI colors. |
| `--color never` | Disable colors. |
| `--no-color` | Disable colors. Equivalent to `--color never`. |

Examples:

```bash
forgrequest -u https://example.com --dry-run --color
```

```bash
forgrequest -u https://example.com --dry-run --color auto
```

```bash
forgrequest -u https://example.com --dry-run --no-color
```

The body is not colorized. This avoids corrupting JSON, HTML, XML, binary output, or redirected output.

### Interactive mode

| Argument | Description |
|---|---|
| `-i`, `--interactive` | Build the request step by step from prompts. |

Example:

```bash
forgrequest --interactive
```

You can also enable it in `forgrequest.config`:

```ini
[request]
interactive = true
```

---

## Handling incomplete chunked responses

Some servers or edge/CDN layers can close a chunked response early. Python may report this as:

```text
IncompleteRead
ChunkedEncodingError
Connection broken
```

Version `1.4.0` handles that condition safely:

- No raw Python traceback is printed.
- The partial body received so far is preserved when possible.
- A warning is printed.
- The process exits with code `4` to indicate that the HTTP response body was incomplete.

Example output:

```text
[Response] HTTP 200 OK | 0.421s | 3963 bytes
[Final URL] https://example.com/api
[!] Warning: Incomplete chunked response: ...
[!] Partial response body was preserved when possible.
```

If you need the partial body for analysis, save it:

```bash
forgrequest -u https://example.com/api -o partial-response.bin
```

---

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Success, or dry-run completed. HTTP status was 2xx or 3xx. |
| `1` | General configuration, validation, file, TLS, connection, or request error. |
| `2` | Missing dependency or startup problem. |
| `3` | HTTP response status was outside 2xx/3xx. |
| `4` | Response body was incomplete or partially read due to chunked/decoding/read error. |

---

## Security notes

- Use only on systems where you have authorization.
- Do not store production credentials in config files.
- Use `--show-request` carefully. Sensitive headers such as `Authorization`, `Cookie`, `Set-Cookie`, `X-API-Key`, and `Proxy-Authorization` are redacted.
- Avoid `--insecure` outside controlled labs.
- Prefer payload/header/cookie files for repeatable testing.
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
