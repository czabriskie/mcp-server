"""Time and timezone tools for the MCP server."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx


class TimeTools:
    """Time-related tools that use IP geolocation to determine timezone."""

    def __init__(self) -> None:
        """Initialize time tools."""
        self.ipapi_base_url = "http://ip-api.com/json"
        self.ipinfo_base_url = "https://ipinfo.io"

    async def get_location_from_ip(self, ip_address: str | None = None) -> dict[str, Any]:
        """Get location information from IP address using ip-api.com.

        Args:
            ip_address: IP address to look up. If None, uses the caller's IP.

        Returns:
            Dictionary with timezone, lat, lon, city, region, country or defaults if lookup fails
        """
        # Skip localhost/private IPs - these won't work with geolocation
        if ip_address and (
            ip_address.startswith("127.")
            or ip_address.startswith("192.168.")
            or ip_address.startswith("10.")
            or ip_address.startswith("172.")
            or ip_address == "::1"
        ):
            ip_address = None  # Let the service detect the real public IP

        # Try ip-api.com first (free, no key needed)
        try:
            url = f"{self.ipapi_base_url}/{ip_address}" if ip_address else self.ipapi_base_url

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    lat = data.get("lat")
                    lon = data.get("lon")

                    # Only return if we got valid coordinates
                    if lat is not None and lon is not None:
                        return {
                            "timezone": data.get("timezone", "UTC"),
                            "lat": lat,
                            "lon": lon,
                            "city": data.get("city", "Unknown"),
                            "region": data.get("regionName", "Unknown"),
                            "country": data.get("country", "Unknown"),
                        }

        except Exception:
            # If first service fails, try ipinfo.io
            pass

        # Try ipinfo.io as fallback (free tier: 50k req/month)
        try:
            url = (
                f"{self.ipinfo_base_url}/{ip_address}/json"
                if ip_address
                else f"{self.ipinfo_base_url}/json"
            )

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # ipinfo.io returns "loc" as "lat,lon"
                if "loc" in data:
                    lat, lon = data["loc"].split(",")
                    return {
                        "timezone": data.get("timezone", "UTC"),
                        "lat": float(lat),
                        "lon": float(lon),
                        "city": data.get("city", "Unknown"),
                        "region": data.get("region", "Unknown"),
                        "country": data.get("country", "Unknown"),
                    }

        except Exception:
            # Both services failed
            pass

        return {
            "timezone": "UTC",
            "lat": None,
            "lon": None,
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
        }

    async def get_current_time(self, ip_address: str | None = None) -> str:
        """Get the current time based on the user's IP address.

        This tool determines the user's timezone from their IP address and returns
        the current local time in that timezone.

        Args:
            ip_address: Optional IP address to determine timezone. If not provided,
                       attempts to detect automatically or defaults to UTC.

        Returns:
            Formatted string with current time, timezone, and ISO timestamp
        """
        # Get location info from IP
        location = await self.get_location_from_ip(ip_address)
        timezone_str = location["timezone"]

        try:
            # Get current time in the detected timezone
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)

            # Format the response with multiple representations
            readable_time = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
            iso_time = now.isoformat()

            result = f"""Current Time Information:
Time: {readable_time}
Timezone: {timezone_str}
UTC Offset: {now.strftime("%z")}
ISO Format: {iso_time}
Day of Week: {now.strftime("%A")}
Date: {now.strftime("%B %d, %Y")}

Location (estimated from IP):
City: {location["city"]}, {location["region"]}, {location["country"]}"""

            if location["lat"] and location["lon"]:
                result += f"\nCoordinates: {location['lat']}, {location['lon']}"
                result += "\n\n✓ Location detected successfully! Use these coordinates for weather lookups."
            else:
                result += "\n\n⚠️ Could not determine precise location from IP address."
                result += "\nFor weather forecasts, please provide your city/state or coordinates manually."

            if ip_address:
                result = f"{result}\n(IP: {ip_address})"

            return result

        except Exception as e:
            # Fallback to UTC if timezone parsing fails
            now = datetime.now(ZoneInfo("UTC"))
            return f"""Current Time (UTC):
Time: {now.strftime("%A, %B %d, %Y at %I:%M:%S %p")} UTC
ISO Format: {now.isoformat()}
Note: Could not determine timezone from IP, showing UTC time.
Error: {e!s}"""
