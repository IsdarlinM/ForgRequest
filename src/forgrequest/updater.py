#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe updater for ForgRequest.

The updater replaces the local application files from a release/source ZIP while
preserving local configuration and operator-generated artifacts. It is designed
for authorized local maintenance only; it does not crawl or scan anything.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable

DEFAULT_REPO_OWNER = "IsdarlinM"
DEFAULT_REPO_NAME = "ForgRequest"
DEFAULT_BRANCH = "main"
DEFAULT_ZIP_URL = f"https://github.com/{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}/archive/refs/heads/{DEFAULT_BRANCH}.zip"
DEFAULT_TIMEOUT = 30

PRESERVE_NAMES = {
    "forgrequest.config",
    ".env",
    ".venv",
    "venv",
    "env",
    "reports",
    "report",
    "sessions",
    "session",
    "cases",
    "case",
    "outputs",
    "output",
    "artifacts",
    "web-artifacts",
    "workspace",
    "workspaces",
    "projects",
    "data",
}

SKIP_COPY_NAMES = {
    ".git",
    ".github",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}

SKIP_COPY_SUFFIXES = {".pyc", ".pyo", ".log"}


class UpdateError(RuntimeError):
    """Raised when an update cannot be completed safely."""


def build_update_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgrequest update",
        description="Safely update the local ForgRequest installation from GitHub or a local ZIP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url", default=DEFAULT_ZIP_URL, help="ZIP URL to download. Defaults to the official GitHub main branch archive.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="GitHub branch to use when --url is not customized.")
    parser.add_argument("--repo-owner", default=DEFAULT_REPO_OWNER, help="GitHub repository owner used to build the default ZIP URL.")
    parser.add_argument("--repo-name", default=DEFAULT_REPO_NAME, help="GitHub repository name used to build the default ZIP URL.")
    parser.add_argument("--from-zip", help="Use a local ZIP file instead of downloading from GitHub. Useful for offline validation.")
    parser.add_argument("--install-dir", help="Installation/project directory to update. Auto-detected by default.")
    parser.add_argument("--config", help="Config file to preserve. Defaults to FORGREQUEST_CONFIG or the detected local config.")
    parser.add_argument("--backup-dir", help="Directory where backups are stored. Defaults to a sibling backup next to the install dir.")
    parser.add_argument("--keep-backup", action="store_true", help="Keep the backup after a successful update.")
    parser.add_argument("--no-deps", action="store_true", help="Do not run pip dependency installation after copying the update.")
    parser.add_argument("--dry-run", action="store_true", help="Validate source/destination and show planned actions without changing files.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Download timeout in seconds.")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    return parser


