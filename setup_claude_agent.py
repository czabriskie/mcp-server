

import os
import sys
import json
from pathlib import Path
import argparse


def get_config_path(force_windows=False, win_user=None):
    if sys.platform == "darwin" and not force_windows:
        # macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"

    if force_windows:
        # Try to get Windows APPDATA from WSL
        win_appdata = os.getenv('WIN_APPDATA')
        if not win_appdata:
            try:
                import subprocess
                win_appdata = subprocess.check_output(['wslvar', 'APPDATA']).decode().strip()
            except Exception:
                win_appdata = None
        if not win_appdata:
            if win_user:
                win_home = f'/mnt/c/Users/{win_user}'
            else:
                win_home = os.getenv('WIN_HOME') or '/mnt/c/Users/' + os.getenv('USER', 'user')
            win_appdata = win_home + '/AppData/Roaming'
        return Path(win_appdata) / 'Claude' / 'claude_desktop_config.json'

    # Windows native
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise EnvironmentError("APPDATA environment variable not found on Windows.")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def get_mac_server_command(project_path=None):
    if not project_path:
        # Default: use the directory this script lives in
        project_path = str(Path(__file__).resolve().parent)
    venv_python = str(Path(project_path) / ".venv" / "bin" / "python")
    return {
        "command": venv_python,
        "args": ["-m", "mcp_server.server"],
    }


def get_wsl_server_command(wsl_user=None):
    if not wsl_user:
        wsl_user = os.getenv("USER", "user")
    wsl_project_path = f"/home/{wsl_user}/Code/mcp-server"
    venv_path = f"{wsl_project_path}/.venv"
    return {
        "command": "wsl",
        "args": [
            "bash", "-c",
            f'source {venv_path}/bin/activate && python3 -m mcp_server.server'
        ],
    }


def build_config(server_cmd):
    return {
        "mcpServers": {
            "mcp-server": {
                "command": server_cmd["command"],
                "args": server_cmd["args"],
                "env": {}
            }
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Setup Claude Desktop MCP agent config.")
    parser.add_argument('--windows', action='store_true', help='Write config to Windows APPDATA from WSL')
    parser.add_argument('--win-user', type=str, help='Specify Windows username for config path')
    parser.add_argument('--wsl-user', type=str, help='Specify WSL username for WSL path')
    parser.add_argument('--project-path', type=str, help='Path to the mcp-server project directory (macOS)')
    args = parser.parse_args()

    config_path = get_config_path(force_windows=args.windows, win_user=args.win_user)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if args.windows:
        print(f"Writing config for Claude Desktop (WSL→Windows). "
              f"Windows user: {args.win_user or os.getenv('USER')}, "
              f"WSL user: {args.wsl_user or os.getenv('USER')}")
        server_cmd = get_wsl_server_command(wsl_user=args.wsl_user)

    elif sys.platform == "darwin":
        project_path = args.project_path or str(Path(__file__).resolve().parent)
        venv_dir = Path(project_path) / ".venv"
        if not venv_dir.exists():
            print(f"Warning: No .venv found at {venv_dir}. "
                  "Run 'python3 -m venv .venv && source .venv/bin/activate && pip install -e .' first.")
        print(f"Detected macOS: configuring Claude Desktop with project at {project_path}")
        server_cmd = get_mac_server_command(project_path=project_path)

    elif sys.platform == "win32":
        print("Detected Windows: configuring Claude Desktop to use WSL.")
        print("Please run this script in your WSL shell to set up the Python venv.")
        server_cmd = get_wsl_server_command()

    else:
        # Linux / WSL default
        print("Detected Linux/WSL: configuring Claude Desktop to use WSL.")
        server_cmd = get_wsl_server_command(wsl_user=args.wsl_user)

    config = build_config(server_cmd)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config written to {config_path}")

if __name__ == "__main__":
    main()
