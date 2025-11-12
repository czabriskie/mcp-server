# Contributing to MCP Server

Thank you for your interest in contributing! This guide will help you add new tools, create custom MCP servers, and contribute to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Adding New Tools to the Weather Server](#adding-new-tools-to-the-weather-server)
- [Creating Your Own MCP Server](#creating-your-own-mcp-server)
- [Using Custom MCP Servers with the Web App](#using-custom-mcp-servers-with-the-web-app)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mcp-server.git
   cd mcp-server
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[all]"
   ```

## Project Structure Guidelines

### Module Organization

- `src/mcp_server/` - Core MCP server code
  - `server.py` - MCP server setup and tool registration
  - `tools/` - Organized tool modules
    - `weather/` - Weather tools module
      - `weather_tools.py` - Weather-related tools
      - `nws_client.py` - NWS API client
    - `time/` - Time/geolocation tools module
      - `time_tools.py` - IP-based time and location detection

- `tests/` - Test suite
  - Follow the same structure as `src/`
  - Use `test_*.py` naming convention

- `web_app/` - Optional testing interface (not for production)

### Code Style

We use `ruff` for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Hints

All code must include type hints:

```python
def get_alerts(self, state: str) -> Optional[dict[str, Any]]:
    """Get weather alerts for a state."""
    ...
```

Run type checking with:
```bash
mypy src/
```

## Testing Guidelines

### Test Structure

All tests follow the **Arrange-Act-Assert** pattern:

```python
@pytest.mark.asyncio
async def test_example(self):
    """Test description.

    Arrange: Setup description
    Act: Action description
    Assert: Expected result description
    """
    # Arrange
    mock_data = {"key": "value"}

    # Act
    result = await function_under_test(mock_data)

    # Assert
    assert result == expected_value
```

### Writing Tests

1. **Unit tests** - Test individual functions in isolation
2. **Use mocks** - Mock external dependencies (API calls, etc.)
3. **Test edge cases** - Error conditions, missing data, etc.
4. **Descriptive names** - Test names should explain what they test

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific tests
pytest tests/test_tools.py
pytest tests/test_tools.py::TestWeatherTools::test_get_alerts_success

# Watch mode (install pytest-watch)
ptw
```

### Coverage Requirements

- Aim for >90% code coverage
- All new features must include tests
- Tests must pass before merging

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following style guidelines
   - Add/update tests
   - Update documentation if needed

3. **Run quality checks**
   ```bash
   # Tests
   pytest

   # Linting
   ruff check src/ tests/

   # Type checking
   mypy src/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Requirements**
   - All tests pass
   - Code coverage maintained/improved
   - Documentation updated
   - No linting errors
   - Descriptive PR title and description

## Adding New Tools to the Weather Server

Want to add more weather-related functionality? Follow these steps:

### Step 1: Add API Method (if needed)

If you need new data from the National Weather Service API, add a method to `src/mcp_server/tools/weather/nws_client.py`:

```python
class NWSAPIClient:
    # ... existing methods ...

    async def get_radar_stations(self, state: str) -> Optional[dict[str, Any]]:
        """Get radar stations for a state."""
        url = f"{self.BASE_URL}/radar/stations?stateCode={state}"
        return await self._make_request(url)
```

### Step 2: Add Tool Implementation

Add your tool logic to `src/mcp_server/tools/weather/weather_tools.py`:

```python
class WeatherTools:
    # ... existing tools ...

    async def get_radar_stations(self, state: str) -> str:
        """Get radar stations for a US state.

        Args:
            state: Two-letter state code (e.g., 'CA', 'NY')

        Returns:
            Formatted list of radar stations
        """
        data = await self.api_client.get_radar_stations(state.upper())

        if not data or not data.get("features"):
            return f"No radar stations found for {state}"

        stations = []
        for feature in data["features"]:
            props = feature.get("properties", {})
            name = props.get("name", "Unknown")
            station_id = props.get("id", "Unknown")
            stations.append(f"- {name} ({station_id})")

        return f"Radar stations in {state}:\n" + "\n".join(stations)
```

### Step 3: Register the Tool

Register your tool in `src/mcp_server/server.py`:

```python
@mcp.tool()
async def get_radar_stations(state: str) -> str:
    """Get radar stations for a US state.

    Args:
        state: Two-letter US state code (e.g., 'CA', 'NY', 'TX')
    """
    return await weather_tools.get_radar_stations(state)
```

### Step 4: Add Tests

Create tests in `tests/test_tools.py` following the Arrange-Act-Assert pattern:

```python
class TestWeatherTools:
    # ... existing tests ...

    @pytest.mark.asyncio
    async def test_get_radar_stations_success(self, weather_tools, mock_api_client):
        """Test successful radar station retrieval."""
        # Arrange
        mock_api_client.get_radar_stations.return_value = {
            "features": [
                {
                    "properties": {
                        "id": "KMUX",
                        "name": "San Francisco"
                    }
                }
            ]
        }

        # Act
        result = await weather_tools.get_radar_stations("CA")

        # Assert
        assert "KMUX" in result
        assert "San Francisco" in result
        mock_api_client.get_radar_stations.assert_called_once_with("CA")
```

### Step 5: Verify

```bash
# Run tests
pytest tests/test_tools.py::TestWeatherTools::test_get_radar_stations_success -v

# Test the tool with the web app
cd web_app && python app.py
# Ask Claude: "Show me radar stations in California"
```

That's it! Your tool is now available to any MCP client.

## Creating Your Own MCP Server

Want to create a completely custom MCP server? Use this project as a template!

### Quick Start Template

1. **Create project structure**
   ```bash
   mkdir my-mcp-server
   cd my-mcp-server
   mkdir -p src/my_mcp_server tests
   ```

2. **Create `pyproject.toml`**
   ```toml
   [project]
   name = "my-mcp-server"
   version = "0.1.0"
   description = "My custom MCP server"
   requires-python = ">=3.10"
   dependencies = [
       "mcp>=0.1.0",
       # Add your dependencies here
   ]

   [project.optional-dependencies]
   dev = ["pytest>=7.0.0", "pytest-asyncio>=0.21.0"]

   [project.scripts]
   my-mcp-server = "my_mcp_server.server:main"
   ```

3. **Create your server** (`src/my_mcp_server/server.py`)
   ```python
   from mcp.server.fastmcp import FastMCP

   # Initialize FastMCP
   mcp = FastMCP("My MCP Server")

   @mcp.tool()
   async def my_tool(param: str) -> str:
       """Description of what your tool does.

       Args:
           param: Description of parameter
       """
       # Your tool logic here
       return f"Result for {param}"

   def main():
       """Run the MCP server."""
       mcp.run(transport='stdio')

   if __name__ == "__main__":
       main()
   ```

4. **Install and test**
   ```bash
   pip install -e .
   my-mcp-server  # Should start successfully
   ```

### Using Your Server with the Web App

The web app can connect to **any MCP server**! Configure it with environment variables:

```bash
# Set your server command
export MCP_SERVER_COMMAND="my-mcp-server"
export MCP_SERVER_ARGS=""

# Or use Python module
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,my_mcp_server.server"

# Or use Node.js
export MCP_SERVER_COMMAND="node"
export MCP_SERVER_ARGS="dist/server.js,--config,config.json"

# Start the web app
cd web_app && python app.py
```

The web app will automatically:
- ✅ Start your MCP server
- ✅ Connect via stdio
- ✅ Discover all tools
- ✅ Enable Claude to use your tools

### Examples of Custom Servers

#### Database MCP Server
```python
from mcp.server.fastmcp import FastMCP
import sqlite3

mcp = FastMCP("Database Tools")

@mcp.tool()
async def query_database(sql: str) -> str:
    """Execute SQL query.

    Args:
        sql: SQL query to execute
    """
    conn = sqlite3.connect("data.db")
    cursor = conn.execute(sql)
    results = cursor.fetchall()
    return str(results)
```

#### File System MCP Server
```python
from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("File System Tools")

@mcp.tool()
async def list_files(directory: str) -> str:
    """List files in directory.

    Args:
        directory: Path to directory
    """
    files = os.listdir(directory)
    return "\n".join(files)
```

#### API Integration MCP Server
```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("API Integration")

@mcp.tool()
async def fetch_data(endpoint: str) -> str:
    """Fetch data from API.

    Args:
        endpoint: API endpoint path
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/{endpoint}")
        return response.text
```

## Using Custom MCP Servers with the Web App

### Environment Variables

| Variable             | Description                      | Default                | Example                      |
| -------------------- | -------------------------------- | ---------------------- | ---------------------------- |
| `MCP_SERVER_COMMAND` | Command to run the MCP server    | `python`               | `node`, `npx`, `./my-server` |
| `MCP_SERVER_ARGS`    | Comma-separated server arguments | `-m,mcp_server.server` | `server.js,--port,3000`      |

### Configuration Examples

#### Using NPX with Filesystem Server
```bash
export MCP_SERVER_COMMAND="npx"
export MCP_SERVER_ARGS="-y,@modelcontextprotocol/server-filesystem,/tmp"
cd web_app && python app.py
```

#### Using Custom Python Package
```bash
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,my_company.mcp_server"
cd web_app && python app.py
```

#### Using Executable with Config
```bash
export MCP_SERVER_COMMAND="/usr/local/bin/my-mcp-server"
export MCP_SERVER_ARGS="--config,/etc/mcp/config.json,--verbose"
cd web_app && python app.py
```

### Testing Your Custom Server

1. **Start the web app with your server**
   ```bash
   export MCP_SERVER_COMMAND="your-server-command"
   export MCP_SERVER_ARGS="your,args"
   cd web_app && python app.py
   ```

2. **Open http://localhost:8000**

3. **Ask Claude to use your tools**
   - "What tools do you have available?"
   - Then use your specific tools in natural language

## Adding New Tools

To add a new weather tool:

1. **Add API method** in `tools/weather/nws_client.py`:
   ```python
   async def get_new_data(self, param: str) -> Optional[dict[str, Any]]:
       """Fetch new data from API."""
       url = f"{self.BASE_URL}/new/endpoint/{param}"
       return await self._make_request(url)
   ```

2. **Add tool method** in `tools/weather/weather_tools.py`:
   ```python
   async def get_new_tool(self, param: str) -> str:
       """Get new weather data.

       Args:
           param: Description

       Returns:
           Formatted result
       """
       data = await self.api_client.get_new_data(param)
       if not data:
           return "Unable to fetch data."
       return self._format_new_data(data)
   ```

3. **Register tool** in `server.py`:
   ```python
   @mcp.tool()
   async def get_new_tool(param: str) -> str:
       """Tool description for MCP clients."""
       return await weather_tools.get_new_tool(param)
   ```

4. **Add tests** in `tests/test_tools.py` and `tests/test_api_client.py`

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
