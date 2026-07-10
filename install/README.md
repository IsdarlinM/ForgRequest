# ForgRequest installers

Installers are intentionally organized by operating system. There are no root-level installer duplicates.

```text
install/
├── linux/
│   ├── README.md
│   └── install_linux.sh
└── windows/
    ├── README.md
    ├── install_windows.cmd
    └── install_windows.ps1
```

Use the installer that matches your operating system from the project root.

## Linux/macOS

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

## Windows

Recommended CMD wrapper:

```cmd
install\windows\install_windows.cmd
```

Uninstall:

```cmd
install\windows\install_windows.cmd -Uninstall
```

The PowerShell script remains in the same folder because the CMD wrapper calls it with a process-scoped execution policy bypass.

After installation, the same command exposes all modes:

```bash
forgrequest --version
forgrequest web --help
forgrequest diff --help
```
