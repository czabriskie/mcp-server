# MCP Server Architecture

## Overview

This document explains the architecture and flow of the MCP (Model Context Protocol) server, from how tools are organized to how they're exposed to Claude Desktop and the web app.

The server demonstrates all three MCP primitives:
- **Tools**: Actions and operations (e.g., get_current_time, get_forecast, clear_old_cache)
- **Resources**: Read-only, cacheable data accessed via URIs (e.g., conversation://log, weather://cache)
- **Prompts**: Guidance templates to help Claude use the server effectively

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
│  • Registers resources with @mcp.resource(uri) decorators   │
│  • Registers prompts with @mcp.prompt() decorators          │
│  • Routes requests to appropriate implementations            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Function calls
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼─────────┐              ┌────────▼────────┐
│  Weather Module │              │   Time Tools    │
│  (weather/)     │              │   (time/)       │
├─────────────────┤              ├─────────────────┤
│ Tools:          │              │ Tools:          │
│  • get_alerts   │              │  • current_time │
│  • get_forecast │              │                 │
│                 │              │                 │
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

        ┌────────────────────────────┐
        │   Conversation Module      │
        │   (conversation/)          │
        ├────────────────────────────┤
        │ Tools:                     │
        │  • clear_old_cache         │
        │                            │
        │ Resources:                 │
        │  • conversation://log      │
        │  • weather://cache         │
        │                            │
        │ conversation_tools.py      │
        │ • Logs all tool calls      │
        │ • Caches weather data      │
        │   (30min alerts, 60min     │
        │    forecasts)              │
        └────────────────────────────┘
```

## Directory Structure

```
src/mcp_server/
├── server.py                    # Entry point - MCP server setup
└── tools/                       # Tool modules (organized by domain)
    ├── __init__.py             # Exports TimeTools, WeatherTools, ConversationTools
    ├── conversation/           # Conversation logging and caching module
    │   ├── __init__.py         # Exports ConversationTools
    │   └── conversation_tools.py # Logging and caching implementations
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

**Purpose**: Set up the MCP server and register all available tools, resources, and prompts.

```python
# server.py creates a FastMCP instance
mcp = FastMCP("general-tools")

# Initialize tool classes
weather_tools = WeatherTools()
time_tools = TimeTools()
conversation_tools = ConversationTools()

# Register tools (actions/operations)
@mcp.tool()
async def get_current_time(ip_address: str = "") -> str:
    """Get current time with timezone detection."""
    ip = ip_address if ip_address else None
    result = await time_tools.get_current_time(ip)
    conversation_tools.log_message("system", f"Provided time for IP: {ip_address}")
    return result

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state (with caching)."""
    cache_key = f"alerts_{state}"
    cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
    if cached:
        conversation_tools.log_message("system", f"Returned cached alerts for {state}")
        return cached
    result = await weather_tools.get_alerts(state)
    conversation_tools.cache_weather_data(cache_key, result, "alerts")
    conversation_tools.log_message("system", f"Fetched fresh alerts for {state}")
    return result

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for coordinates (with caching)."""
    cache_key = f"forecast_{latitude}_{longitude}"
    cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=60)
    if cached:
        conversation_tools.log_message("system", f"Returned cached forecast for {latitude}, {longitude}")
        return cached
    result = await weather_tools.get_forecast(latitude, longitude)
    conversation_tools.cache_weather_data(cache_key, result, "forecast")
    conversation_tools.log_message("system", f"Fetched fresh forecast for {latitude}, {longitude}")
    return result

@mcp.tool()
async def clear_old_cache(max_age_minutes: int = 60) -> str:
    """Manually clear expired cache entries."""
    removed = conversation_tools.clear_expired_cache(max_age_minutes)
    return f"Cleared {removed} expired cache entries older than {max_age_minutes} minutes."

# Register resources (read-only data via URIs)
@mcp.resource("conversation://log")
async def get_conversation_log_resource() -> str:
    """Full conversation log resource."""
    return conversation_tools.get_conversation_log()

@mcp.resource("conversation://log/recent/{limit}")
async def get_recent_conversation_log_resource(limit: int) -> str:
    """Recent N messages from conversation log."""
    return conversation_tools.get_conversation_log(limit=limit)

@mcp.resource("weather://cache")
async def get_weather_cache_resource() -> str:
    """All cached weather data with timestamps and ages."""
    return conversation_tools.get_all_cached_weather()

# Register prompts (guidance templates)
@mcp.prompt(title="Weather Analysis")
def analyze_weather_prompt(location: str, coordinates: str = "") -> list[Message]:
    """Multi-step weather analysis guide."""
    # Returns structured messages to guide Claude
    pass

@mcp.prompt(title="Time Zone Helper")
def timezone_helper_prompt(action: str = "check") -> str:
    """Contextual timezone operation helper."""
    # Returns appropriate prompt based on action
    pass
```

**Key Points**:
- FastMCP handles all MCP protocol details (JSON-RPC, stdio communication)
- `@mcp.tool()` exposes actions/operations
- `@mcp.resource(uri)` exposes read-only data with URI patterns
- `@mcp.prompt()` provides guidance templates
- Tool implementations are kept separate from protocol handling
- The `main()` function starts the server with `mcp.run(transport="stdio")`

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

### 4. Conversation Tools Module (`tools/conversation/`)

**Architecture**: In-memory logging and caching system.

#### `conversation_tools.py` - Logging and Caching Layer
```python
class ConversationTools:
    """Manages conversation logging and weather data caching"""

    def __init__(self):
        self.conversation_log: list[dict[str, Any]] = []
        self.weather_cache: dict[str, dict[str, Any]] = {}

    def log_message(self, role: str, content: str) -> None:
        # Logs tool invocations with UTC timestamps
        pass

    def get_conversation_log(self, limit: int | None = None) -> str:
        # Returns JSON conversation history
        pass

    def cache_weather_data(self, key: str, data: str, type: str) -> None:
        # Stores weather data with timestamp
        pass

    def get_cached_weather(self, key: str, max_age_minutes: int = 60) -> str | None:
        # Returns cached data if fresh, None if expired
        pass

    def get_all_cached_weather(self) -> str:
        # Returns JSON cache summary with ages
        pass

    def clear_expired_cache(self, max_age_minutes: int) -> int:
        # Removes stale entries
        pass
```

**Key Features**:
- **Transparent Caching**: Weather tools wrapped with cache checks
- **Time-Based Expiration**: Different expiry times (30min alerts, 60min forecasts)
- **Conversation Logging**: All tool invocations logged with timestamps
- **Resource Inspection**: Cache and logs available as resources
- **UTC Timestamps**: Prevents timezone confusion

**Why Add Caching?**:
- **Reduce API Calls**: NWS API has rate limits
- **Improve Response Time**: Cached data returns instantly
- **Better UX**: Faster responses for repeated queries
- **Debugging**: Logs show what's being cached vs fresh

### 5. Request Flow Example

**User asks Claude**: "What's the weather forecast for Seattle?"

```
1. Claude Desktop or Web App
   └─> Calls tool: get_forecast(47.6062, -122.3321)

2. server.py
   └─> @mcp.tool() decorator receives request
   └─> Checks conversation_tools.get_cached_weather("forecast_47.6062_-122.3321", 60)

3. conversation_tools.py
   └─> Cache miss (no cached data or expired)
   └─> Returns None

4. server.py
   └─> Calls: weather_tools.get_forecast(47.6062, -122.3321)

5. weather_tools.py
   └─> Calls: self.api_client.get_forecast(47.6062, -122.3321)

6. nws_client.py
   └─> Step 1: GET https://api.weather.gov/points/47.6062,-122.3321
       └─> Returns: { "properties": { "forecast": "https://..." } }
   └─> Step 2: GET https://api.weather.gov/gridpoints/SEW/124,67/forecast
       └─> Returns: { "properties": { "periods": [...] } }

7. weather_tools.py
   └─> Receives forecast data
   └─> Formats first 5 periods into readable text
   └─> Returns formatted string

8. server.py
   └─> Caches result: conversation_tools.cache_weather_data("forecast_47.6062_-122.3321", result, "forecast")
   └─> Logs action: conversation_tools.log_message("system", "Fetched fresh forecast...")
   └─> Returns result through FastMCP

9. Claude Desktop or Web App
   └─> Displays formatted forecast to user

10. Second Request (within 60 minutes)
    └─> Cache hit! Returns cached data instantly without API calls
```

**Using Prompts Example**:

```
1. User: "Help me analyze the weather in Boston"

2. Claude Desktop
   └─> Invokes: analyze_weather_prompt("Boston", "42.3601,-71.0589")

3. server.py
   └─> Returns structured guidance:
       - "Analyze the weather for Boston"
       - "1. Call get_forecast(42.3601, -71.0589)"
       - "2. Call get_alerts('MA')"
       - "3. Provide summary with safety concerns"

4. Claude Desktop
   └─> Follows the guidance automatically
   └─> Calls get_forecast tool
   └─> Calls get_alerts tool
   └─> Synthesizes comprehensive analysis for user
```

**Using Resources Example**:

```
1. User: "Show me the conversation history"

2. Claude Desktop or Web App
   └─> Calls: read_resource("conversation://log")

3. server.py
   └─> @mcp.resource() decorator receives request
   └─> Calls: conversation_tools.get_conversation_log()

4. conversation_tools.py
   └─> Returns JSON with all logged messages and timestamps

5. Claude Desktop or Web App
   └─> Displays conversation history to user

Note: Web app uses a custom read_resource tool that calls session.read_resource()
```

## Design Principles

### 1. Using the Right MCP Primitive

**Pattern**: Choose the appropriate primitive for each use case.

- **Tools** (`@mcp.tool()`):
  - For actions that change state or perform operations
  - Examples: get_current_time, get_forecast, get_alerts, clear_old_cache
  - Not cacheable by client, executed every time
  - Weather tools include server-side caching to reduce API calls

- **Resources** (`@mcp.resource(uri)`):
  - For read-only data that can be accessed via URI
  - Identified by URI patterns
  - Examples: conversation://log, weather://cache
  - Claude Desktop can cache these
  - Web app uses read_resource tool to access

- **Prompts** (`@mcp.prompt()`):
  - For guidance templates
  - Help Claude use the server effectively
  - Examples: Multi-step analysis guides, operation helpers

**Benefits**:
- Semantic clarity (data vs actions)
- Server-side caching reduces API calls
- Client-side caching (Claude Desktop) improves performance
- Improved user experience
- Standardized access patterns
- Conversation logging for debugging

### 2. Server-Side Caching Pattern

**Pattern**: Wrap tool calls with transparent caching layer.

```python
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    # 1. Check cache
    cache_key = f"forecast_{latitude}_{longitude}"
    cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=60)

    # 2. Return cached if fresh
    if cached:
        conversation_tools.log_message("system", "Returned cached forecast")
        return cached

    # 3. Fetch fresh data
    result = await weather_tools.get_forecast(latitude, longitude)

    # 4. Cache and log
    conversation_tools.cache_weather_data(cache_key, result, "forecast")
    conversation_tools.log_message("system", "Fetched fresh forecast")

    return result
```

**Why Cache?**:
- **Reduce API Calls**: NWS API has rate limits
- **Faster Responses**: Cached data returns instantly
- **Cost Savings**: Fewer external API calls
- **Better UX**: Repeated queries are instant

**Expiry Times**:
- Alerts: 30 minutes (change frequently)
- Forecasts: 60 minutes (update less often)
- Custom: Use clear_old_cache tool

### 3. Modular Tool Organization

**Pattern**: Each tool category lives in its own subdirectory.

```
tools/
├── weather/       # Everything weather-related
├── time/          # Everything time-related
├── conversation/  # Logging and caching
└── future/        # Easy to add new tools
```

**Benefits**:
- Clear ownership and boundaries
- Easy to find related code
- Simple to add new tool categories
- No naming conflicts

### 3. Separation of Concerns

**Layers**:
1. **Protocol Layer** (server.py): MCP protocol handling (tools/resources/prompts)
2. **Caching Layer** (conversation_tools.py): Transparent caching and logging
3. **Tool Layer** (weather_tools.py, time_tools.py): Business logic and formatting
4. **Client Layer** (nws_client.py): External API communication

**Why**:
- Each layer can be tested independently
- Changes in one layer don't cascade
- Clear responsibilities reduce complexity

### 4. Dependency Injection

```python
class WeatherTools:
    def __init__(self, api_client: NWSAPIClient | None = None):
        self.api_client = api_client or NWSAPIClient()
```

**Benefits**:
- Easy to mock in tests
- Can swap implementations
- Flexible configuration

### 5. Type Safety

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

### 6. Error Handling

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

# As a resource (read-only data)
@mcp.resource("stocks://quote/{symbol}")
async def get_stock_quote_resource(symbol: str) -> str:
    """Stock quote resource (cacheable)."""
    return await stocks_tools.get_quote(symbol)

# Or as a tool (if it's an action)
@mcp.tool()
async def buy_stock(symbol: str, quantity: int) -> str:
    """Buy stock (this is an action)."""
    return await stocks_tools.buy(symbol, quantity)

# Optional: Add a prompt
@mcp.prompt(title="Stock Analysis")
def stock_analysis_prompt(symbol: str) -> str:
    """Guide for analyzing stocks."""
    return (
        f"Analyze {symbol}:\n"
        f"1. Read stocks://quote/{symbol}\n"
        "2. Check market trends\n"
        "3. Provide recommendation"
    )
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
2. **Three Primitives Available**: Tools (actions), Resources (data), Prompts (guidance)
3. **Use the Right Primitive**: Tools for actions, Resources for inspection, Prompts for help
4. **Server-Side Caching**: Weather tools include transparent caching to reduce API calls
5. **Conversation Logging**: All tool invocations logged with UTC timestamps
6. **Tools are Self-Contained**: Each module is independent and testable
7. **Layers are Separated**: Protocol → Caching → Tools → Clients
8. **Type Safety Throughout**: Mypy ensures correctness
9. **Easy to Extend**: Add new tools/resources/prompts by following the pattern
10. **Comprehensive Testing**: 76 tests cover all functionality including caching
11. **Automated Quality**: CI/CD enforces standards
12. **Flexible Clients**: Works with Claude Desktop (full MCP) and web app (tools + resources)

## Questions to Ask When Adding Features

1. **Which MCP primitive should I use?**
   - Performing an action? → Tool
   - Providing read-only data for inspection? → Resource
   - Guiding Claude through a workflow? → Prompt
   - Note: Weather endpoints are tools (with caching), not resources

2. **Does this belong in an existing module or need a new one?**
   - Related to weather? → `tools/weather/`
   - Related to caching/logging? → `tools/conversation/`
   - New domain? → Create `tools/newdomain/`

3. **Should this be cached?**
   - Frequently accessed data? → Add server-side caching
   - Data changes often? → Use shorter expiry time
   - Static data? → Consider making it a resource

4. **Does it need an API client?**
   - Yes → Separate client class (testability)
   - No → Keep in tool class

5. **What should it return?**
   - User-facing? → Return formatted string
   - Internal? → Return structured dict

6. **How do I test it?**
   - Mock external APIs
   - Test caching behavior separately
   - Test formatting logic separately
   - Add integration tests for complex flows

7. **What are the error cases?**
   - API down? → Return helpful message
   - Cache expired? → Fetch fresh data
   - Invalid input? → Validate and return error
   - Timeout? → Handle gracefully
