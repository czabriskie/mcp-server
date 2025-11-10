# Quick Start Guide

Get up and running with MCP Weather Server in 5 minutes.

## Installation

```bash
# Clone or navigate to the project
cd mcp-weather-server

# Install the package
pip install -e .
```

## Basic Usage

### 1. Run the MCP Server

```bash
mcp-weather-server
```

The server will start and listen on stdio for MCP protocol messages.

### 2. Test with Python

```python
# test_server.py
import asyncio
from mcp_weather_server.tools import WeatherTools

async def main():
    tools = WeatherTools()

    # Get alerts for California
    alerts = await tools.get_alerts("CA")
    print(alerts)

    # Get forecast for San Francisco
    forecast = await tools.get_forecast(37.7749, -122.4194)
    print(forecast)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Connect from Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "weather": {
      "command": "mcp-weather-server"
    }
  }
}
```

Restart Claude Desktop and try:
> "What's the weather forecast for Seattle?"

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=mcp_weather_server
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

### Get Weather Alerts

```python
from mcp_weather_server.tools import WeatherTools

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
from mcp_weather_server.tools import WeatherTools

async def main():
    tools = WeatherTools()
    print(await tools.get_alerts('CA'))

asyncio.run(main())
"
```

## Project Structure

```
├── src/mcp_weather_server/    # Main package
│   ├── server.py               # MCP server entry point
│   ├── tools.py                # Weather tools logic
│   └── api_client.py           # NWS API client
├── tests/                      # Test suite
├── web_app/                    # Optional web interface
└── pyproject.toml              # Project configuration
```

## Next Steps

- Read the [full README](README.md) for detailed documentation
- Check out [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- See [AWS_SETUP.md](AWS_SETUP.md) for web app configuration
- Browse the code in `src/mcp_weather_server/` to understand the implementation

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
