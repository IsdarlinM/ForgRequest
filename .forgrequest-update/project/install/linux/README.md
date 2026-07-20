# Linux/macOS Installer

Run from the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Default paths:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

The installer automatically adds this line to common shell startup files when it is missing:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The wrapper created at `~/.local/bin/forgrequest` exports:

```bash
FORGREQUEST_CONFIG="$HOME/.config/forgrequest/forgrequest.config"
FORGREQUEST_INSTALL_DIR="$HOME/.local/share/forgrequest"
```

These variables allow the command to work immediately in new terminals and allow `forgrequest update` to locate the active installation safely.

The installer also installs the Playwright Python dependency. It uses an existing system Chromium/Chrome when available; otherwise it attempts to download the Playwright Chromium runtime. Browser setup can be retried with:

```bash
forgrequest browser-install chromium
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

The uninstall action removes the command wrapper and application directory, but keeps the configuration directory. Delete `~/.config/forgrequest` manually if you also want to remove configuration.

Update after installation:

```bash
forgrequest update --dry-run
forgrequest update --yes
```
