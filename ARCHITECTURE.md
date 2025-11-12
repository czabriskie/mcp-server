# MCP Server Architecture

## Overview

This document explains the architecture and flow of the MCP (Model Context Protocol) server, from how tools are organized to how they're exposed to Claude Desktop.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Desktop                          │
│  (Sends MCP protocol messages via stdio)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ JSON-RPC over stdio
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   MCP Server (server.py)                     │
│  • FastMCP handles protocol                                  │
│  • Registers tools with @mcp.tool() decorators              │
│  • Routes requests to tool implementations                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Function calls
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼─────────┐              ┌────────▼────────┐
│  Weather Tools  │              │   Time Tools    │
│  (weather/)     │              │   (time/)       │
├─────────────────┤              ├─────────────────┤
│ weather_tools.py│              │ time_tools.py   │
│ nws_client.py   │              │                 │
└───────┬─────────┘              └────────┬────────┘
        │                                  │
        │ HTTP Requests                    │ HTTP Requests
        │                                  │
┌───────▼──────────────┐          ┌────────▼─────────────┐
│  National Weather    │          │  IP Geolocation APIs │
│  Service API         │          │  (ip-api, ipinfo.io) │
│  api.weather.gov     │          └──────────────────────┘
└──────────────────────┘
```

## Directory Structure

```
src/mcp_server/
├── server.py                    # Entry point - MCP server setup
└── tools/                       # Tool modules (organized by domain)
    ├── __init__.py             # Exports TimeTools and WeatherTools
    ├── weather/                # Weather forecasting module
    │   ├── __init__.py         # Exports WeatherTools, NWSAPIClient
    │   ├── weather_tools.py    # Weather tool implementations
    │   └── nws_client.py       # HTTP client for NWS API
    └── time/                   # Time/geolocation module
        ├── __init__.py         # Exports TimeTools
        └── time_tools.py       # IP-based time/location detection
```

## Component Flow

### 1. Server Initialization (`server.py`)

**Purpose**: Set up the MCP server and register all available tools.

```python
# server.py creates a FastMCP instance
mcp = FastMCP("general-tools")

# Initialize tool classes
weather_tools = WeatherTools()
time_tools = TimeTools()

# Register tools with decorators
@mcp.tool()
async def get_alerts(state: str) -> str:
    return await weather_tools.get_alerts(state)

@mcp.tool()
async def get_current_time(ip_address: str = "") -> str:
    ip = ip_address if ip_address else None
    return await time_tools.get_current_time(ip)
```

**Key Points**:
- FastMCP handles all MCP protocol details (JSON-RPC, stdio communication)
- Each `@mcp.tool()` decorator exposes a function to Claude Desktop
- Tool implementations are kept separate from protocol handling
- The `main()` function starts the server with `server.run(transport="stdio")`

### 2. Weather Tools Module (`tools/weather/`)

**Architecture**: Separation of concerns between API client and business logic.

#### `nws_client.py` - HTTP Client Layer
```python
class NWSAPIClient:
    """Handles all HTTP communication with National Weather Service API"""

    async def get_alerts(self, state: str) -> dict[str, Any] | None:
        # Makes HTTP request to NWS API
        # Returns raw JSON data or None on failure

    async def get_forecast(self, lat: float, lon: float) -> dict[str, Any] | None:
        # Two-step process:
        # 1. Get grid endpoint from /points/{lat},{lon}
        # 2. Fetch forecast from grid endpoint
```

**Responsibilities**:
- Construct API URLs
- Set required headers (User-Agent, Accept)
- Handle HTTP errors gracefully
- Return structured data (dict) or None

#### `weather_tools.py` - Business Logic Layer
```python
class WeatherTools:
    """Formats weather data for user consumption"""

    def __init__(self, api_client: NWSAPIClient | None = None):
        self.api_client = api_client or NWSAPIClient()

    async def get_alerts(self, state: str) -> str:
        # 1. Fetch data from API client
        # 2. Check for errors/empty data
        # 3. Format into human-readable strings
        # 4. Return formatted text
