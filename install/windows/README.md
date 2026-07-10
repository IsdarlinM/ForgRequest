# Windows installer

Run from the project root using CMD:

```cmd
install\windows\install_windows.cmd
```

You can also run the underlying PowerShell script directly:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install\windows\install_windows.ps1
```

Default paths:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     forgrequest.cmd, available as forgrequest after PATH update
```

Uninstall:

```cmd
install\windows\install_windows.cmd -Uninstall
```

Open a new terminal after installation if Windows does not immediately detect the updated PATH.

After installation, the same command exposes all modes:

```bash
forgrequest --version
forgrequest web --help
forgrequest diff --help
```
