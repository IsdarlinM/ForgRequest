# ForgRequest v1.6.0 validation results

Validation date: 2026-07-10
Environment available for execution: Linux container with Python 3.13.

## Scope

The validation focused on the project boundary documented in the README: ForgRequest is a manual HTTP client for request replay, request modification, response observation, reporting, and local diff. It is not a crawler and not a vulnerability scanner.

## CLI validation

Validated successfully:

- Python bytecode compilation:
  - `src/forgrequest/cli.py`
  - `src/forgrequest/webui.py`
  - `forgrequest.py`
- Startup and command help:
  - `python forgrequest.py --version`
  - `python forgrequest.py --help`
  - `python forgrequest.py diff --help`
  - `python forgrequest.py web --help`
- Config generation:
  - `python forgrequest.py --init-config -c ./new.config`
- HTTP method handling against a local controlled HTTP server:
  - `GET`
  - `POST`
  - `PUT`
  - `PATCH`
  - `DELETE`
  - `HEAD`
  - `OPTIONS`
  - `TRACE`
- Request building and modification:
  - `--headers`
  - `--headers-file`
  - `--set-header`
  - `--remove-header`
  - `--cookies`
  - `--cookies-file`
  - `--load-cookies`
  - `--save-cookies`
  - `--cookie-jar`
  - `--set-cookie`
  - `--remove-cookie`
  - `--set-query`
  - `--remove-query`
- Body helpers:
  - `--payload`
  - `--payload-file`
  - `--json`
  - `--json-file`
  - `--form`
  - `--form-file`
  - `--binary-file`
  - `--multipart`
  - `--replace-body`
- Replay/import/export:
  - `--raw-request`
  - `--raw-scheme`
  - `--from-curl`
  - `--export-curl`
  - `--export-python`
  - `--save-prepared-request`
- Execution controls:
  - `--timeout`
  - `--no-redirects`
  - `--show-redirect-chain`
  - `--insecure` argument parsing
  - `--proxy` argument parsing
  - `--no-env-proxy`
  - `--include`
  - `--show-request`
  - `--dry-run`
  - `--raw`
  - `--no-logo`
  - `--no-color`
- Reports and artifacts:
  - `--output`
  - `--report-json`
  - `--report-html`
  - `--save-session`
  - `--no-redact-reports`
- Diff command:
  - equal files return `0`
  - different files return `3`
  - `--json`
  - `--no-body-diff`
  - `--context`

## Web Console validation

Validated successfully:

- `python forgrequest.py web --help`
- Local Web Console startup on `127.0.0.1` with a temporary workspace.
- `GET /api/info` returned version `1.6.0` and signature metadata.
- `GET /` returned the full HTML/CSS/JavaScript interface.
- UI markup contains the expected panels:
  - Request Builder
  - Raw / cURL Replay
  - Modifiers
  - Execution & Reports
  - Response Diff
  - Feature Map
- Web request execution through `POST /api/run`:
  - builder mode with JSON body
  - raw request mode
  - cURL import mode
  - report JSON artifact generation
  - report HTML artifact generation
  - cURL export output
  - Python export output
- Web diff execution through `POST /api/diff`:
  - different text returned exit code `3`
  - unified diff output was returned
  - diff JSON artifact was generated
- Web config generation:
  - `initConfig` created a `forgrequest.generated.config` artifact.

## Installer validation

Linux/macOS installer validated successfully in a temporary HOME:

- `install/linux/install_linux.sh`
- global wrapper creation under `~/.local/bin/forgrequest`
- wrapper version command:
  - `forgrequest --version`
- wrapper subcommands after installer fix:
  - `forgrequest web --help`
  - `forgrequest diff --help`
- Linux uninstall:
  - `install/linux/install_linux.sh --uninstall`

Windows installer file was reviewed statically in the Linux environment:

- `install/windows/install_windows.cmd`

The Windows CMD installer now performs the full installation directly, creates the wrapper, updates the user PATH, and sets `FORGREQUEST_CONFIG`. The wrapper uses `FORGREQUEST_CONFIG` instead of injecting `-c` before user arguments, preserving subcommand compatibility for:

- `forgrequest web ...`
- `forgrequest diff ...`

## Notes

- No crawler, scanner, fuzzing, brute force, or automatic vulnerability testing was added.
- The Web Console is intentionally local-first and binds to `127.0.0.1` by default.
- Screenshots are intentionally not included in the deliverable. The Web Console was validated through HTTP, API responses, generated artifacts, and HTML/CSS/JavaScript inspection.

## Signature rename validation

Validated after signature rename:

- Replaced every text occurrence of the previous signature with `imr`.
- Confirmed no remaining references to the previous signature in project text files.
- Re-ran Python compilation for `src` and `forgrequest.py`.
- Validated `python forgrequest.py --version` returns `signature imr`.
- Validated `--help`, `web --help`, `diff --help`, and `--dry-run` still work.

## Web UI input normalization validation

Validated after Web Console field-width normalization:

- Updated the Web Console CSS so `input`, `select`, and `textarea` elements use full-width responsive sizing.
- Added explicit `min-width:0`, `max-width:100%`, normalized heights, and responsive grid behavior to prevent narrow or visually inconsistent controls.
- Added a global `.span9` grid utility used by the Raw / cURL Replay panel, fixing the narrow raw request text area.
- Expanded the Target and Network cards so method, URL, timeout, and proxy fields have consistent professional width.
- Verified visible form controls in each panel with DOM/CSS inspection.
- Removed screenshot artifacts from the deliverable because they are not required.
- Re-ran Python compilation and core CLI/Web help commands.

## Installer environment variable validation

Validated after installer updates:

- Removed the Windows PowerShell installer from the project.
- Kept Windows installation through `install/windows/install_windows.cmd` only.
- Updated the Windows CMD installer to persist the user PATH with `reg add HKCU\Environment /v Path ...`.
- Updated the Windows CMD installer to set `FORGREQUEST_CONFIG` at user level.
- Updated the Linux installer to append `export PATH="$HOME/.local/bin:$PATH"` to common shell startup files when missing.
- Confirmed the Linux installer validates the PATH-resolved `forgrequest --help` command after installation.
- Re-ran Linux installation and uninstall in a temporary HOME.
