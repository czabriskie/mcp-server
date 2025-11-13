"""MCP Server - Main server implementation.

This server provides various tools, resources, and prompts via the Model Context Protocol (MCP).
Add your own tools by registering them in the create_server() function.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import Message, UserMessage

from .tools import ConversationTools, TimeTools, WeatherTools


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

    # Initialize tool modules
    weather_tools = WeatherTools()
    time_tools = TimeTools()
    conversation_tools = ConversationTools()

    # ========================================
    # Weather Tools
    # ========================================

    @mcp.tool()
    async def get_alerts(state: str) -> str:
        """Get active weather alerts for a US state.

        Provides current weather alerts and warnings for the specified state.
        Checks cache first (30 min expiry), fetches fresh if needed.

        Args:
            state: Two-letter US state code (e.g. CA, NY)
        """
        # Check cache first
        cache_key = f"alerts_{state.upper()}"
        cached: str | None = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
        if cached:
            conversation_tools.log_message("system", f"Returned cached alerts for {state}")
            return cached

        # Fetch fresh data
        result: str = await weather_tools.get_alerts(state)
        conversation_tools.cache_weather_data(cache_key, result, "alerts")
        conversation_tools.log_message("system", f"Fetched fresh alerts for {state}")
        return result

    @mcp.tool()
    async def get_forecast(latitude: float, longitude: float) -> str:
        """Get weather forecast for geographic coordinates.

        Provides a 5-day forecast for the specified location.
        Checks cache first (60 min expiry), fetches fresh if needed.

        Args:
            latitude: Latitude of the location (-90 to 90)
            longitude: Longitude of the location (-180 to 180)
        """
        # Check cache first
        cache_key = f"forecast_{latitude:.2f}_{longitude:.2f}"
        cached: str | None = conversation_tools.get_cached_weather(cache_key, max_age_minutes=60)
        if cached:
            conversation_tools.log_message(
                "system", f"Returned cached forecast for {latitude}, {longitude}"
            )
            return cached

        # Fetch fresh data
        result: str = await weather_tools.get_forecast(latitude, longitude)
        conversation_tools.cache_weather_data(cache_key, result, "forecast")
        conversation_tools.log_message(
            "system", f"Fetched fresh forecast for {latitude}, {longitude}"
        )
        return result

    # ========================================
    # Time Tools
    # ========================================

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
        result = await time_tools.get_current_time(ip)
        conversation_tools.log_message("system", f"Provided time for IP: {ip or 'auto'}")
        return result

    # ========================================
    # Conversation & Cache Resources
    # ========================================

    @mcp.resource("conversation://log")
    def get_conversation_log() -> str:
        """Conversation log resource.

        Returns the complete conversation log with timestamps.
        This is read-only data accessible via URI.
        """
        log: str = conversation_tools.get_conversation_log()
        return log

    @mcp.resource("conversation://log/recent/{limit}")
    def get_recent_conversation(limit: int) -> str:
        """Recent conversation log resource.

        Args:
            limit: Number of recent messages to return

        Returns:
            JSON formatted recent conversation log
        """
        log: str = conversation_tools.get_conversation_log(limit=limit)
        return log

    @mcp.resource("weather://cache")
    def get_weather_cache() -> str:
        """Weather cache resource.

        Returns all cached weather data with timestamps and age information.
        Shows what forecasts and alerts are available without re-fetching.
        """
        cache: str = conversation_tools.get_all_cached_weather()
        return cache

    @mcp.tool()
    def clear_old_cache(max_age_minutes: int = 60) -> str:
        """Clear expired weather cache entries.

        Args:
            max_age_minutes: Maximum age in minutes before considering expired

        Returns:
            Status message with number of entries removed
        """
        removed = conversation_tools.clear_expired_cache(max_age_minutes)
        return f"Cleared {removed} expired cache entries older than {max_age_minutes} minutes"

    # ========================================
    # Prompts (Help Claude use the server better)
    # ========================================

    @mcp.prompt(title="Weather Analysis")
    def analyze_weather_prompt(location: str, coordinates: str = "") -> list[Message]:
        """Generate a comprehensive weather analysis prompt.

        Args:
            location: City/state name (e.g., "Seattle, WA")
            coordinates: Optional "lat,lon" format (e.g., "47.6062,-122.3321")
        """
        messages: list[Message] = [
            UserMessage(f"Analyze the weather for {location}."),
        ]

        if coordinates:
            lat, lon = coordinates.split(",")
            messages.append(
                UserMessage(
                    f"1. Use get_forecast({lat.strip()}, {lon.strip()}) to check the forecast"
                )
            )
        else:
            messages.append(
                UserMessage(
                    "1. First, determine the coordinates for this location\n"
                    "2. Then use get_forecast(lat, lon) to check the forecast"
                )
            )

        messages.extend(
            [
                UserMessage("2. Use get_alerts(state) to check for any warnings"),
                UserMessage("3. Provide a summary with any safety concerns or recommendations"),
            ]
        )

        return messages

    @mcp.prompt(title="Time Zone Helper")
    def timezone_helper_prompt(action: str = "check") -> str:
        """Generate a prompt for working with timezones.

        Args:
            action: Type of timezone help needed (check, convert, compare)
        """
        if action == "convert":
            return (
                "Help me convert times between different timezones. "
                "Use get_current_time to determine timezone information."
            )
        if action == "compare":
            return (
                "Help me compare times across multiple locations. "
                "Use get_current_time for each location."
            )
        return (
            "Help me check what time it is in a specific location. "
            "Use get_current_time with an IP address or let it auto-detect."
        )

    # ========================================
    # Add Your Custom Tools/Resources/Prompts Here
    # ========================================
    # Use @mcp.tool() for actions, @mcp.resource() for data,
    # and @mcp.prompt() for guidance templates

    return mcp


def main() -> None:
    """Run the MCP server."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
