"""Tests for setup_claude_agent.py to verify Windows/WSL and macOS config generation."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import functions under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup_claude_agent import (
    get_config_path,
    get_mac_server_command,
    get_wsl_server_command,
    build_config,
    main,
)


# --- get_config_path ---

class TestGetConfigPathWindows:
    """Ensure Windows/WSL config path logic is preserved."""

    def test_force_windows_with_win_user(self):
        with patch.dict(os.environ, {}, clear=True):
            path = get_config_path(force_windows=True, win_user="StudentA")
        assert path == Path("/mnt/c/Users/StudentA/AppData/Roaming/Claude/claude_desktop_config.json")

    def test_force_windows_falls_back_to_USER_env(self):
        with patch.dict(os.environ, {"USER": "wslguy"}, clear=True):
            path = get_config_path(force_windows=True)
        assert path == Path("/mnt/c/Users/wslguy/AppData/Roaming/Claude/claude_desktop_config.json")

    def test_force_windows_uses_WIN_APPDATA_env(self):
        with patch.dict(os.environ, {"WIN_APPDATA": "C:/Users/Foo/AppData/Roaming"}, clear=True):
            path = get_config_path(force_windows=True)
        assert path == Path("C:/Users/Foo/AppData/Roaming/Claude/claude_desktop_config.json")

    def test_force_windows_uses_WIN_HOME_env(self):
        with patch.dict(os.environ, {"WIN_HOME": "/mnt/c/Users/Bar"}, clear=True):
            path = get_config_path(force_windows=True)
        assert path == Path("/mnt/c/Users/Bar/AppData/Roaming/Claude/claude_desktop_config.json")

    def test_native_windows_uses_APPDATA(self):
        with patch.dict(os.environ, {"APPDATA": r"C:\Users\Student\AppData\Roaming"}, clear=True), \
             patch("setup_claude_agent.sys") as mock_sys:
            mock_sys.platform = "win32"
            path = get_config_path(force_windows=False)
        assert path == Path(r"C:\Users\Student\AppData\Roaming") / "Claude" / "claude_desktop_config.json"

    def test_native_windows_raises_without_APPDATA(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("setup_claude_agent.sys") as mock_sys:
            mock_sys.platform = "win32"
            with pytest.raises(EnvironmentError, match="APPDATA"):
                get_config_path(force_windows=False)


class TestGetConfigPathMac:
    """Ensure macOS config path is correct."""

    def test_mac_config_path(self):
        with patch("setup_claude_agent.sys") as mock_sys:
            mock_sys.platform = "darwin"
            path = get_config_path(force_windows=False)
        expected = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        assert path == expected

    def test_mac_force_windows_overrides_platform(self):
        """Even on macOS, --windows flag should produce a WSL path."""
        with patch("setup_claude_agent.sys") as mock_sys:
            mock_sys.platform = "darwin"
            path = get_config_path(force_windows=True, win_user="WinStudent")
        assert "mnt/c/Users/WinStudent" in str(path)


# --- get_wsl_server_command ---

class TestGetWslServerCommand:
    """Verify WSL server command structure hasn't changed."""

    def test_default_wsl_user(self):
        with patch.dict(os.environ, {"USER": "testuser"}):
            cmd = get_wsl_server_command()
        assert cmd["command"] == "wsl"
        assert cmd["args"][0] == "bash"
        assert cmd["args"][1] == "-c"
        assert "/home/testuser/Code/mcp-server/.venv" in cmd["args"][2]
        assert "python3 -m mcp_server.server" in cmd["args"][2]

    def test_explicit_wsl_user(self):
        cmd = get_wsl_server_command(wsl_user="alice")
        assert "/home/alice/Code/mcp-server/.venv" in cmd["args"][2]

    def test_command_structure(self):
        cmd = get_wsl_server_command(wsl_user="u")
        assert "command" in cmd
        assert "args" in cmd
        assert isinstance(cmd["args"], list)


# --- get_mac_server_command ---

