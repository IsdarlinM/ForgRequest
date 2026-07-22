# ForgRequest Installers

Installers are organized by operating system under this directory.

## Linux/macOS

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

The installer creates an application-owned virtual environment at `~/.local/share/forgrequest/.venv`, installs dependencies there, creates `~/.local/bin/forgrequest`, persists `~/.local/bin` in `PATH`, and exports `FORGREQUEST_CONFIG` plus `FORGREQUEST_INSTALL_DIR` from the wrapper.

This avoids modifying Kali/Debian's externally managed system Python and does not require `pip --user` or `--break-system-packages`.

## Windows

```cmd
install\windows\install_windows.cmd
```

The CMD installer creates `%LOCALAPPDATA%\Programs\forgrequest\.venv`, installs dependencies inside that environment, creates the command wrapper, updates the user `PATH`, and sets `FORGREQUEST_CONFIG` plus `FORGREQUEST_INSTALL_DIR`.

## Update

```bash
forgrequest update --dry-run
forgrequest update --yes
```

Updated installations use the managed `.venv`, preserve configuration and artifacts, and refresh the command wrapper after a successful update.

For an older installation that already fails with `externally-managed-environment`, bootstrap the fixed updater first:

```bash
forgrequest update --no-deps --no-browser-runtime --yes
forgrequest update --yes
```
