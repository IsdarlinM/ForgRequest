#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="forgrequest"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/$APP_NAME"

resolve_project_root() {
  local candidates=(
    "$SCRIPT_DIR"
    "$SCRIPT_DIR/.."
    "$SCRIPT_DIR/../.."
  )
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate/forgrequest.py" && -f "$candidate/src/forgrequest/cli.py" ]]; then
      cd "$candidate" && pwd
      return 0
    fi
  done
  echo "[!] Could not find project root. Expected forgrequest.py and src/forgrequest/cli.py." >&2
  exit 1
}

ensure_shell_path() {
  local export_line='export PATH="$HOME/.local/bin:$PATH"'
  local files=()

  # ~/.profile is used by many login shells. ~/.bashrc and ~/.zshrc cover common interactive shells.
  files+=("$HOME/.profile")
  [[ -f "$HOME/.bashrc" ]] && files+=("$HOME/.bashrc")
  [[ -f "$HOME/.zshrc" ]] && files+=("$HOME/.zshrc")

  for rc_file in "${files[@]}"; do
    mkdir -p "$(dirname "$rc_file")"
    touch "$rc_file"
    if ! grep -Fq 'export PATH="$HOME/.local/bin:$PATH"' "$rc_file"; then
      {
        echo ""
        echo "# Added by ForgRequest installer"
        echo "$export_line"
      } >> "$rc_file"
      echo "[+] Added PATH update to: $rc_file"
    fi
  done

  # Make the command available to child processes launched by this installer.
  export PATH="$BIN_DIR:$PATH"
}

PROJECT_ROOT="$(resolve_project_root)"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$WRAPPER"
  rm -rf "$INSTALL_DIR"
  echo "[+] $APP_NAME uninstalled. Configuration kept at: $CONFIG_DIR"
  echo "    Delete that directory manually if you also want to remove the configuration."
  exit 0
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[!] $PYTHON_BIN was not found. Install Python 3.10+ and run again." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("[!] Python 3.10+ is required")
PY

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$BIN_DIR"
rm -rf "$INSTALL_DIR/src"
cp -R "$PROJECT_ROOT/src" "$INSTALL_DIR/src"
cp "$PROJECT_ROOT/forgrequest.py" "$INSTALL_DIR/forgrequest.py"
cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/requirements.txt" 2>/dev/null || true
cp "$PROJECT_ROOT/README.md" "$INSTALL_DIR/README.md" 2>/dev/null || true
cp "$PROJECT_ROOT/pyproject.toml" "$INSTALL_DIR/pyproject.toml" 2>/dev/null || true
chmod +x "$INSTALL_DIR/forgrequest.py"

if [[ -f "$PROJECT_ROOT/config/forgrequest.config" && ! -f "$CONFIG_DIR/forgrequest.config" ]]; then
  cp "$PROJECT_ROOT/config/forgrequest.config" "$CONFIG_DIR/forgrequest.config"
elif [[ ! -f "$CONFIG_DIR/forgrequest.config" ]]; then
  "$PYTHON_BIN" "$INSTALL_DIR/forgrequest.py" --init-config -c "$CONFIG_DIR/forgrequest.config"
fi

if ! "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
  echo "[+] Installing requests dependency for the current user..."
  "$PYTHON_BIN" -m pip install --user -r "$INSTALL_DIR/requirements.txt"
fi

cat > "$WRAPPER" <<EOF_WRAPPER
#!/usr/bin/env bash
export FORGREQUEST_CONFIG="$CONFIG_DIR/forgrequest.config"
exec "$PYTHON_BIN" "$INSTALL_DIR/forgrequest.py" "\$@"
EOF_WRAPPER
chmod +x "$WRAPPER"

ensure_shell_path

if ! "$WRAPPER" --help >/dev/null 2>&1; then
  echo "[!] Installation completed, but the command test failed." >&2
  exit 1
fi

# Also verify the PATH-resolved command from this installer process.
if ! forgrequest --help >/dev/null 2>&1; then
  echo "[!] PATH was configured, but command lookup failed in this installer process." >&2
  exit 1
fi

echo "[+] Installed successfully."
echo "[+] Command: forgrequest"
echo "[+] Wrapper: $WRAPPER"
echo "[+] Install dir: $INSTALL_DIR"
echo "[+] Config:  $CONFIG_DIR/forgrequest.config"
echo "[+] PATH configured with: export PATH=\"$HOME/.local/bin:\$PATH\""
echo "[+] Open a new terminal if the current parent shell does not immediately see the command."
echo "[+] Test: forgrequest -u https://example.com --dry-run --no-logo"