class TestGetMacServerCommand:
    """Verify macOS server command generation."""

    def test_with_explicit_project_path(self):
        cmd = get_mac_server_command(project_path="/Users/student/Code/mcp-server")
        assert cmd["command"] == "/Users/student/Code/mcp-server/.venv/bin/python"
        assert cmd["args"] == ["-m", "mcp_server.server"]

    def test_default_project_path_uses_script_dir(self):
        cmd = get_mac_server_command()
        # Should point to the repo root's .venv/bin/python
        assert cmd["command"].endswith(".venv/bin/python")
        assert cmd["args"] == ["-m", "mcp_server.server"]

    def test_command_structure(self):
        cmd = get_mac_server_command(project_path="/tmp/proj")
        assert "command" in cmd
        assert "args" in cmd
        assert isinstance(cmd["args"], list)


# --- build_config ---

class TestBuildConfig:
    """Verify the config dict structure is correct for both platforms."""

    def test_wsl_config_structure(self):
        cmd = get_wsl_server_command(wsl_user="student")
        config = build_config(cmd)
        server = config["mcpServers"]["mcp-server"]
        assert server["command"] == "wsl"
        assert server["args"][0] == "bash"
        assert server["env"] == {}

    def test_mac_config_structure(self):
        cmd = get_mac_server_command(project_path="/Users/s/proj")
        config = build_config(cmd)
        server = config["mcpServers"]["mcp-server"]
        assert server["command"] == "/Users/s/proj/.venv/bin/python"
        assert server["args"] == ["-m", "mcp_server.server"]
        assert server["env"] == {}

    def test_config_has_required_keys(self):
        cmd = {"command": "x", "args": ["y"]}
        config = build_config(cmd)
        assert "mcpServers" in config
        assert "mcp-server" in config["mcpServers"]
        srv = config["mcpServers"]["mcp-server"]
        assert set(srv.keys()) == {"command", "args", "env"}


# --- main (integration) ---

class TestMainIntegration:
    """Test main() writes valid JSON config for each platform."""

    def test_main_windows_flag(self, tmp_path):
        config_file = tmp_path / "Claude" / "claude_desktop_config.json"
        with patch("setup_claude_agent.get_config_path", return_value=config_file), \
             patch("sys.argv", ["setup_claude_agent.py", "--windows", "--wsl-user", "stu"]):
            main()
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        srv = config["mcpServers"]["mcp-server"]
        assert srv["command"] == "wsl"
        assert "stu" in srv["args"][2]

    def test_main_mac(self, tmp_path):
        config_file = tmp_path / "Claude" / "claude_desktop_config.json"
        with patch("setup_claude_agent.get_config_path", return_value=config_file), \
             patch("setup_claude_agent.sys") as mock_sys, \
             patch("sys.argv", ["setup_claude_agent.py", "--project-path", "/Users/s/proj"]):
            mock_sys.platform = "darwin"
            # Re-import main's arg parsing needs real sys.argv
            main()
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        srv = config["mcpServers"]["mcp-server"]
        assert srv["command"] == "/Users/s/proj/.venv/bin/python"

    def test_main_linux_fallback(self, tmp_path):
        config_file = tmp_path / "Claude" / "claude_desktop_config.json"
        with patch("setup_claude_agent.get_config_path", return_value=config_file), \
             patch("setup_claude_agent.sys") as mock_sys, \
             patch("sys.argv", ["setup_claude_agent.py", "--wsl-user", "lin"]):
            mock_sys.platform = "linux"
            main()
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        srv = config["mcpServers"]["mcp-server"]
        assert srv["command"] == "wsl"
        assert "lin" in srv["args"][2]

    def test_written_config_is_valid_json(self, tmp_path):
        config_file = tmp_path / "Claude" / "claude_desktop_config.json"
        with patch("setup_claude_agent.get_config_path", return_value=config_file), \
             patch("sys.argv", ["setup_claude_agent.py", "--windows"]):
            main()
        # Should not raise
        json.loads(config_file.read_text())
