# ForgRequest Installers

Installers are organized by operating system and are stored only under this directory.

```text
install/
├── README.md
├── linux/
│   ├── README.md
│   └── install_linux.sh
└── windows/
    ├── README.md
    └── install_windows.cmd
```

## Linux/macOS

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

The Linux/macOS installer:

- installs the application under `~/.local/share/forgrequest`;
- installs the config under `~/.config/forgrequest/forgrequest.config`;
- creates the command wrapper at `~/.local/bin/forgrequest`;
- adds `export PATH="$HOME/.local/bin:$PATH"` to common shell startup files when missing;
- sets `FORGREQUEST_CONFIG` and `FORGREQUEST_INSTALL_DIR` inside the installed wrapper;
- installs Playwright support and uses or installs Chromium for JavaScript browser mode;
- supports uninstall with `./install/linux/install_linux.sh --uninstall`.

## Windows

```cmd
install\windows\install_windows.cmd
```

The Windows installer is CMD-only. No PowerShell installer is shipped.

The Windows installer:

- installs the application under `%LOCALAPPDATA%\Programs\forgrequest`;
- installs the config at `%LOCALAPPDATA%\Programs\forgrequest\forgrequest.config`;
- creates `%LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd`;
- updates the user PATH through `HKCU\Environment`;
- sets `FORGREQUEST_CONFIG` and `FORGREQUEST_INSTALL_DIR` as user environment variables;
- installs Playwright support and uses Chrome/Edge or installs Chromium for JavaScript browser mode;
- supports uninstall with `install\windows\install_windows.cmd --uninstall`.

## Update command

After installation, update with:

```bash
forgrequest update --yes
```

Dry-run first:

```bash
forgrequest update --dry-run
```

The updater uses `FORGREQUEST_INSTALL_DIR` when available, creates a full backup, preserves local configuration/artifacts, and restores the previous installation if the update fails.

## Browser runtime

```bash
forgrequest browser-install chromium
forgrequest browser-install all
```

Browser runtime failure does not disable standard HTTP request replay.
