# ForgRequest v1.8.0 validation results

Validation was performed in a Linux environment after adding the optional JavaScript browser engine and reorganizing the Web Console.

## Build and documentation

- Python compilation passed for `forgrequest.py` and every module under `src/forgrequest`.
- `README.md` and `docs/README.md` are byte-for-byte synchronized.
- Runtime, package, config, Web server, installer, and documentation versions are `1.8.0`.
- Signature remains `imr`.
- The project contains no PowerShell or BAT installer; Windows installation uses only `install/windows/install_windows.cmd`.
- No screenshots are included in the deliverable.

## CLI help and command routing

The following commands and help routes were validated:

- `forgrequest --version`
- `forgrequest --help`
- `forgrequest web --help`
- `forgrequest diff --help`
- `forgrequest update --help`
- `forgrequest browser-install --help`

The main help lists the `web`, `diff`, `update`, and `browser-install` commands and documents every browser option.

## Standard HTTP engine regression

A controlled local HTTP server was used to validate:

- Methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, and `TRACE`.
- Headers: inline, file-based, set/replace, remove, and User-Agent handling.
- Cookies: inline, file-based, load/save, cookie jar, set/replace, and remove.
- Query parameters: set, replace, remove, and template-variable expansion.
- Request bodies: plain payload, payload file, JSON, JSON file, form, form file, binary file, multipart fields/files, and body replacement.
- Raw HTTP/1.1 replay and cURL import.
- Redirect following, redirect-chain display, and `--no-redirects`.
- Pretty JSON and raw response output.
- Response body output with `-o`.
- Prepared-request export, cURL export, and Python `requests` export.
- JSON and HTML reports, report redaction, explicit unredacted reports, and session evidence.
- Interactive mode.
- Local file/response diff with JSON output and the expected changed-result exit code.
- `.config` generation.

## JavaScript browser engine validation

The following browser-mode paths were validated:

- Browser CLI arguments and organized help.
- Browser dry-run planning.
- Chromium/Firefox/WebKit engine selection parsing.
- Lifecycle wait, selector wait, extra wait, viewport, explicit executable, storage-state load/save, headed/headless, and JavaScript-specific Python export paths.
- Browser report metadata and browser session artifacts.
- GET-only boundary and rejection of body-based requests or `--no-redirects`.
- Viewport validation and browser-support detection.
- Full browser execution logic with a simulated Playwright runtime, including rendered DOM, final URL, response metadata, title, console messages, page errors, cookies, and storage state.
- CLI browser execution/report/output integration with a simulated Playwright result.

The environment had Playwright and a system Chromium executable, but live Chromium navigation was blocked by an environment browser policy (`ERR_BLOCKED_BY_ADMINISTRATOR`). Downloading another Playwright browser runtime was also unavailable because external DNS access failed. Therefore, browser integration was validated through dry-run, Web API generation, support detection, and controlled Playwright simulation rather than claiming a successful live browser navigation in this container.

## Web Console validation

The local Web Console was tested through its HTTP API and static UI structure:

- `GET /api/info` returned version `1.8.0`, signature `imr`, Playwright status, and detected browser information.
- `GET /` returned the reorganized Web Console.
- Exactly one `Run request` button is present, in the upper-right header next to the version.
- UI sections are organized as Request, Replay & Import, Modifiers & Data, Browser & Network, Output & Reports, Response Diff, and Feature Map.
- Required HTTP and browser controls are present.
- Inline JavaScript passed `node --check`.
- Rapid Web job creation was validated after replacing millisecond-only names with collision-resistant temporary directories.
- `POST /api/run` executed a controlled standard HTTP request with headers, cookies, JSON body, reports, and session artifacts.
- `POST /api/run` generated and validated a JavaScript-browser dry-run command.
- `POST /api/diff` produced the expected changed-result code and downloadable diff metadata.

## Installer and updater validation

Linux/macOS installer:

- Shell syntax passed.
- Installation under an isolated temporary HOME completed.
- The installer created the command wrapper and config.
- The installer persisted `export PATH="$HOME/.local/bin:$PATH"` in the shell profile.
- Installed `forgrequest --version`, HTTP execution, `web --help`, and `browser-install --help` worked.
- Uninstall removed the application wrapper and application directory while retaining configuration behavior.

Windows installer:

- The CMD-only installer was reviewed statically.
- Non-printable/control-character validation passed.
- PATH, `FORGREQUEST_CONFIG`, and `FORGREQUEST_INSTALL_DIR` configuration is present.
- The Chromium detection/install command references the correct `forgrequest.py` path.
- Windows execution itself was not possible in the Linux validation environment.

Updater:

- Local-ZIP dry-run passed.
- Local-ZIP update passed.
- Configuration and local report directories were preserved.
- `--no-deps` and `--no-browser-runtime` were validated for controlled offline update testing.
