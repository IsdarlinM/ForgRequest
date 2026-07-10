# ForgRequest validation results

Environment used for validation:

- Linux container
- Python 3.13 runtime available in the execution environment
- Dependency: `requests`

Validation performed:

1. Python syntax compilation for:
   - `src/forgrequest/cli.py`
   - `src/forgrequest/__init__.py`
   - `forgrequest.py`
2. CLI help validation with `python forgrequest.py --help`.
3. Dry-run validation for:
   - basic request preparation
   - variable substitution with `--vars-file`
   - sensitive header redaction
   - raw HTTP request import with `--raw-request`
   - cookie removal from imported raw requests
   - query parameter modification
   - prepared raw request export
   - cURL export
   - Python `requests` export
   - JSON report generation
   - HTML report generation
   - session artifact generation
   - cURL import with `--from-curl`
   - local diff command with `forgrequest diff`
4. Live local HTTP server validation for:
   - GET response rendering
   - response headers with `--include`
   - redirect chain with `--show-redirect-chain`
   - cookie jar save/load with `--cookie-jar`
   - JSON POST helper with `--json`
   - multipart POST helper with `--multipart`
   - HEAD request handling
   - JSON/HTML report creation
   - session artifact creation
5. Linux installer validation using an isolated temporary `HOME`:
   - install
   - wrapper command execution
   - dry-run through installed command
   - uninstall

Windows installer note:

- The Windows PowerShell/BAT installer files were statically reviewed and updated.
- They were not executed because the validation environment is Linux-only.
