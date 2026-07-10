# Windows installation

From Command Prompt in the project root:

```cmd
install\windows\install_windows.cmd
```

Installed paths:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     %LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd
```

The `.cmd` installer updates the user PATH using Windows environment variables and also sets `FORGREQUEST_CONFIG`. Open a new terminal after installation if an already-open terminal does not immediately recognize `forgrequest`.

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```
