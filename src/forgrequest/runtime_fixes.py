"""Runtime hardening for installed ForgRequest builds.

Keeps dependency management isolated from externally-managed system Python
installations (PEP 668) and refreshes launch wrappers after updates.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _venv_python(install_dir: Path) -> Path:
    if os.name == "nt":
        return install_dir / ".venv" / "Scripts" / "python.exe"
    return install_dir / ".venv" / "bin" / "python"


def _base_python() -> str:
    return str(getattr(sys, "_base_executable", None) or sys.executable)


def _ensure_venv(install_dir: Path, update_error: type[Exception]) -> Path:
    python_bin = _venv_python(install_dir)
    if python_bin.is_file():
        return python_bin
    venv_dir = install_dir / ".venv"
    print(f"[+] Creating isolated Python environment: {venv_dir}")
    result = subprocess.run(
        [_base_python(), "-m", "venv", str(venv_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0 or not python_bin.is_file():
        raise update_error(
            "Could not create the ForgRequest virtual environment.\n"
            + result.stdout
            + "\nInstall Python venv support (Kali/Debian: python3-venv or python3-full) and retry."
        )
    return python_bin


def _refresh_wrapper(install_dir: Path, python_bin: Path, config_path: Path | None) -> None:
    launcher = install_dir / "forgrequest.py"
    if os.name == "nt":
        wrapper = install_dir / "forgrequest.cmd"
        config = config_path or (install_dir / "forgrequest.config")
        content = (
            "@echo off\r\n"
            f'set "FORGREQUEST_CONFIG={config}"\r\n'
            f'set "FORGREQUEST_INSTALL_DIR={install_dir}"\r\n'
            f'"{python_bin}" "{launcher}" %*\r\n'
        )
    else:
        wrapper = Path.home() / ".local" / "bin" / "forgrequest"
        config = config_path or (Path.home() / ".config" / "forgrequest" / "forgrequest.config")
        content = (
            "#!/usr/bin/env bash\n"
            f'export FORGREQUEST_CONFIG="{config}"\n'
            f'export FORGREQUEST_INSTALL_DIR="{install_dir}"\n'
            f'exec "{python_bin}" "{launcher}" "$@"\n'
        )
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    tmp = wrapper.with_name(wrapper.name + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="")
    if os.name != "nt":
        tmp.chmod(0o755)
    tmp.replace(wrapper)
    print(f"[+] Command wrapper refreshed: {wrapper}")


def patch_updater(module: Any) -> None:
    """Patch the bundled updater without changing its public CLI contract."""
    if getattr(module, "_FORGREQUEST_PEP668_PATCHED", False):
        return
    update_error = module.UpdateError
    original_update = module.update_from_source_zip

    def run_dependency_install(install_dir: Path) -> None:
        requirements = install_dir / "requirements.txt"
        python_bin = _ensure_venv(install_dir, update_error)
        if not requirements.is_file():
            return
        result = subprocess.run(
            [str(python_bin), "-m", "pip", "install", "-r", str(requirements)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode != 0:
            raise update_error(
                "Dependency installation failed inside the ForgRequest virtual environment:\n" + result.stdout
            )

    def ensure_browser_runtime(install_dir: Path) -> None:
        candidates = [
            "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
            "chrome", "msedge", "microsoft-edge",
        ]
        if any(shutil.which(name) for name in candidates):
            print("[+] System Chromium/Chrome/Edge detected; browser mode can use it directly.")
            return
        python_bin = _ensure_venv(install_dir, update_error)
        launcher = install_dir / "forgrequest.py"
        if not launcher.is_file():
            return
        print("[+] Installing Playwright Chromium runtime for JavaScript browser mode...")
        result = subprocess.run([str(python_bin), str(launcher), "browser-install", "chromium"])
        if result.returncode != 0:
            print("[!] Chromium runtime installation failed. HTTP mode remains available.")
            print("    Retry later with: forgrequest browser-install chromium")

    def update_from_source_zip(args: Any) -> int:
        result = int(original_update(args))
        if result != 0:
            return result
        install_dir = Path(args.install_dir).expanduser().resolve() if args.install_dir else module.project_root_from_module()
        python_bin = _venv_python(install_dir)
        if not python_bin.is_file() and not args.no_deps:
            python_bin = _ensure_venv(install_dir, update_error)
        if python_bin.is_file():
            config_path = Path(args.config).expanduser().resolve() if args.config else module.resolve_default_config(install_dir)
            _refresh_wrapper(install_dir, python_bin, config_path)
            validation = subprocess.run(
                [str(python_bin), str(install_dir / "forgrequest.py"), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if validation.returncode != 0:
                raise update_error("Updated installation validation failed:\n" + validation.stdout)
        return result

    module.run_dependency_install = run_dependency_install
    module.ensure_browser_runtime = ensure_browser_runtime
    module.update_from_source_zip = update_from_source_zip
    module._FORGREQUEST_PEP668_PATCHED = True


def patch_cli_namespace(namespace: dict[str, Any]) -> None:
    """Replace browser runtime bootstrap so it never writes to system/user pip."""
    def install_browser_runtime(argv: list[str]) -> int:
        parser = namespace["build_browser_install_parser"]()
        args = parser.parse_args(argv)
        try:
            import playwright  # noqa: F401
        except ImportError:
            if sys.prefix == sys.base_prefix:
                namespace["die"](
                    "Playwright is not installed in an isolated Python environment. "
                    "Rerun the ForgRequest installer/update, or create a virtual environment and install requirements.txt first.",
                    2,
                )
            print("[+] Installing the Playwright Python package inside the active virtual environment...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", "playwright>=1.40.0,<2"])
            if result.returncode != 0:
                namespace["die"]("Could not install Playwright inside the active virtual environment.", 2)

        browsers = ["chromium", "firefox", "webkit"] if args.browser == "all" else [args.browser]
        command = [sys.executable, "-m", "playwright", "install"]
        if args.with_deps:
            command.append("--with-deps")
        command.extend(browsers)
        print("[+] Installing Playwright runtime: " + ", ".join(browsers))
        completed = subprocess.run(command)
        if completed.returncode != 0:
            namespace["die"]("Playwright browser installation failed. Review the installer output above.", 2)
        print("[+] Browser runtime installed successfully.")
        return 0

    namespace["install_browser_runtime"] = install_browser_runtime
