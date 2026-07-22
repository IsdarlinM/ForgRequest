# Windows Installer

Run from CMD in the project root:

```cmd
install\windows\install_windows.cmd
```

No PowerShell installer is required or shipped.

Default paths:

```text
Application:        %LOCALAPPDATA%\Programs\forgrequest
Python environment: %LOCALAPPDATA%\Programs\forgrequest\.venv
Config:             %LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
Command:            %LOCALAPPDATA%\Programs\forgrequest\forgrequest.cmd
```

The CMD installer creates an application-owned Python virtual environment, installs dependencies inside it, and makes the wrapper execute:

```text
%LOCALAPPDATA%\Programs\forgrequest\.venv\Scripts\python.exe
```

The installer updates the user environment through `HKCU\Environment`:

```text
Path += %LOCALAPPDATA%\Programs\forgrequest
FORGREQUEST_CONFIG=%LOCALAPPDATA%\Programs\forgrequest\forgrequest.config
FORGREQUEST_INSTALL_DIR=%LOCALAPPDATA%\Programs\forgrequest
```

Open a new terminal if the current terminal does not immediately detect `forgrequest`.

The installer uses an existing Chrome, Chromium, or Edge executable when available; otherwise it attempts to download the Playwright Chromium runtime.

Retry browser setup when needed:

```cmd
forgrequest browser-install chromium
```

Uninstall:

```cmd
install\windows\install_windows.cmd --uninstall
```

The uninstall action removes the application directory, including the managed `.venv`. If desired, remove the PATH entry manually from Environment Variables.

Update after installation:

```cmd
forgrequest update --dry-run
forgrequest update --yes
```

The updater preserves local configuration/artifacts and refreshes `forgrequest.cmd` so it continues to use the managed `.venv` after an update.
