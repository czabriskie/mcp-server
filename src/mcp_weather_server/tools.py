"""Weather tools for the MCP server."""

from typing import Optional
from .api_client import NWSAPIClient


class WeatherTools:
    """Weather-related tools for the MCP server."""

    def __init__(self, api_client: Optional[NWSAPIClient] = None):
        """Initialize weather tools.

        Args:
            api_client: Optional NWS API client instance
        """
        self.api_client = api_client or NWSAPIClient()

    def format_alert(self, feature: dict) -> str:
        """Format an alert feature into a readable string.

        Args:
            feature: Alert feature from NWS API

        Returns:
            Formatted alert string
        """
        props = feature["properties"]
        return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

    async def get_alerts(self, state: str) -> str:
        """Get weather alerts for a US state.

        Args:
            state: Two-letter US state code (e.g. CA, NY)

        Returns:
            Formatted alert information or error message
        """
        data = await self.api_client.get_alerts(state)

        if not data or "features" not in data:
            return "Unable to fetch alerts or no alerts found."

        if not data["features"]:
            return "No active alerts for this state."

        alerts = [self.format_alert(feature) for feature in data["features"]]
        return "\n---\n".join(alerts)

    async def get_forecast(self, latitude: float, longitude: float) -> str:
        """Get weather forecast for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location

        Returns:
            Formatted forecast information or error message
        """
        forecast_data = await self.api_client.get_forecast(latitude, longitude)

        if not forecast_data:
            return "Unable to fetch forecast data for this location."

        try:
            periods = forecast_data["properties"]["periods"]
        except (KeyError, TypeError):
            return "Unable to parse forecast data."

        # Format the periods into a readable forecast
        forecasts = []
        for period in periods[:5]:  # Only show next 5 periods
            forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
            forecasts.append(forecast)

        return "\n---\n".join(forecasts)