```

**Responsibilities**:
- Validate inputs
- Call API client methods
- Handle None responses (error cases)
- Format JSON data into readable text
- Return user-friendly strings

**Why Separate?**:
- **Testability**: Can mock API client to test formatting logic
- **Reusability**: API client can be used by other tools if needed
- **Maintainability**: API changes only affect one file
- **Single Responsibility**: Each class has one job

### 3. Time Tools Module (`tools/time/`)

**Architecture**: Self-contained module with dual-service fallback.

#### `time_tools.py` - Geolocation and Time Detection
```python
class TimeTools:
    """IP-based timezone and location detection"""

    async def get_location_from_ip(self, ip_address: str | None) -> dict[str, Any]:
        # 1. Skip localhost/private IPs
        # 2. Try ip-api.com first (free, no key)
        # 3. Fallback to ipinfo.io if first service fails
        # 4. Return location dict with timezone, lat, lon, city, etc.

    async def get_current_time(self, ip_address: str | None) -> str:
        # 1. Get location/timezone from IP
        # 2. Create ZoneInfo object for timezone
        # 3. Get current time in that timezone
        # 4. Format with multiple representations (readable, ISO, etc.)
        # 5. Include location info if available
```

**Key Features**:
- **Resilience**: Dual-service fallback ensures uptime
- **Smart Handling**: Detects localhost/private IPs and uses public IP instead
- **Rich Output**: Returns time in multiple formats (human-readable, ISO, day of week, etc.)
- **Location Context**: Includes estimated location from IP for better UX

**Why Self-Contained?**:
- No external APIs like NWS (uses public geolocation services)
- Simple enough to not need separation
- All HTTP logic is internal fallback handling

### 4. Request Flow Example

**User asks Claude**: "What's the weather forecast for Seattle?"

```
1. Claude Desktop
   └─> Sends MCP request: get_forecast(latitude=47.6062, longitude=-122.3321)

2. server.py
   └─> @mcp.tool() decorator receives request
   └─> Calls: weather_tools.get_forecast(47.6062, -122.3321)

3. weather_tools.py
   └─> Calls: self.api_client.get_forecast(47.6062, -122.3321)

4. nws_client.py
   └─> Step 1: GET https://api.weather.gov/points/47.6062,-122.3321
       └─> Returns: { "properties": { "forecast": "https://..." } }
   └─> Step 2: GET https://api.weather.gov/gridpoints/SEW/124,67/forecast
       └─> Returns: { "properties": { "periods": [...] } }

5. weather_tools.py
   └─> Receives forecast data
   └─> Formats first 5 periods into readable text
   └─> Returns formatted string

6. server.py
   └─> Returns result through FastMCP

7. Claude Desktop
   └─> Displays formatted forecast to user
```

## Design Principles

### 1. Modular Tool Organization

**Pattern**: Each tool category lives in its own subdirectory.

```
tools/
├── weather/    # Everything weather-related
├── time/       # Everything time-related
└── future/     # Easy to add new tools
```

**Benefits**:
- Clear ownership and boundaries
- Easy to find related code
- Simple to add new tool categories
- No naming conflicts

### 2. Separation of Concerns

**Layers**:
1. **Protocol Layer** (server.py): MCP protocol handling
2. **Tool Layer** (weather_tools.py, time_tools.py): Business logic and formatting
3. **Client Layer** (nws_client.py): External API communication

**Why**:
- Each layer can be tested independently
- Changes in one layer don't cascade
- Clear responsibilities reduce complexity

### 3. Dependency Injection

```python
class WeatherTools:
    def __init__(self, api_client: NWSAPIClient | None = None):
        self.api_client = api_client or NWSAPIClient()
```

**Benefits**:
- Easy to mock in tests
- Can swap implementations
- Flexible configuration

### 4. Type Safety

**All modules use type hints**:
```python
async def get_forecast(self, latitude: float, longitude: float) -> str:
    """Get weather forecast for coordinates."""
