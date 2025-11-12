"""Tests for weather tools."""

from unittest.mock import AsyncMock

import pytest

from mcp_server.tools.api_client import NWSAPIClient
from mcp_server.tools.weather_tools import WeatherTools


class TestWeatherTools:
    """Test suite for WeatherTools."""

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client.

        Returns:
            Mock NWSAPIClient
        """
        return AsyncMock(spec=NWSAPIClient)

    @pytest.fixture
    def weather_tools(self, mock_api_client):
        """Create WeatherTools instance with mock client.

        Args:
            mock_api_client: Mocked API client fixture

        Returns:
            WeatherTools instance
        """
        return WeatherTools(api_client=mock_api_client)

    def test_format_alert(self, weather_tools):
        """Test alert formatting.

        Arrange: Create sample alert feature
        Act: Format the alert
        Assert: Returns properly formatted string
        """
        # Arrange
        feature = {
            "properties": {
                "event": "Tornado Warning",
                "areaDesc": "Los Angeles County",
                "severity": "Severe",
                "description": "Tornado spotted",
                "instruction": "Take shelter immediately",
            }
        }

        # Act
        result = weather_tools.format_alert(feature)

        # Assert
        assert "Tornado Warning" in result
        assert "Los Angeles County" in result
        assert "Severe" in result
        assert "Tornado spotted" in result
        assert "Take shelter immediately" in result

    def test_format_alert_missing_fields(self, weather_tools):
        """Test alert formatting with missing fields.

        Arrange: Create alert feature with missing properties
        Act: Format the alert
        Assert: Uses default values for missing fields
        """
        # Arrange
        feature = {"properties": {}}

        # Act
        result = weather_tools.format_alert(feature)

        # Assert
        assert "Unknown" in result
        assert "No description available" in result
        assert "No specific instructions provided" in result

    @pytest.mark.asyncio
    async def test_get_alerts_success(self, weather_tools, mock_api_client):
        """Test successful alert retrieval.

        Arrange: Mock API client to return alert data
        Act: Call get_alerts()
        Assert: Returns formatted alerts
        """
        # Arrange
        mock_api_client.get_alerts.return_value = {
            "features": [
                {
                    "properties": {
                        "event": "Flood Warning",
                        "areaDesc": "Bay Area",
                        "severity": "Moderate",
                        "description": "Heavy rain expected",
                        "instruction": "Avoid low-lying areas",
                    }
                }
            ]
        }

        # Act
        result = await weather_tools.get_alerts("CA")

        # Assert
        assert "Flood Warning" in result
        assert "Bay Area" in result
        mock_api_client.get_alerts.assert_called_once_with("CA")

    @pytest.mark.asyncio
    async def test_get_alerts_no_data(self, weather_tools, mock_api_client):
        """Test alert retrieval with no data.

        Arrange: Mock API client to return None
        Act: Call get_alerts()
        Assert: Returns error message
        """
        # Arrange
        mock_api_client.get_alerts.return_value = None

        # Act
        result = await weather_tools.get_alerts("CA")

        # Assert
        assert "Unable to fetch alerts" in result

    @pytest.mark.asyncio
    async def test_get_alerts_no_active_alerts(self, weather_tools, mock_api_client):
        """Test alert retrieval with no active alerts.

        Arrange: Mock API client to return empty features
        Act: Call get_alerts()
        Assert: Returns no alerts message
        """
        # Arrange
        mock_api_client.get_alerts.return_value = {"features": []}

        # Act
        result = await weather_tools.get_alerts("CA")

        # Assert
        assert "No active alerts" in result

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, weather_tools, mock_api_client):
        """Test successful forecast retrieval.

        Arrange: Mock API client to return forecast data
        Act: Call get_forecast()
        Assert: Returns formatted forecast
        """
        # Arrange
        mock_api_client.get_forecast.return_value = {
            "properties": {
                "periods": [
                    {
                        "name": "Tonight",
                        "temperature": 45,
                        "temperatureUnit": "F",
                        "windSpeed": "10 mph",
                        "windDirection": "NW",
                        "detailedForecast": "Clear skies",
                    },
                    {
                        "name": "Tomorrow",
                        "temperature": 65,
                        "temperatureUnit": "F",
                        "windSpeed": "5 mph",
                        "windDirection": "N",
                        "detailedForecast": "Sunny",
                    },
                ]
            }
        }

        # Act
        result = await weather_tools.get_forecast(37.7749, -122.4194)

        # Assert
        assert "Tonight" in result
        assert "45°F" in result
        assert "Clear skies" in result
        assert "Tomorrow" in result
        mock_api_client.get_forecast.assert_called_once_with(37.7749, -122.4194)

    @pytest.mark.asyncio
    async def test_get_forecast_no_data(self, weather_tools, mock_api_client):
        """Test forecast retrieval with no data.

        Arrange: Mock API client to return None
        Act: Call get_forecast()
        Assert: Returns error message
        """
        # Arrange
        mock_api_client.get_forecast.return_value = None

        # Act
        result = await weather_tools.get_forecast(37.7749, -122.4194)

        # Assert
        assert "Unable to fetch forecast" in result

    @pytest.mark.asyncio
    async def test_get_forecast_invalid_data(self, weather_tools, mock_api_client):
        """Test forecast retrieval with invalid data structure.

        Arrange: Mock API client to return malformed data
        Act: Call get_forecast()
        Assert: Returns error message
        """
        # Arrange
        mock_api_client.get_forecast.return_value = {"invalid": "data"}

        # Act
        result = await weather_tools.get_forecast(37.7749, -122.4194)

        # Assert
        assert "Unable to parse forecast" in result

    @pytest.mark.asyncio
    async def test_get_forecast_limits_periods(self, weather_tools, mock_api_client):
        """Test that forecast limits to 5 periods.

        Arrange: Mock API client to return 10 periods
        Act: Call get_forecast()
        Assert: Result contains only 5 periods
        """
        # Arrange
        periods = [
            {
                "name": f"Period {i}",
                "temperature": 50 + i,
                "temperatureUnit": "F",
                "windSpeed": "10 mph",
                "windDirection": "N",
                "detailedForecast": f"Forecast {i}",
            }
            for i in range(10)
        ]
        mock_api_client.get_forecast.return_value = {"properties": {"periods": periods}}

        # Act
        result = await weather_tools.get_forecast(37.7749, -122.4194)

        # Assert
        assert "Period 0" in result
        assert "Period 4" in result
        assert "Period 5" not in result
        assert result.count("---") == 4  # 5 periods separated by 4 dividers
