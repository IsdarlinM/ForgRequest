# ForgRequest installers

Installers are organized by operating system and are the only supported installation entry points. There are no root-level convenience installers.

```text
install/
├── linux/
│   ├── install_linux.sh
│   └── README.md
└── windows/
    ├── install_windows.cmd
    └── README.md
```

## Linux/macOS

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

The installer creates the command wrapper in `~/.local/bin/forgrequest` and automatically appends this PATH line to common shell startup files when needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

## Windows

Use the CMD installer:

```cmd
install\windows\install_windows.cmd
```

The installer creates `%LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd` and updates the user PATH from the `.cmd` installer so the `forgrequest` command is available in new terminals. It also sets the user-level `FORGREQUEST_CONFIG` environment variable.

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```
