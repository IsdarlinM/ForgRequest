"""Runtime loader for the bundled ForgRequest Web Console implementation."""
from pathlib import Path as _Path

_parts = _Path(__file__).with_name("_source") / "webui"
_source = "".join(path.read_text(encoding="utf-8") for path in sorted(_parts.iterdir()) if path.is_file())
exec(compile(_source, str(__file__), "exec"), globals(), globals())
