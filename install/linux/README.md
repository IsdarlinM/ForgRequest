# Linux/macOS Installer

Run from the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Default paths:

```text
Application:        ~/.local/share/forgrequest
Python environment: ~/.local/share/forgrequest/.venv
Config:             ~/.config/forgrequest/forgrequest.config
Command:            ~/.local/bin/forgrequest
```

The installer creates an application-owned Python virtual environment and installs ForgRequest dependencies inside it. It does not install packages into Kali/Debian's externally managed system Python and does not require `pip --user` or `--break-system-packages`.

If virtual-environment support is missing on Kali/Debian, install it first:

```bash
apt update
apt install python3-venv
```

`python3-full` is also suitable when a complete Python environment is desired.

The installer automatically adds this line to common shell startup files when it is missing:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The wrapper created at `~/.local/bin/forgrequest` exports:

```bash
FORGREQUEST_CONFIG="$HOME/.config/forgrequest/forgrequest.config"
FORGREQUEST_INSTALL_DIR="$HOME/.local/share/forgrequest"
```

and executes ForgRequest with:

```text
~/.local/share/forgrequest/.venv/bin/python
```

The installer uses an existing system Chromium/Chrome when available; otherwise it attempts to install the Playwright Chromium runtime. Browser setup can be retried with:

```bash
forgrequest browser-install chromium
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

The uninstall action removes the command wrapper, application directory, and managed `.venv`, but keeps the configuration directory.

Update after installation:

```bash
forgrequest update --dry-run
forgrequest update --yes
```

For an older installation that currently fails with `externally-managed-environment`, bootstrap the fixed updater without dependency installation first:

```bash
forgrequest update --no-deps --no-browser-runtime --yes
forgrequest update --yes
```

The second command creates/migrates the managed `.venv`, installs dependencies there, and refreshes the command wrapper.
