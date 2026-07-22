"""Runtime loader for the bundled ForgRequest CLI implementation."""
from pathlib import Path as _Path

_parts = _Path(__file__).with_name("_source") / "cli"
_source = "".join(path.read_text(encoding="utf-8") for path in sorted(_parts.iterdir()) if path.is_file())
exec(compile(_source, str(__file__), "exec"), globals(), globals())

from . import updater as _updater
from .runtime_fixes import patch_cli_namespace as _patch_cli_namespace, patch_updater as _patch_updater

_patch_updater(_updater)
_patch_cli_namespace(globals())
