"""Tests for the National Weather Service API client."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.tools.api_client import NWSAPIClient


class TestNWSAPIClient:
    """Test suite for NWSAPIClient."""

    @pytest.fixture
    def client(self):
        """Create a test client instance.

        Returns:
            NWSAPIClient instance
        """
        return NWSAPIClient(timeout=10.0)

    @pytest.mark.asyncio
    async def test_get_alerts_success(self, client):
        """Test successful alerts retrieval.

        Arrange: Mock httpx response with alert data
        Act: Call get_alerts()
        Assert: Returns expected data structure
        """
        # Arrange
        mock_response_data = {
            "features": [{"properties": {"event": "Tornado Warning", "areaDesc": "Test Area"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()  # Regular Mock, not AsyncMock
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # Act
            result = await client.get_alerts("CA")

            # Assert
            assert result is not None
            assert "features" in result
            assert len(result["features"]) == 1
            assert result["features"][0]["properties"]["event"] == "Tornado Warning"

    @pytest.mark.asyncio
    async def test_get_alerts_failure(self, client):
        """Test alerts retrieval failure handling.

        Arrange: Mock httpx to raise an exception
        Act: Call get_alerts()
        Assert: Returns None
        """
        # Arrange
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Act
            result = await client.get_alerts("CA")

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, client):
        """Test successful forecast retrieval.

        Arrange: Mock httpx responses for points and forecast endpoints
        Act: Call get_forecast()
        Assert: Returns forecast data
        """
        # Arrange
        mock_points_data = {
            "properties": {"forecast": "https://api.weather.gov/gridpoints/MTR/85,105/forecast"}
        }
        mock_forecast_data = {
            "properties": {
                "periods": [{"name": "Tonight", "temperature": 45, "temperatureUnit": "F"}]
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response1 = Mock()  # Regular Mock, not AsyncMock
            mock_response1.json.return_value = mock_points_data
            mock_response1.raise_for_status = Mock()

            mock_response2 = Mock()  # Regular Mock, not AsyncMock
            mock_response2.json.return_value = mock_forecast_data
            mock_response2.raise_for_status = Mock()

            mock_client.get = AsyncMock(side_effect=[mock_response1, mock_response2])
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # Act
            result = await client.get_forecast(37.7749, -122.4194)

            # Assert
            assert result is not None
            assert "properties" in result
            assert "periods" in result["properties"]
            assert result["properties"]["periods"][0]["name"] == "Tonight"

    @pytest.mark.asyncio
    async def test_get_forecast_points_failure(self, client):
        """Test forecast retrieval when points endpoint fails.

        Arrange: Mock points endpoint to fail
        Act: Call get_forecast()
        Assert: Returns None
        """
        # Arrange
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Act
            result = await client.get_forecast(37.7749, -122.4194)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_forecast_missing_forecast_url(self, client):
        """Test forecast retrieval when forecast URL is missing.

        Arrange: Mock points response without forecast URL
        Act: Call get_forecast()
        Assert: Returns None
        """
        # Arrange
        mock_points_data = {"properties": {}}  # Missing forecast key

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_points_data
            mock_response.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Act
            result = await client.get_forecast(37.7749, -122.4194)

            # Assert
            assert result is None
