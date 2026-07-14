# ForgRequest v1.7.2 validation results

Validation performed in a Linux environment after reorganizing the main CLI help output.

## Help validation

- `python3 forgrequest.py --version` returns `forgrequest 1.7.2 :: signature imr`.
- `python3 forgrequest.py --help` now lists the top-level commands:
  - `web`
  - `diff`
  - `update`
- Main help is organized into workflow sections:
  - commands
  - general
  - target and method
  - request import and replay
  - headers
  - cookies
  - query parameters
  - payload and body helpers
  - template variables
  - network, redirects, proxy and TLS
  - output, display and exports
  - reports and session evidence
  - color and interactive mode
- `python3 forgrequest.py web --help` works.
- `python3 forgrequest.py diff --help` works.
- `python3 forgrequest.py update --help` works.

## CLI regression validation

The following workflows were tested successfully:

- Python compilation with `py_compile`.
- Standard dry-run request:
  - `python3 forgrequest.py -u https://example.com --dry-run --no-logo --no-color`
- Response diff command with JSON summary:
  - `python3 forgrequest.py diff a.txt b.txt --json diff.json --no-body-diff`
- Local HTTP execution against a controlled test server.
- JSON and HTML report generation.
- Response body output using `-o`.
- Raw HTTP request replay using `--raw-request`.
- cURL import using `--from-curl`.
- Redirect chain display using `--show-redirect-chain`.

## Web validation

The Web Console was started locally and validated through HTTP requests:

- `GET /api/info` returned version `1.7.2` and signature `imr`.
- `GET /` returned the Web Console HTML.
- `POST /api/run` executed a dry-run request through the web API and returned CLI output containing `Dry-run active`.

## Notes

- Windows `.cmd` installer behavior was not executed in this Linux environment.
- No screenshots are included in the deliverable.

## Web primary-action visibility and interaction

- Confirmed the sticky top navigation contains the only visible `Run request` button, next to the version indicator.
- Confirmed the Execution & Reports panel retains a redesigned primary action card.
- Confirmed desktop rendering at `1440x900`: the header action is fully inside the viewport and the sidebar action is visible without navigation.
- Confirmed mobile rendering at `390x844`: the header action remains fully visible and the sidebar action expands to the available width.
- Confirmed the sidebar quick action submits the request form.
- Confirmed `Ctrl+Enter` submits the current request form.
- Confirmed the single top-right Run request control enters a disabled/running state during execution.
- Confirmed the Web API executed a local controlled request and returned HTTP 200 with exit code `0`.
- No UI screenshots are included in the deliverable.
