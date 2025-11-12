# MCP Server - General Purpose Tools

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server with a **generic, extensible architecture**. Currently includes weather tools, but designed to easily add any type of tool.

**Key Features:**
- 🔧 **Generic Server Design** - Easy to add your own custom tools
- 🌦️ **Weather Tools** - Get forecasts and alerts from National Weather Service (example implementation)
- 🌐 **Universal Web Interface** - Works with **any MCP-compatible server**
- 🧪 **Comprehensive Tests** - Unit tests with arrange/act/assert pattern
- 📦 **Proper Packaging** - pip-installable with entry points
- 🔌 **MCP Compliant** - Works with Claude Desktop and other MCP clients

## Project Structure

```
mcp-server/
├── src/
│   └── mcp_server/
│       ├── __init__.py
│       ├── server.py          # Generic MCP server (add your tools here!)
│       └── tools/              # Organized tool modules
│           ├── __init__.py
│           ├── weather_tools.py   # Weather tool implementations (example)
│           ├── time_tools.py      # IP-based time/location detection
│           └── api_client.py      # NWS API client (example)
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py     # API client tests
│   ├── test_tools.py           # Weather tool tests
│   ├── test_time_tools.py      # Time tool tests
│   └── test_time_integration.py   # Integration tests
├── web_app/                    # Universal web testing interface
│   ├── app.py                  # FastAPI web app (works with ANY MCP server)
│   ├── README.md               # Web app configuration guide
│   └── static/
│       └── index.html          # Chat UI with model pricing
├── examples/                   # Example scripts and configurations
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md             # Guide to adding tools and creating servers
├── QUICKSTART.md               # Quick start guide
└── AWS_SETUP.md                # AWS Bedrock setup instructions
```

## Quick Start

### 1. Install

```bash
pip install -e ".[all]"  # Includes server, web app, and dev tools
```

### 2. Run the Server

```bash
mcp-server  # Starts the MCP server with stdio transport
```

### 3. Test with Web Interface

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"

# Start web app
cd web_app && python app.py
```

Visit http://localhost:8000 and ask: "Get weather alerts for California"

## Features

- 🌐 **Generic MCP Server** - Extensible architecture for any type of tools
- ⏰ **Time Tools** - IP-based timezone detection and current time
- 🌦️ **Weather Tools** - National Weather Service alerts and forecasts
- ☁️ **AWS Bedrock Integration** - Converse API with multiple Claude models
- 🤖 **Multiple Claude Models** - 6 models including inference profiles (Sonnet v2, Opus, Haiku 3.5)
- 💰 **Transparent Pricing** - Model costs displayed upfront ($0.25-$75 per 1M tokens)
- 🌍 **Multi-Region Support** - Configure AWS region via environment variables
- 🔄 **Automatic Retry Logic** - Handles throttling with adaptive retry (up to 10 attempts)
- 🔌 **Easy Extension** - Add custom tools in minutes with `@mcp.tool()` decorator
- 🖥️ **Web Interface** - FastAPI-based chat UI with model selection
- 🧪 **Comprehensive Tests** - 42 tests with 100% coverage

## Installation

### Install Core Server Only

```bash
pip install -e .
```

### Install with Web App

```bash
pip install -e ".[web]"
```

### Install Everything (Recommended)

```bash
pip install -e ".[all]"  # Includes dev tools and tests
```

```bash
pip install -e ".[all]"
```

## Usage

### Running the MCP Server

The MCP server is designed to be run as a standalone service and connected to via stdio:

```bash
# Using the installed entry point
mcp-server

