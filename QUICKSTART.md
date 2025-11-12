# Quick Start Guide

Get up and running with MCP Server in 5 minutes.

## Installation

```bash
# Clone or navigate to the project
cd mcp-server

# Install the package
pip install -e .
```

## Basic Usage

### 1. Run the MCP Server

```bash
mcp-server
```

The server will start and listen on stdio for MCP protocol messages.

### 2. Test with Python

```python
# test_server.py
import asyncio
from mcp_server.tools.weather_tools import WeatherTools
from mcp_server.tools.time_tools import TimeTools

async def main():
    # Test weather tools
    weather = WeatherTools()
    alerts = await weather.get_alerts("CA")
    print(alerts)

    forecast = await weather.get_forecast(37.7749, -122.4194)
    print(forecast)

    # Test time tools
    time_tools = TimeTools()
    time_info = await time_tools.get_current_time("8.8.8.8")
    print(time_info)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Connect from Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mcp-server": {
      "command": "python3",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "PYTHONPATH": "/Users/YOUR_USERNAME/Code/personal/mcp-server/src"
      }
    }
  }
}
```

**Important:** Replace `/Users/YOUR_USERNAME/Code/personal/mcp-server/src` with your actual project path.

Alternatively, if you've installed it in a virtual environment, use the venv's Python:

```json
{
  "mcpServers": {
    "mcp-server": {
      "command": "/Users/YOUR_USERNAME/Code/personal/mcp-server/.venv/bin/python3",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

Restart Claude Desktop and try:
> "What's the weather forecast for Seattle?"
> "What time is it in Tokyo?"

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=mcp_server
```

### Try the Web Interface (Optional)

```bash
# Install web dependencies
pip install -e ".[web]"

# Run web app
cd web_app
python app.py
```

Visit http://localhost:8000 to test interactively.

**Note:** You'll need AWS Bedrock configured. See [AWS_SETUP.md](AWS_SETUP.md) for details.

## Common Use Cases

### Get Current Time

```python
from mcp_server.tools.time_tools import TimeTools

tools = TimeTools()
time_info = await tools.get_current_time()  # Auto-detect from IP
time_info = await tools.get_current_time("8.8.8.8")  # Specific IP
```

### Get Weather Alerts

```python
from mcp_server.tools.weather_tools import WeatherTools

tools = WeatherTools()
alerts = await tools.get_alerts("TX")  # Texas alerts
```

### Get Forecast

```python
# New York City
forecast = await tools.get_forecast(40.7128, -74.0060)

# Los Angeles
forecast = await tools.get_forecast(34.0522, -118.2437)

# Chicago
forecast = await tools.get_forecast(41.8781, -87.6298)
```

### Use from Command Line

```bash
# Using Python
python -c "
import asyncio
from mcp_server.tools.weather_tools import WeatherTools

async def main():
    tools = WeatherTools()
    print(await tools.get_alerts('CA'))

asyncio.run(main())
"
```

## Project Structure

```
├── src/mcp_server/    # Main package
│   ├── server.py               # MCP server entry point
│   └── tools/                  # Tool modules
│       ├── weather_tools.py    # Weather tools logic
│       ├── time_tools.py       # Time/geolocation tools
│       └── api_client.py       # NWS API client
├── tests/                      # Test suite
├── web_app/                    # Optional web interface
└── pyproject.toml              # Project configuration
```

## Next Steps

- Read the [full README](README.md) for detailed documentation
- Check out [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- See [AWS_SETUP.md](AWS_SETUP.md) for web app configuration
- Browse the code in `src/mcp_server/` to understand the implementation

## Troubleshooting

### "Module not found" error

Make sure you installed the package:
```bash
pip install -e .
```

### "No active alerts" message

This is normal if there are no weather alerts in that state.

### Tests failing

Ensure you have dev dependencies:
```bash
pip install -e ".[dev]"
```

## Getting Help

- Open an issue on GitHub
- Check existing issues for solutions
- Read the documentation in the README
