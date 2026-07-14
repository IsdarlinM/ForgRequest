# Windows Installer

Run from CMD in the project root:

```cmd
install\windows\install_windows.cmd
```

No PowerShell installer is required or shipped.

Default paths:

```text
Application: %LOCALAPPDATA%\Programs\forgrequest
Config:      %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:     %LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd
```

The CMD installer updates the user environment through `HKCU\Environment`:

```text
Path += %LOCALAPPDATA%\Programs\forgrequest
FORGREQUEST_CONFIG=%LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
FORGREQUEST_INSTALL_DIR=%LOCALAPPDATA%\Programs\forgrequest
```

Open a new terminal if the current terminal does not immediately detect `forgrequest`.

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```

The uninstall action removes the application directory. If desired, remove the PATH entry manually from Environment Variables.

Update after installation:

```cmd
forgrequest update --dry-run
forgrequest update --yes
```