# Or directly with Python
python -m mcp_server.server
```

### Connecting to the Server

The server uses stdio transport. Configure your MCP client (like Claude Desktop) to connect:

```json
{
  "mcpServers": {
    "weather": {
      "command": "mcp-server"
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
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

### Available Tools

The server currently includes two tool modules as examples. **You can easily add your own custom tools** - see [Adding Custom Tools](#adding-custom-tools) below.

#### Time Tools

##### `get_current_time(ip_address: Optional[str] = None) -> str`

Get the current time based on the user's IP address with automatic timezone detection.

**Parameters:**
- `ip_address` (str, optional): IP address to lookup. Auto-detected if not provided.

**Returns:** JSON string with current time, timezone, location, and coordinates

**Example:**
```python
get_current_time("8.8.8.8")  # Get time for specific IP
get_current_time()  # Auto-detect from request
```

#### Weather Tools

##### `get_alerts(state: str) -> str`

Get weather alerts for a US state.

**Parameters:**
- `state` (str): Two-letter US state code (e.g., "CA", "NY", "TX")

**Returns:** Formatted weather alerts or status message

**Example:**
```python
get_alerts("CA")  # Get alerts for California
```

##### `get_forecast(latitude: float, longitude: float) -> str`

Get detailed weather forecast for coordinates.

**Parameters:**
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate

**Returns:** 5-period weather forecast

**Example:**
```python
get_forecast(37.7749, -122.4194)  # San Francisco forecast
```

## Adding Custom Tools

The server is designed to be **generic and extensible**. Here's how to add your own tools:

### Quick Example

1. **Open** `src/mcp_server/server.py`

2. **Add your tool** in the designated section:

```python
# ========================================
# Add Your Custom Tools Here
# ========================================

@mcp.tool()
async def my_custom_tool(param: str) -> str:
    """Description of what your tool does.

    Args:
        param: Description of the parameter

    Returns:
        Description of the return value
    """
    # Your logic here
    result = f"Processed: {param}"
    return result
```

3. **Restart the server** - That's it! Your tool is now available.

### For Complex Tools

For more complex tools with external APIs or databases:

1. Create a new tool module (e.g., `src/mcp_server/tools/my_tools.py`)
2. Import and initialize it in `server.py`
3. Register your tool methods with `@mcp.tool()` decorators

**See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed examples including:**
- Database tools
- File system tools
- API integration tools
- Step-by-step guides with tests

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

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

1. **MCP Server** (`src/mcp_server/`) - The core server meant to be run independently
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

## Using Custom MCP Servers

The web app can connect to **any MCP-compatible server**, not just the weather server. Configure which server to use via environment variables:

### Configuration

```bash
# Use the default weather server (Python)
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,mcp_server.server"

# Use a Node.js MCP server
export MCP_SERVER_COMMAND="node"
export MCP_SERVER_ARGS="path/to/your-server.js"

# Use an MCP server with additional arguments
export MCP_SERVER_COMMAND="npx"
export MCP_SERVER_ARGS="-y,@modelcontextprotocol/server-filesystem,/tmp"

# Start the web app
cd web_app
python app.py
```

### Environment Variables

| Variable             | Description                       | Default                | Example                      |
| -------------------- | --------------------------------- | ---------------------- | ---------------------------- |
| `MCP_SERVER_COMMAND` | The command to run the MCP server | `python`               | `node`, `npx`, `./my-server` |
| `MCP_SERVER_ARGS`    | Comma-separated server arguments  | `-m,mcp_server.server` | `server.js,--port,3000`      |

### Examples

#### Using the Filesystem MCP Server

```bash
export MCP_SERVER_COMMAND="npx"
export MCP_SERVER_ARGS="-y,@modelcontextprotocol/server-filesystem,/Users/you/Documents"
cd web_app && python app.py
```

#### Using a Custom Python MCP Server

```bash
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,my_custom_mcp.server"
cd web_app && python app.py
```

#### Using an Executable MCP Server

```bash
export MCP_SERVER_COMMAND="/path/to/my-mcp-server"
export MCP_SERVER_ARGS="--config,config.json"
cd web_app && python app.py
```

The web app will automatically:
- Connect to your MCP server
- Discover available tools
- Enable Claude to use those tools in conversations

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

- **`tools/api_client.py`**: HTTP client for NWS API
  - Handles all API communication
  - Error handling and retries
  - Type-safe responses

- **`tools/weather_tools.py`**: Business logic for weather tools
  - Data formatting
  - Tool implementations
  - Independent of MCP protocol

- **`tools/time_tools.py`**: IP-based geolocation and time detection
  - Dual-service fallback (ip-api.com + ipinfo.io)
  - Timezone detection from coordinates
  - Localhost/private IP handling

- **`server.py`**: MCP server setup
  - Tool registration
  - Protocol handling
  - Entry point

This separation allows:
- Easy testing of individual components
- Reusable API clients
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
from mcp_server.tools.api_client import NWSAPIClient

client = NWSAPIClient(timeout=30.0)
alerts = await client.get_alerts("CA")
forecast = await client.get_forecast(37.7749, -122.4194)
```

### WeatherTools

```python
from mcp_server.tools.weather_tools import WeatherTools

tools = WeatherTools()
alerts_text = await tools.get_alerts("NY")
forecast_text = await tools.get_forecast(40.7128, -74.0060)
```

### TimeTools

```python
from mcp_server.tools.time_tools import TimeTools

tools = TimeTools()
time_info = await tools.get_current_time("8.8.8.8")  # Returns JSON with time, timezone, location
location = await tools.get_location_from_ip("8.8.8.8")  # Returns location dict
```

## Deployment

### As a System Service

The MCP server can be deployed as a system service and accessed by multiple applications:

1. Install on your server:
   ```bash
   pip install git+https://github.com/yourusername/mcp-server.git
   ```

2. Create a systemd service (Linux) or launch daemon (macOS)

3. Connect multiple clients to the same server instance

### With Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["mcp-server"]
```

## Contributing

We welcome contributions! Whether you want to:
- 🛠️ Add new weather tools to this server
- 🎨 Create your own custom MCP server
- 🐛 Fix bugs or improve documentation
- ✨ Suggest new features

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guides on:
- Adding new tools to the weather server
- Creating your own MCP server from scratch
- Using custom MCP servers with the web app
- Testing guidelines and best practices

### Quick Start

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