def project_root_from_module() -> Path:
    env_dir = os.getenv("FORGREQUEST_INSTALL_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def resolve_default_config(install_dir: Path) -> Path | None:
    env_config = os.getenv("FORGREQUEST_CONFIG")
    candidates: list[Path] = []
    if env_config:
        candidates.append(Path(env_config).expanduser())
    candidates.extend(
        [
            install_dir / "forgrequest.config",
            install_dir / "config" / "forgrequest.config",
            Path.home() / ".config" / "forgrequest" / "forgrequest.config",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def make_default_url(owner: str, repo: str, branch: str, explicit_url: str) -> str:
    if explicit_url != DEFAULT_ZIP_URL:
        return explicit_url
    return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"


def download_zip(url: str, destination: Path, timeout: int) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ForgRequest-Updater"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise UpdateError(f"Download failed with HTTP status {status}")
            with destination.open("wb") as fh:
                shutil.copyfileobj(response, fh)
    except urllib.error.URLError as exc:
        raise UpdateError(f"Could not download update ZIP: {exc}") from exc
    except OSError as exc:
        raise UpdateError(f"Could not save update ZIP: {exc}") from exc


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                target = (destination / member.filename).resolve()
                try:
                    target.relative_to(destination.resolve())
                except ValueError as exc:
                    raise UpdateError(f"Unsafe ZIP path detected: {member.filename}") from exc
            zf.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise UpdateError(f"Invalid ZIP file: {zip_path}") from exc


def find_extracted_project_root(extract_dir: Path) -> Path:
    candidates = []
    for path in extract_dir.iterdir():
        if path.is_dir():
            candidates.append(path)
    candidates.append(extract_dir)
    for candidate in candidates:
        if (candidate / "forgrequest.py").is_file() and (candidate / "src" / "forgrequest" / "cli.py").is_file():
            return candidate.resolve()
    raise UpdateError("The update archive does not look like a ForgRequest project. Expected forgrequest.py and src/forgrequest/cli.py.")


def validate_project_root(path: Path) -> None:
    if not path.is_dir():
        raise UpdateError(f"Install directory does not exist: {path}")
    if not (path / "forgrequest.py").is_file():
        raise UpdateError(f"Install directory is missing forgrequest.py: {path}")
    if not (path / "src" / "forgrequest" / "cli.py").is_file():
        raise UpdateError(f"Install directory is missing src/forgrequest/cli.py: {path}")


def should_skip_copy(path: Path) -> bool:
    if path.name in SKIP_COPY_NAMES:
        return True
    if path.suffix.lower() in SKIP_COPY_SUFFIXES:
        return True
    return False


def iter_items(path: Path) -> Iterable[Path]:
    return sorted(path.iterdir(), key=lambda item: item.name.lower())


def copy_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in iter_items(src):
        if should_skip_copy(item):
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        else:
            shutil.copy2(item, target)


def collect_preserve_paths(install_dir: Path, config_path: Path | None) -> list[Path]:
    paths: list[Path] = []
    for child in install_dir.iterdir() if install_dir.exists() else []:
        if child.name in PRESERVE_NAMES:
            paths.append(child)
    if config_path and config_path.exists():
        paths.append(config_path)
    # Deduplicate by resolved path while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def copy_preserved_to_backup(paths: list[Path], backup_root: Path) -> None:
    preserve_root = backup_root / "_preserved"
    preserve_root.mkdir(parents=True, exist_ok=True)
    manifest = []
    for path in paths:
        if not path.exists():
            continue
        safe_name = str(path.resolve()).strip(os.sep).replace(":", "").replace(os.sep, "__")
        target = preserve_root / safe_name
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        manifest.append({"source": str(path.resolve()), "backup": str(target)})
    (preserve_root / "manifest.json").write_text(__import__("json").dumps(manifest, indent=2), encoding="utf-8")


def restore_preserved_from_backup(backup_root: Path) -> None:
    preserve_root = backup_root / "_preserved"
    manifest_path = preserve_root / "manifest.json"
    if not manifest_path.is_file():
        return
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest:
        source = Path(item["source"])
        backup = Path(item["backup"])
        if not backup.exists():
            continue
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
        if backup.is_dir():
            shutil.copytree(backup, source)
        else:
            shutil.copy2(backup, source)


def run_dependency_install(install_dir: Path) -> None:
    requirements = install_dir / "requirements.txt"
    if not requirements.is_file():
        return
    cmd = [sys.executable, "-m", "pip", "install", "--user", "-r", str(requirements)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise UpdateError("Dependency installation failed:\n" + result.stdout)


def prompt_confirmation(install_dir: Path, source_label: str, yes: bool) -> None:
    if yes:
        return
    print("[Update plan]")
    print(f"Source:      {source_label}")
    print(f"Destination: {install_dir}")
    print("A full backup will be created before replacing application files.")
    answer = input("Continue? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        raise UpdateError("Update cancelled by operator")


def update_from_source_zip(args: argparse.Namespace) -> int:
    install_dir = Path(args.install_dir).expanduser().resolve() if args.install_dir else project_root_from_module()
    validate_project_root(install_dir)

    config_path = Path(args.config).expanduser().resolve() if args.config else resolve_default_config(install_dir)
    source_url = make_default_url(args.repo_owner, args.repo_name, args.branch, args.url)
    source_label = str(Path(args.from_zip).expanduser().resolve()) if args.from_zip else source_url
    prompt_confirmation(install_dir, source_label, args.yes or args.dry_run)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(args.backup_dir).expanduser().resolve() if args.backup_dir else install_dir.parent / f"{install_dir.name}.backup-{timestamp}"

    print(f"[+] Install dir: {install_dir}")
    if config_path:
        print(f"[+] Preserving config: {config_path}")
    print(f"[+] Backup dir: {backup_dir}")

    with tempfile.TemporaryDirectory(prefix="forgrequest-update-") as tmp_name:
        tmp = Path(tmp_name)
        zip_path = Path(args.from_zip).expanduser().resolve() if args.from_zip else tmp / "update.zip"
        if not args.from_zip:
            print(f"[+] Downloading update: {source_url}")
            if not args.dry_run:
                download_zip(source_url, zip_path, args.timeout)
        elif not zip_path.is_file():
            raise UpdateError(f"Local ZIP not found: {zip_path}")

        extract_dir = tmp / "extract"
        extract_dir.mkdir()
        if not args.dry_run:
            safe_extract_zip(zip_path, extract_dir)
            source_root = find_extracted_project_root(extract_dir)
        else:
            # Dry-run still validates local ZIP structure when possible.
            if args.from_zip:
                safe_extract_zip(zip_path, extract_dir)
                source_root = find_extracted_project_root(extract_dir)
            else:
                source_root = Path("<downloaded ForgRequest archive>")
        print(f"[+] Update source: {source_root}")

        preserved = collect_preserve_paths(install_dir, config_path)
        if preserved:
            print("[+] Local items selected for preservation:")
            for path in preserved:
                print(f"    - {path}")

        if args.dry_run:
            print("[+] Dry-run complete. No files were changed.")
            return 0

        if backup_dir.exists():
            raise UpdateError(f"Backup directory already exists: {backup_dir}")
        print("[+] Creating full backup...")
        shutil.copytree(install_dir, backup_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        copy_preserved_to_backup(preserved, backup_dir)

        try:
            print("[+] Replacing application files...")
            for item in list(install_dir.iterdir()):
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            copy_tree_contents(source_root, install_dir)
            restore_preserved_from_backup(backup_dir)
            if not args.no_deps:
                print("[+] Verifying dependencies...")
                run_dependency_install(install_dir)
        except Exception:
            print("[!] Update failed. Restoring previous installation...", file=sys.stderr)
            if install_dir.exists():
                shutil.rmtree(install_dir)
            shutil.copytree(backup_dir, install_dir)
            raise

    print("[+] Update completed successfully.")
    if args.keep_backup:
        print(f"[+] Backup kept at: {backup_dir}")
    else:
        try:
            shutil.rmtree(backup_dir)
            print("[+] Backup removed after successful update. Use --keep-backup to preserve it.")
        except OSError as exc:
            print(f"[!] Could not remove backup {backup_dir}: {exc}", file=sys.stderr)
    print("[+] Test: forgrequest --version")
    return 0


def run_update(argv: list[str] | None = None) -> int:
    parser = build_update_parser()
    args = parser.parse_args(argv)
    try:
        return update_from_source_zip(args)
    except KeyboardInterrupt:
        print("\n[!] Update cancelled", file=sys.stderr)
        return 1
    except UpdateError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1
