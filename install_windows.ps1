[CmdletBinding()]
param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$AppName = "forgrequest"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\forgrequest"
$ConfigPath = Join-Path $InstallDir "forgrequest.config"
$WrapperPath = Join-Path $InstallDir "forgrequest.cmd"

function Resolve-ProjectRoot {
    $candidates = @(
        $ScriptDir,
        (Join-Path $ScriptDir ".."),
        (Join-Path $ScriptDir "..\..")
    )
    foreach ($candidate in $candidates) {
        $root = Resolve-Path $candidate -ErrorAction SilentlyContinue
        if ($root) {
            $rootPath = $root.Path
            if ((Test-Path (Join-Path $rootPath "forgrequest.py")) -and (Test-Path (Join-Path $rootPath "src\forgrequest\cli.py"))) {
                return $rootPath
            }
        }
    }
    throw "Could not find project root. Expected forgrequest.py and src\forgrequest\cli.py."
}

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python was not found. Install Python 3.10+ and enable 'Add python.exe to PATH'."
}

function Invoke-Python {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$PythonArgs
    )
    $cmd = Get-PythonCommand
    $exe = $cmd[0]
    $prefix = @()
    if ($cmd.Length -gt 1) { $prefix = $cmd[1..($cmd.Length - 1)] }
    & $exe @prefix @PythonArgs
}

if ($Uninstall) {
    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
    }
    Write-Host "[+] $AppName uninstalled from $InstallDir"
    Write-Host "[!] If this installer added PATH, you can remove it manually from Environment Variables."
    exit 0
}

$ProjectRoot = Resolve-ProjectRoot
Invoke-Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10+ is required."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$TargetSrc = Join-Path $InstallDir "src"
if (Test-Path $TargetSrc) {
    Remove-Item -Recurse -Force $TargetSrc
}
Copy-Item -Recurse -Force (Join-Path $ProjectRoot "src") $TargetSrc
Copy-Item -Force (Join-Path $ProjectRoot "forgrequest.py") (Join-Path $InstallDir "forgrequest.py")
foreach ($file in @("requirements.txt", "README.md", "pyproject.toml")) {
    $source = Join-Path $ProjectRoot $file
    if (Test-Path $source) {
        Copy-Item -Force $source (Join-Path $InstallDir $file)
    }
}

$SourceConfig = Join-Path $ProjectRoot "config\forgrequest.config"
if ((Test-Path $SourceConfig) -and !(Test-Path $ConfigPath)) {
    Copy-Item -Force $SourceConfig $ConfigPath
} elseif (!(Test-Path $ConfigPath)) {
    Invoke-Python (Join-Path $InstallDir "forgrequest.py") --init-config -c $ConfigPath
}

Invoke-Python -c "import requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[+] Installing requests dependency for the current user..."
    $ReqPath = Join-Path $InstallDir "requirements.txt"
    if (Test-Path $ReqPath) {
        Invoke-Python -m pip install --user -r $ReqPath
    } else {
        Invoke-Python -m pip install --user requests
    }
}

$cmd = Get-PythonCommand
$PyPrefix = ($cmd -join " ")
$Wrapper = @"
@echo off
$PyPrefix "%~dp0forgrequest.py" -c "%~dp0forgrequest.config" %*
"@
Set-Content -Path $WrapperPath -Value $Wrapper -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
$pathParts = $userPath.Split(';', [System.StringSplitOptions]::RemoveEmptyEntries)
if ($pathParts -notcontains $InstallDir) {
    $newPath = if ($userPath.Trim()) { "$userPath;$InstallDir" } else { $InstallDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$InstallDir"
    Write-Host "[+] Added to user PATH: $InstallDir"
    Write-Host "[!] Open a new terminal so Windows loads the updated PATH."
}

& $WrapperPath --help > $null
if ($LASTEXITCODE -ne 0) {
    throw "Installation completed, but the command test failed."
}

Write-Host "[+] Installed successfully."
Write-Host "[+] Command: forgrequest"
Write-Host "[+] Install dir: $InstallDir"
Write-Host "[+] Config:   $ConfigPath"
Write-Host "[+] Test:    forgrequest -u https://example.com --dry-run --no-logo"
