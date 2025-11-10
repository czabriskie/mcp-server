# Contributing to MCP Weather Server

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mcp-weather-server.git
   cd mcp-weather-server
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

- `src/mcp_weather_server/` - Core MCP server code
  - `server.py` - MCP server setup and tool registration
  - `tools.py` - Business logic for weather tools
  - `api_client.py` - HTTP client for external APIs

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
pytest --cov=mcp_weather_server --cov-report=html

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

## Adding New Tools

To add a new weather tool:

1. **Add API method** in `api_client.py`:
   ```python
   async def get_new_data(self, param: str) -> Optional[dict[str, Any]]:
       """Fetch new data from API."""
       url = f"{self.BASE_URL}/new/endpoint/{param}"
       return await self._make_request(url)
   ```

2. **Add tool method** in `tools.py`:
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
