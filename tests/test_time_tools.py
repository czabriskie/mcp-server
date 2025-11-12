"""Tests for time tools functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.tools.time_tools import TimeTools


class TestTimeTools:
    """Test suite for TimeTools class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.time_tools = TimeTools()

    @pytest.mark.asyncio
    async def test_get_location_from_ip_success_ipapi(self):
        """Test successful location lookup with ip-api.com."""
        # Arrange
        mock_response = {
            "status": "success",
            "lat": 37.7749,
            "lon": -122.4194,
            "city": "San Francisco",
            "regionName": "California",
            "country": "United States",
            "timezone": "America/Los_Angeles",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                json=MagicMock(return_value=mock_response), raise_for_status=MagicMock()
            )

            # Act
            result = await self.time_tools.get_location_from_ip("8.8.8.8")

            # Assert
            assert result["lat"] == 37.7749
            assert result["lon"] == -122.4194
            assert result["city"] == "San Francisco"
            assert result["region"] == "California"
            assert result["country"] == "United States"
            assert result["timezone"] == "America/Los_Angeles"

    @pytest.mark.asyncio
    async def test_get_location_from_ip_localhost(self):
        """Test that localhost IPs are skipped and auto-detection is used."""
        # Arrange
        mock_response = {
            "status": "success",
            "lat": 40.7128,
            "lon": -74.0060,
            "city": "New York",
            "regionName": "New York",
            "country": "United States",
            "timezone": "America/New_York",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                json=MagicMock(return_value=mock_response), raise_for_status=MagicMock()
            )

            # Act - test various localhost IPs
            for ip in ["127.0.0.1", "127.0.1.1", "192.168.1.1", "10.0.0.1", "172.16.0.1", "::1"]:
                result = await self.time_tools.get_location_from_ip(ip)

                # Assert - should get auto-detected location, not fail
                assert result["lat"] is not None
                assert result["lon"] is not None

    @pytest.mark.asyncio
    async def test_get_location_from_ip_fallback_to_ipinfo(self):
        """Test fallback to ipinfo.io when ip-api.com fails."""
        # Arrange
        mock_ipinfo_response = {
            "loc": "34.0522,-118.2437",
            "city": "Los Angeles",
            "region": "California",
            "country": "US",
            "timezone": "America/Los_Angeles",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            # First call (ip-api) fails, second call (ipinfo) succeeds
            mock_get.side_effect = [
                AsyncMock(side_effect=httpx.HTTPError("Connection failed")),
                AsyncMock(
                    json=MagicMock(return_value=mock_ipinfo_response), raise_for_status=MagicMock()
                ),
            ]

            # Act
            result = await self.time_tools.get_location_from_ip("8.8.8.8")

            # Assert
            assert result["lat"] == 34.0522
            assert result["lon"] == -118.2437
            assert result["city"] == "Los Angeles"
            assert result["region"] == "California"
            assert result["country"] == "US"

    @pytest.mark.asyncio
    async def test_get_location_from_ip_both_services_fail(self):
        """Test graceful fallback when both services fail."""
        # Arrange
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")

            # Act
            result = await self.time_tools.get_location_from_ip("8.8.8.8")

            # Assert - should return defaults
            assert result["timezone"] == "UTC"
            assert result["lat"] is None
            assert result["lon"] is None
            assert result["city"] == "Unknown"
            assert result["region"] == "Unknown"
            assert result["country"] == "Unknown"

    @pytest.mark.asyncio
    async def test_get_location_from_ip_invalid_coordinates(self):
        """Test handling of response with missing coordinates."""
        # Arrange
        mock_response = {
            "status": "success",
            "city": "Unknown",
            "regionName": "Unknown",
            "country": "Unknown",
            "timezone": "UTC",
            # No lat/lon provided
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = [
                AsyncMock(json=MagicMock(return_value=mock_response), raise_for_status=MagicMock()),
                AsyncMock(side_effect=httpx.HTTPError("Connection failed")),
            ]

            # Act
            result = await self.time_tools.get_location_from_ip("8.8.8.8")

            # Assert - should return defaults when coordinates missing
            assert result["lat"] is None
            assert result["lon"] is None

    @pytest.mark.asyncio
    async def test_get_current_time_with_valid_location(self):
        """Test get_current_time with successfully detected location."""
        # Arrange
        mock_location = {
            "timezone": "America/Los_Angeles",
            "lat": 37.7749,
            "lon": -122.4194,
            "city": "San Francisco",
            "region": "California",
            "country": "United States",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time("8.8.8.8")

            # Assert
            assert "Current Time Information:" in result
            assert "America/Los_Angeles" in result
            assert "San Francisco" in result
            assert "California" in result
            assert "37.7749, -122.4194" in result
            assert "✓ Location detected successfully!" in result
            assert "IP: 8.8.8.8" in result

    @pytest.mark.asyncio
    async def test_get_current_time_without_coordinates(self):
        """Test get_current_time when location detection fails."""
        # Arrange
        mock_location = {
            "timezone": "UTC",
            "lat": None,
            "lon": None,
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time("127.0.0.1")

            # Assert
            assert "Current Time Information:" in result
            assert "UTC" in result
            assert "⚠️ Could not determine precise location from IP address." in result
            assert "please provide your city/state or coordinates manually" in result

    @pytest.mark.asyncio
    async def test_get_current_time_timezone_components(self):
        """Test that all expected time components are present."""
        # Arrange
        mock_location = {
            "timezone": "America/New_York",
            "lat": 40.7128,
            "lon": -74.0060,
            "city": "New York",
            "region": "New York",
            "country": "United States",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert - check for all required components
            assert "Time:" in result
            assert "Timezone:" in result
            assert "UTC Offset:" in result
            assert "ISO Format:" in result
            assert "Day of Week:" in result
            assert "Date:" in result
            assert "Location (estimated from IP):" in result

    @pytest.mark.asyncio
    async def test_get_current_time_invalid_timezone_fallback(self):
        """Test fallback to UTC when timezone is invalid."""
        # Arrange
        mock_location = {
            "timezone": "Invalid/Timezone",
            "lat": 0,
            "lon": 0,
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert - should fall back to UTC
            assert "Current Time (UTC):" in result
            assert "Could not determine timezone from IP" in result

    @pytest.mark.asyncio
    async def test_get_current_time_no_ip_provided(self):
        """Test get_current_time with no IP address provided."""
        # Arrange
        mock_location = {
            "timezone": "America/Chicago",
            "lat": 41.8781,
            "lon": -87.6298,
            "city": "Chicago",
            "region": "Illinois",
            "country": "United States",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert - should not include IP in output
            assert "IP:" not in result
            assert "Chicago" in result

    def test_time_tools_initialization(self):
        """Test TimeTools initialization."""
        # Act
        tools = TimeTools()

        # Assert
        assert tools.ipapi_base_url == "http://ip-api.com/json"
        assert tools.ipinfo_base_url == "https://ipinfo.io"

    @pytest.mark.asyncio
    async def test_get_location_ipinfo_loc_parsing(self):
        """Test parsing of ipinfo.io 'loc' field."""
        # Arrange
        mock_ipinfo_response = {
            "loc": "51.5074,-0.1278",  # London coordinates
            "city": "London",
            "region": "England",
            "country": "GB",
            "timezone": "Europe/London",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = [
                AsyncMock(side_effect=httpx.HTTPError("First service failed")),
                AsyncMock(
                    json=MagicMock(return_value=mock_ipinfo_response), raise_for_status=MagicMock()
                ),
            ]

            # Act
            result = await self.time_tools.get_location_from_ip("8.8.4.4")

            # Assert
            assert result["lat"] == 51.5074
            assert result["lon"] == -0.1278
            assert result["city"] == "London"


class TestTimeToolsIntegration:
    """Integration tests for TimeTools with real datetime operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.time_tools = TimeTools()

    @pytest.mark.asyncio
    async def test_current_time_format_consistency(self):
        """Test that time format is consistent and parseable."""
        # Arrange
        mock_location = {
            "timezone": "America/Los_Angeles",
            "lat": 37.7749,
            "lon": -122.4194,
            "city": "San Francisco",
            "region": "California",
            "country": "United States",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert - check ISO format is present and valid
            assert "ISO Format:" in result
            iso_line = [line for line in result.split("\n") if "ISO Format:" in line][0]
            iso_str = iso_line.split("ISO Format:")[1].strip()

            # Should be able to parse the ISO timestamp
            parsed_dt = datetime.fromisoformat(iso_str)
            assert parsed_dt is not None

    @pytest.mark.asyncio
    async def test_timezone_offset_calculation(self):
        """Test that timezone offset is correctly calculated."""
        # Arrange
        mock_location = {
            "timezone": "America/New_York",
            "lat": 40.7128,
            "lon": -74.0060,
            "city": "New York",
            "region": "New York",
            "country": "United States",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert - offset should be present (format: -0500 or -0400 depending on DST)
            assert "UTC Offset:" in result
            offset_line = [line for line in result.split("\n") if "UTC Offset:" in line][0]
            offset = offset_line.split("UTC Offset:")[1].strip()

            # Should match format +/-HHMM
            assert len(offset) == 5
            assert offset[0] in ["+", "-"]
            assert offset[1:].isdigit()

    @pytest.mark.asyncio
    async def test_day_of_week_is_valid(self):
        """Test that day of week is a valid day name."""
        # Arrange
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        mock_location = {
            "timezone": "UTC",
            "lat": 0,
            "lon": 0,
            "city": "UTC",
            "region": "UTC",
            "country": "UTC",
        }

        with patch.object(self.time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await self.time_tools.get_current_time()

            # Assert
            assert "Day of Week:" in result
            day_line = [line for line in result.split("\n") if "Day of Week:" in line][0]
            day = day_line.split("Day of Week:")[1].strip()
            assert day in valid_days


# Fixtures for pytest
@pytest.fixture
def time_tools():
    """Provide a TimeTools instance for tests."""
    return TimeTools()


@pytest.fixture
def mock_successful_location():
    """Provide a mock successful location response."""
    return {
        "timezone": "America/Los_Angeles",
        "lat": 37.7749,
        "lon": -122.4194,
        "city": "San Francisco",
        "region": "California",
        "country": "United States",
    }


@pytest.fixture
def mock_failed_location():
    """Provide a mock failed location response."""
    return {
        "timezone": "UTC",
        "lat": None,
        "lon": None,
        "city": "Unknown",
        "region": "Unknown",
        "country": "Unknown",
    }
