"""API client for National Weather Service."""

from typing import Any

import httpx


class NWSAPIClient:
    """Client for interacting with the National Weather Service API."""

    BASE_URL = "https://api.weather.gov"
    USER_AGENT = "mcp-weather-server/1.0"

    def __init__(self, timeout: float = 30.0):
        """Initialize the NWS API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {"User-Agent": self.USER_AGENT, "Accept": "application/geo+json"}

    async def get_alerts(self, state: str) -> dict[str, Any] | None:
        """Get weather alerts for a US state.

        Args:
            state: Two-letter US state code (e.g., CA, NY)

        Returns:
            API response data or None if request fails
        """
        url = f"{self.BASE_URL}/alerts/active/area/{state}"
        return await self._make_request(url)

    async def get_forecast(self, latitude: float, longitude: float) -> dict[str, Any] | None:
        """Get weather forecast for coordinates.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location

        Returns:
            API response data or None if request fails
        """
        # First get the forecast grid endpoint
        points_url = f"{self.BASE_URL}/points/{latitude},{longitude}"
        points_data = await self._make_request(points_url)

        if not points_data:
            return None

        # Get the forecast URL from the points response
        try:
            forecast_url = points_data["properties"]["forecast"]
            return await self._make_request(forecast_url)
        except (KeyError, TypeError):
            return None

    async def _make_request(self, url: str) -> dict[str, Any] | None:
        """Make an HTTP request to the NWS API.

        Args:
            url: Full URL to request

        Returns:
            JSON response data or None if request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data
            except (httpx.HTTPError, Exception):
                return None
