"""MCP Weather Server - Main server implementation."""

from mcp.server.fastmcp import FastMCP
from .tools import WeatherTools


def create_server() -> FastMCP:
    """Create and configure the MCP weather server.

    Returns:
        Configured FastMCP server instance
    """
    # Initialize server
    mcp = FastMCP("weather")

    # Initialize tools
    weather_tools = WeatherTools()

    # Register tools
    @mcp.tool()
    async def get_alerts(state: str) -> str:
        """Get weather alerts for a US state.

        Args:
            state: Two-letter US state code (e.g. CA, NY)

        Returns:
            Weather alerts information
        """
        return await weather_tools.get_alerts(state)

    @mcp.tool()
    async def get_forecast(latitude: float, longitude: float) -> str:
        """Get weather forecast for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location

        Returns:
            Weather forecast information
        """
        return await weather_tools.get_forecast(latitude, longitude)

    return mcp


def main():
    """Run the MCP weather server."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
