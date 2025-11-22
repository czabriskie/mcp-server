
import os
import sys
import json
from pathlib import Path
import argparse


def get_config_path(force_windows=False, win_user=None):
    if force_windows:
        # Try to get Windows APPDATA from WSL
        win_appdata = os.getenv('WIN_APPDATA')
        if not win_appdata:
            # Try to get via wslvar (WSL 2)
            try:
                import subprocess
                win_appdata = subprocess.check_output(['wslvar', 'APPDATA']).decode().strip()
            except Exception:
                win_appdata = None
        if not win_appdata:
            # Use provided Windows username or fallback to WSL user
            if win_user:
                win_home = f'/mnt/c/Users/{win_user}'
            else:
                win_home = os.getenv('WIN_HOME') or '/mnt/c/Users/' + os.getenv('USER', 'user')
            win_appdata = win_home + '/AppData/Roaming'
        return Path(win_appdata) / 'Claude' / 'claude_desktop_config.json'
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise EnvironmentError("APPDATA environment variable not found on Windows.")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        # Assume Linux/Unix
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_wsl_server_command(wsl_user=None):
    # Path to project in WSL (assume /home/<wsl_user>/Code/mcp-server)
    if not wsl_user:
        wsl_user = os.getenv("USER", "user")
    wsl_project_path = f"/home/{wsl_user}/Code/mcp-server"
    venv_path = f"{wsl_project_path}/.venv"
    # Activate venv and run server using module syntax
    return [
        "wsl",
        "bash",
        "-c",
        f'source {venv_path}/bin/activate && python3 -m mcp_server.server'
    ]

def get_server_command():
    if sys.platform == "win32":
        # Use WSL to run the server in Linux environment
        return get_wsl_server_command()
    else:
        return "python3"


def setup_venv_linux():
    venv_dir = Path(".venv")
    if not venv_dir.exists():
        print("Creating Python venv in .venv...")
        os.system("python3 -m venv .venv")
        print("Installing requirements...")
        os.system(".venv/bin/pip install -e .")
    else:
        print("Python venv already exists.")


def main():
    parser = argparse.ArgumentParser(description="Setup Claude Desktop MCP agent config.")
    parser.add_argument('--windows', action='store_true', help='Write config to Windows APPDATA from WSL')
    parser.add_argument('--win-user', type=str, help='Specify Windows username for config path')
    parser.add_argument('--wsl-user', type=str, help='Specify WSL username for WSL path')
    args = parser.parse_args()

    config_path = get_config_path(force_windows=args.windows, win_user=args.win_user)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if args.windows:
        print(f"Writing config to Windows APPDATA for Claude Desktop (from WSL) as Windows user: {args.win_user or os.getenv('USER')}, WSL user: {args.wsl_user or os.getenv('USER')}")
        server_cmd = get_wsl_server_command(wsl_user=args.wsl_user)
        config = {
            "mcpServers": {
                "mcp-server": {
                    "command": server_cmd[0],
                    "args": server_cmd[1:],
                    "env": {}
                }
            }
        }
    elif sys.platform == "win32":
        print("Detected Windows: configuring Claude Desktop to use WSL.")
        print("Please run this script in your WSL shell to set up the Python venv.")
        server_cmd = get_wsl_server_command()
        config = {
            "mcpServers": {
                "mcp-server": {
                    "command": server_cmd[0],
                    "args": server_cmd[1:],
                    "env": {}
                }
            }
        }
    else:
        print("Detected Unix/Mac: setting up venv and config.")
        setup_venv_linux()
        server_command = get_server_command()
        server_args = [str(Path(__file__).parent.parent / "src" / "mcp_server" / "server.py")]
        config = {
            "mcpServers": {
                "mcp-server": {
                    "command": server_command,
                    "args": server_args,
                    "env": {}
                }
            }
        }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config written to {config_path}")

if __name__ == "__main__":
    main()