```

**Benefits**:
- Mypy catches errors before runtime
- Better IDE autocomplete
- Self-documenting code
- Easier refactoring

### 5. Error Handling

**Graceful degradation at every layer**:

```python
# Client layer returns None on failure
async def get_alerts(self, state: str) -> dict[str, Any] | None:
    try:
        response = await client.get(url)
        return response.json()
    except Exception:
        return None

# Tool layer handles None gracefully
async def get_alerts(self, state: str) -> str:
    data = await self.api_client.get_alerts(state)
    if not data:
        return "Unable to fetch alerts or no alerts found."
```

## Adding New Tools

### Example: Adding a "Stocks" Tool Module

**1. Create module structure**:
```
tools/stocks/
├── __init__.py
├── stocks_tools.py
└── market_client.py
```

**2. Implement client** (`market_client.py`):
```python
class MarketAPIClient:
    async def get_stock_price(self, symbol: str) -> dict[str, Any] | None:
        # HTTP logic here
        pass
```

**3. Implement tools** (`stocks_tools.py`):
```python
class StocksTools:
    def __init__(self, api_client: MarketAPIClient | None = None):
        self.api_client = api_client or MarketAPIClient()

    async def get_price(self, symbol: str) -> str:
        data = await self.api_client.get_stock_price(symbol)
        # Format data
        return formatted_price
```

**4. Export from module** (`__init__.py`):
```python
from .stocks_tools import StocksTools
__all__ = ["StocksTools"]
```

**5. Register in server** (`server.py`):
```python
from .tools.stocks import StocksTools

stocks_tools = StocksTools()

@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    return await stocks_tools.get_price(symbol)
```

**6. Write tests** (`tests/test_stocks.py`):
```python
from mcp_server.tools.stocks import StocksTools

async def test_get_price_success(mock_api_client):
    tools = StocksTools(api_client=mock_api_client)
    # Test logic
```

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Fast execution

```python
# Mock API client
mock_client = AsyncMock()
mock_client.get_alerts.return_value = {...}

# Test tool logic
tools = WeatherTools(api_client=mock_client)
result = await tools.get_alerts("CA")
assert "Fire Warning" in result
```

### Integration Tests
- Test multiple components together
- Use real datetime operations
- Verify end-to-end flows

```python
# Test actual time formatting with real timezone objects
tools = TimeTools()
result = await tools.get_current_time()
assert "Current Time Information:" in result
```

## CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/ci.yml`):

```yaml
jobs:
  test:        # Run pytest on Python 3.10, 3.11, 3.12, 3.13, 3.14
  lint:        # Run ruff check + format check
  type-check:  # Run mypy on src/
  security:    # Run bandit security scan
```

**All checks must pass** before merging to main.

## Key Takeaways

1. **MCP Protocol is Hidden**: FastMCP handles all protocol complexity
2. **Tools are Self-Contained**: Each module is independent and testable
3. **Layers are Separated**: Protocol → Tools → Clients
4. **Type Safety Throughout**: Mypy ensures correctness
5. **Easy to Extend**: Add new tools by following the pattern
6. **Comprehensive Testing**: 42 tests cover all functionality
7. **Automated Quality**: CI/CD enforces standards

## Questions to Ask When Adding Features

1. **Does this belong in an existing module or need a new one?**
   - Related to weather? → `tools/weather/`
   - New domain? → Create `tools/newdomain/`

2. **Does it need an API client?**
   - Yes → Separate client class (testability)
   - No → Keep in tool class

3. **What should it return?**
   - User-facing? → Return formatted string
   - Internal? → Return structured dict

4. **How do I test it?**
   - Mock external APIs
   - Test formatting logic separately
   - Add integration tests for complex flows

5. **What are the error cases?**
   - API down? → Return helpful message
   - Invalid input? → Validate and return error
   - Timeout? → Handle gracefully
