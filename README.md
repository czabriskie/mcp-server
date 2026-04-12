# MCP Server

An extensible [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server with weather and time tools. Built for learning — connect it to Claude Desktop and start chatting.

## Getting Started

### 1. Clone & Install

```bash
git clone <repo-url> && cd mcp-server
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux / WSL
pip install -e .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
git clone <repo-url> && cd mcp-server
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Connect to Claude Desktop

Run the setup script to automatically write the Claude Desktop config file:

**macOS:**

```bash
python setup_claude_agent.py
```

This writes `~/Library/Application Support/Claude/claude_desktop_config.json` pointing to your project's `.venv/bin/python`.

If your project is in a non-standard location, pass it explicitly:

```bash
python setup_claude_agent.py --project-path /path/to/mcp-server
```

**Windows (via WSL):**

```bash
python3 setup_claude_agent.py --windows --win-user <YourWindowsUser> --wsl-user <YourWSLUser>
```

For example:

```bash
python3 setup_claude_agent.py --windows --win-user Cam --wsl-user cam
```

This writes `%APPDATA%\Claude\claude_desktop_config.json` and configures Claude Desktop to launch the server through WSL.

### 3. Restart Claude Desktop

Close and reopen Claude Desktop. To verify the server is connected, go to **Settings → Developer** — you should see `mcp-server` with a green **running** badge.

### 4. Try It Out

Ask Claude any of the following:

- **"What time is it?"** — uses the `get_current_time` tool
- **"Get weather alerts for California"** — uses the `weather://alerts/CA` resource
- **"What's the forecast for latitude 40.7128, longitude -74.0060?"** — uses the forecast resource

You don't need to start the server manually — Claude Desktop launches it automatically.

---

## Available Tools & Resources

| Type | Name | What it does |
|------|------|-------------|
| Tool | `get_current_time` | Returns current time with automatic timezone detection |
| Resource | `weather://alerts/{state}` | Weather alerts for a US state (e.g. `CA`, `NY`) |
| Resource | `weather://forecast/{lat}/{lon}` | 5-period forecast for coordinates |
| Prompt | `analyze_weather_prompt` | Guides Claude through a full weather analysis |
| Prompt | `timezone_helper_prompt` | Helps with timezone checks, conversions, comparisons |

## Adding Your Own Tools

Open `src/mcp_server/server.py` and add a function with the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def my_tool(param: str) -> str:
    """Description of what this tool does."""
    return f"Result for {param}"
```

Restart Claude Desktop to pick up the change.

For resources and prompts, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Running Tests

```bash
pip install -e ".[dev]"   # or: uv pip install -e ".[dev]"
pytest
```

## Project Structure

```
src/mcp_server/
├── server.py              # MCP server entry point — register tools here
└── tools/
    ├── weather/           # Weather alerts & forecasts (NWS API)
    ├── time/              # IP-based timezone & current time
    └── conversation/      # Conversation tools
```

## License

MIT

## Resources

- [Model Context Protocol Docs](https://modelcontextprotocol.io)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- [Building an MCP Server](https://modelcontextprotocol.io/docs/develop/build-server)