@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_NAME=forgrequest"
set "SCRIPT_DIR=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\forgrequest"
set "CONFIG_PATH=%INSTALL_DIR%\forgrequest.config"
set "WRAPPER_PATH=%INSTALL_DIR%\forgrequest.cmd"

if /I "%~1"=="--uninstall" goto uninstall
if /I "%~1"=="-Uninstall" goto uninstall
if /I "%~1"=="/uninstall" goto uninstall

call :resolve_project_root
if errorlevel 1 exit /b 1

call :find_python
if errorlevel 1 exit /b 1

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo [!] Python 3.10+ is required.
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if exist "%INSTALL_DIR%\src" rmdir /S /Q "%INSTALL_DIR%\src"
xcopy "%PROJECT_ROOT%\src" "%INSTALL_DIR%\src" /E /I /Y >nul
copy /Y "%PROJECT_ROOT%\forgrequest.py" "%INSTALL_DIR%\forgrequest.py" >nul
if exist "%PROJECT_ROOT%\requirements.txt" copy /Y "%PROJECT_ROOT%\requirements.txt" "%INSTALL_DIR%\requirements.txt" >nul
if exist "%PROJECT_ROOT%\README.md" copy /Y "%PROJECT_ROOT%\README.md" "%INSTALL_DIR%\README.md" >nul
if exist "%PROJECT_ROOT%\pyproject.toml" copy /Y "%PROJECT_ROOT%\pyproject.toml" "%INSTALL_DIR%\pyproject.toml" >nul

if not exist "%CONFIG_PATH%" (
  if exist "%PROJECT_ROOT%\config\forgrequest.config" (
    copy /Y "%PROJECT_ROOT%\config\forgrequest.config" "%CONFIG_PATH%" >nul
  ) else (
    %PY_CMD% "%INSTALL_DIR%\forgrequest.py" --init-config -c "%CONFIG_PATH%"
    if errorlevel 1 exit /b 1
  )
)

%PY_CMD% -c "import requests, playwright" >nul 2>nul
if errorlevel 1 (
  echo [+] Installing ForgRequest Python dependencies for the current user...
  if exist "%INSTALL_DIR%\requirements.txt" (
    %PY_CMD% -m pip install --user -r "%INSTALL_DIR%\requirements.txt"
  ) else (
    %PY_CMD% -m pip install --user requests
  )
  if errorlevel 1 exit /b 1
)

%PY_CMD% -c "import sys; sys.path.insert(0, r'%INSTALL_DIR%\src'); from forgrequest.browser import find_system_browser; raise SystemExit(0 if find_system_browser('chromium') else 1)" >nul 2>nul
if errorlevel 1 (
  echo [+] Installing the Playwright Chromium runtime for JavaScript browser mode...
  %PY_CMD% "%INSTALL_DIR%\forgrequest.py" browser-install chromium
  if errorlevel 1 (
    echo [!] Chromium runtime installation failed. HTTP mode remains available.
    echo     Retry later with: forgrequest browser-install chromium
  )
) else (
  echo [+] System Chrome/Chromium/Edge detected; browser mode can use it directly.
)

(
  echo @echo off
  echo set "FORGREQUEST_CONFIG=%%~dp0forgrequest.config"
  echo set "FORGREQUEST_INSTALL_DIR=%%~dp0"
  echo %PY_CMD% "%%~dp0forgrequest.py" %%*
) > "%WRAPPER_PATH%"

call :ensure_user_path "%INSTALL_DIR%"
if errorlevel 1 exit /b 1

call "%WRAPPER_PATH%" --help >nul
if errorlevel 1 (
  echo [!] Installation completed, but the command test failed.
  exit /b 1
)

echo [+] Installed successfully.
echo [+] Command: forgrequest
echo [+] Install dir: %INSTALL_DIR%
echo [+] Config:   %CONFIG_PATH%
echo [+] PATH configured for future terminals.
echo [+] Test:    forgrequest -u https://example.com --dry-run --no-logo
exit /b 0

:uninstall
if exist "%INSTALL_DIR%" rmdir /S /Q "%INSTALL_DIR%"
echo [+] %APP_NAME% uninstalled from %INSTALL_DIR%
echo [!] User PATH entries are not removed automatically. Remove %INSTALL_DIR% from Environment Variables if desired.
exit /b 0

:resolve_project_root
for %%D in ("%SCRIPT_DIR%" "%SCRIPT_DIR%.." "%SCRIPT_DIR%..\..") do (
  if exist "%%~fD\forgrequest.py" if exist "%%~fD\src\forgrequest\cli.py" (
    set "PROJECT_ROOT=%%~fD"
    exit /b 0
  )
)
echo [!] Could not find project root. Expected forgrequest.py and src\forgrequest\cli.py.
exit /b 1

:find_python
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=py -3"
  exit /b 0
)
python -c "import sys" >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=python"
  exit /b 0
)
echo [!] Python was not found. Install Python 3.10+ and enable Add python.exe to PATH.
exit /b 1

:ensure_user_path
set "PATH_TO_ADD=%~1"
set "USER_PATH="
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v Path 2^>nul ^| findstr /I "Path"') do set "USER_PATH=%%B"

echo ;%USER_PATH%; | find /I ";%PATH_TO_ADD%;" >nul
if errorlevel 1 (
  if defined USER_PATH (
    reg add HKCU\Environment /v Path /t REG_EXPAND_SZ /d "%USER_PATH%;%PATH_TO_ADD%" /f >nul
  ) else (
    reg add HKCU\Environment /v Path /t REG_EXPAND_SZ /d "%PATH_TO_ADD%" /f >nul
  )
  set "PATH=%PATH%;%PATH_TO_ADD%"
  echo [+] Added to user PATH: %PATH_TO_ADD%
) else (
  echo [+] User PATH already contains: %PATH_TO_ADD%
)

reg add HKCU\Environment /v FORGREQUEST_CONFIG /t REG_EXPAND_SZ /d "%CONFIG_PATH%" /f >nul
reg add HKCU\Environment /v FORGREQUEST_INSTALL_DIR /t REG_EXPAND_SZ /d "%INSTALL_DIR%" /f >nul
set "FORGREQUEST_CONFIG=%CONFIG_PATH%"
set "FORGREQUEST_INSTALL_DIR=%INSTALL_DIR%"
exit /b 0
