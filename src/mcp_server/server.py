"""MCP Server - Main server implementation.

This server provides various tools via the Model Context Protocol (MCP).
Add your own tools by registering them in the create_server() function.
"""

from mcp.server.fastmcp import FastMCP

from .tools import TimeTools, WeatherTools


def create_server(server_name: str = "general-tools") -> FastMCP:
    """Create and configure a generic MCP server.

    This function creates a FastMCP server and registers all available tools.
    To add new tools:
    1. Import your tool class
    2. Initialize it
    3. Register tool methods using @mcp.tool() decorators

    Args:
        server_name: Name for the MCP server (default: "general-tools")

    Returns:
        Configured FastMCP server instance with all tools registered
    """
    # Initialize server
    mcp = FastMCP(server_name)

    # ========================================
    # Weather Tools
    # ========================================
    weather_tools = WeatherTools()

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

    # ========================================
    # Time Tools
    # ========================================
    time_tools = TimeTools()

    @mcp.tool()
    async def get_current_time(ip_address: str = "") -> str:
        """Get the current time based on the user's IP address.

        This tool determines the user's timezone from their IP address using
        geolocation and returns the current local time in that timezone.

        Args:
            ip_address: Optional IP address to determine timezone. If not provided
                       or empty string, attempts to detect automatically or defaults to UTC.

        Returns:
            Formatted string with current time, timezone, day, and ISO timestamp
        """
        # Pass None to the tool if empty string to trigger auto-detection
        ip = ip_address if ip_address else None
        return await time_tools.get_current_time(ip)

    # ========================================
    # Add Your Custom Tools Here
    # ========================================
    # Example:
    # from .my_tools import MyTools
    # my_tools = MyTools()
    #
    # @mcp.tool()
    # async def my_custom_tool(param: str) -> str:
    #     """Description of what your tool does."""
    #     return await my_tools.my_method(param)

    return mcp


def main() -> None:
    """Run the MCP server."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
