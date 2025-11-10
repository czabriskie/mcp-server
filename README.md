# MCP Weather Server

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides weather data via the National Weather Service API.

## Project Structure

```
mcp-weather-server/
├── src/
│   └── mcp_weather_server/
│       ├── __init__.py
│       ├── server.py          # Main MCP server
│       ├── tools.py            # Weather tool implementations
│       └── api_client.py       # NWS API client
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py     # API client tests
│   └── test_tools.py           # Tool tests
├── web_app/                    # Optional web testing interface
│   ├── app.py                  # FastAPI web app
│   └── static/
│       └── index.html          # Chat UI
├── pyproject.toml
└── README.md
```

## Features

- ✅ **Production-ready architecture** - Modular, testable code structure
- 🌦️ **Weather tools** - Get forecasts and alerts from National Weather Service
- 🧪 **Comprehensive tests** - Unit tests with arrange/act/assert pattern
- 📦 **Proper packaging** - pip-installable with entry points
- 🔌 **MCP compliant** - Works with any MCP-compatible client

## Installation

### For MCP Server Only

```bash
pip install -e .
```

### For Development (includes tests)

```bash
pip install -e ".[dev]"
```

### For Web App Testing Interface

```bash
pip install -e ".[web]"
```

### Install Everything

```bash
pip install -e ".[all]"
```

## Usage

### Running the MCP Server

The MCP server is designed to be run as a standalone service and connected to via stdio:

```bash
# Using the installed entry point
mcp-weather-server

# Or directly with Python
python -m mcp_weather_server.server
```

### Connecting to the Server

The server uses stdio transport. Configure your MCP client (like Claude Desktop) to connect:

```json
{
  "mcpServers": {
    "weather": {
      "command": "mcp-weather-server"
    }
  }
}
```

Or if using from source:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["-m", "mcp_weather_server.server"]
    }
  }
}
```

### Available Tools

#### `get_alerts(state: str) -> str`

Get weather alerts for a US state.

**Parameters:**
- `state` (str): Two-letter US state code (e.g., "CA", "NY", "TX")

**Returns:** Formatted weather alerts or status message

**Example:**
```python
get_alerts("CA")  # Get alerts for California
```

#### `get_forecast(latitude: float, longitude: float) -> str`

Get detailed weather forecast for coordinates.

**Parameters:**
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate

**Returns:** 5-period weather forecast

**Example:**
```python
get_forecast(37.7749, -122.4194)  # San Francisco forecast
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_weather_server --cov-report=html

# Run specific test file
pytest tests/test_tools.py

# Run specific test
pytest tests/test_tools.py::TestWeatherTools::test_get_alerts_success
```

### Code Quality

```bash
# Format and lint
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/
```

### Project Structure Philosophy

This project separates concerns:

1. **MCP Server** (`src/mcp_weather_server/`) - The core server meant to be run independently
2. **Web App** (`web_app/`) - Optional testing interface, not meant for production hosting
3. **Tests** (`tests/`) - Comprehensive test coverage with arrange/act/assert pattern

The MCP server should be hosted/deployed separately and can serve multiple client applications.

## Web Testing Interface (Optional)

For interactive testing, a web app is provided but should **not** be used in production. The MCP server should run independently.

### Running the Web App

```bash
cd web_app
python app.py
```

Then visit http://localhost:8000

The web app includes:
- Chat interface with AWS Bedrock models
- MCP tool integration (when using Claude models)
- Model selection dropdown

**Note:** Claude models require filling out AWS Bedrock use case form. See [AWS_SETUP.md](AWS_SETUP.md) for details.

## Architecture

### MCP Server Architecture

```
┌─────────────────┐
│  MCP Client     │ (Claude Desktop, custom app, etc.)
│  (Your App)     │
└────────┬────────┘
         │ stdio
         ↓
┌─────────────────┐
│  MCP Server     │
│  (server.py)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────┐
│  Weather Tools  │ ───> │  NWS API     │
│  (tools.py)     │      │  Client      │
└─────────────────┘      └──────────────┘
```

### Modular Design

- **`api_client.py`**: HTTP client for NWS API
  - Handles all API communication
  - Error handling and retries
  - Type-safe responses

- **`tools.py`**: Business logic for weather tools
  - Data formatting
  - Tool implementations
  - Independent of MCP protocol

- **`server.py`**: MCP server setup
  - Tool registration
  - Protocol handling
  - Entry point

This separation allows:
- Easy testing of individual components
- Reusable API client
- Protocol-agnostic tool logic

## Testing Philosophy

All tests follow the **Arrange-Act-Assert** pattern:

```python
async def test_get_alerts_success(self, weather_tools, mock_api_client):
    """Test successful alert retrieval."""
    # Arrange: Set up test data and mocks
    mock_api_client.get_alerts.return_value = {
        "features": [...]
    }

    # Act: Execute the function being tested
    result = await weather_tools.get_alerts("CA")

    # Assert: Verify the results
    assert "Flood Warning" in result
    mock_api_client.get_alerts.assert_called_once_with("CA")
```

## API Reference

### NWSAPIClient

```python
from mcp_weather_server.api_client import NWSAPIClient

client = NWSAPIClient(timeout=30.0)
alerts = await client.get_alerts("CA")
forecast = await client.get_forecast(37.7749, -122.4194)
```

### WeatherTools

```python
from mcp_weather_server.tools import WeatherTools

tools = WeatherTools()
alerts_text = await tools.get_alerts("NY")
forecast_text = await tools.get_forecast(40.7128, -74.0060)
```

## Deployment

### As a System Service

The MCP server can be deployed as a system service and accessed by multiple applications:

1. Install on your server:
   ```bash
   pip install git+https://github.com/yourusername/mcp-weather-server.git
   ```

2. Create a systemd service (Linux) or launch daemon (macOS)

3. Connect multiple clients to the same server instance

### With Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["mcp-weather-server"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Ensure all tests pass: `pytest`
6. Submit a pull request

## License

MIT

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

Starting with the basics
https://modelcontextprotocol.io/docs/develop/build-server