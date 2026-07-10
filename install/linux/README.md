# Linux/macOS installation

From the project root:

```bash
chmod +x install/linux/install_linux.sh
./install/linux/install_linux.sh
```

Installed paths:

```text
Application: ~/.local/share/forgrequest
Config:      ~/.config/forgrequest/forgrequest.config
Command:     ~/.local/bin/forgrequest
```

The installer automatically adds the following line to common shell startup files when it is missing:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Open a new terminal after installation if your current shell does not immediately see the command.

Uninstall:

```bash
./install/linux/install_linux.sh --uninstall
```
