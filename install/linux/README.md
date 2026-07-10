# Linux/macOS installer

Run from the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Default paths:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```

If `~/.local/bin` is not in your `PATH`, add it to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

After installation, the same command exposes all modes:

```bash
forgrequest --version
forgrequest web --help
forgrequest diff --help
```
