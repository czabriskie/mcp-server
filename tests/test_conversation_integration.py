"""Integration tests for conversation logging with weather tools."""

import json
from unittest.mock import AsyncMock

import pytest

from mcp_server.tools.conversation import ConversationTools
from mcp_server.tools.weather import NWSAPIClient, WeatherTools


class TestConversationIntegration:
    """Integration tests for conversation logging and caching with MCP server."""

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock NWS API client."""
        return AsyncMock(spec=NWSAPIClient)

    @pytest.fixture
    def weather_tools(self, mock_api_client):
        """Create WeatherTools with mock API client."""
        return WeatherTools(api_client=mock_api_client)

    @pytest.fixture
    def conversation_tools(self):
        """Create ConversationTools instance."""
        return ConversationTools()

    # ========================================
    # Weather Tools with Caching Integration
    # ========================================

    @pytest.mark.asyncio
    async def test_alerts_caching_workflow(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test complete alerts workflow with caching.

        Arrange: Mock API to return alerts data
        Act: Fetch alerts, cache, fetch again
        Assert: Second fetch returns cached data without API call
        """
        # Arrange
        mock_api_client.get_alerts.return_value = {
            "features": [
                {
                    "properties": {
                        "event": "Fire Warning",
                        "headline": "Red Flag Warning",
                        "description": "High fire danger",
                    }
                }
            ]
        }

        # Act - First fetch
        cache_key = "alerts_CA"
        result1 = await weather_tools.get_alerts("CA")
        conversation_tools.cache_weather_data(cache_key, result1, "alerts")
        conversation_tools.log_message("system", "Fetched fresh alerts for CA")

        # Act - Check cache
        cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)

        # Assert
        assert cached is not None
        assert "Fire Warning" in cached
        assert mock_api_client.get_alerts.call_count == 1

        # Verify conversation log
        log = conversation_tools.get_conversation_log()
        parsed = json.loads(log)
        assert len(parsed) == 1
        assert "Fetched fresh alerts for CA" in parsed[0]["content"]

    @pytest.mark.asyncio
    async def test_forecast_caching_workflow(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test complete forecast workflow with caching.

        Arrange: Mock API to return forecast data
        Act: Fetch forecast, cache, retrieve from cache
        Assert: Cached forecast matches fetched data
        """
        # Arrange
        mock_api_client.get_forecast.return_value = {
            "properties": {
                "periods": [
                    {
                        "name": "Today",
                        "temperature": 75,
                        "temperatureUnit": "F",
                        "windSpeed": "5 mph",
                        "windDirection": "N",
                        "shortForecast": "Sunny",
                        "detailedForecast": "Clear skies",
                    }
                ]
            }
        }

        # Act - Fetch and cache
        cache_key = "forecast_37.77_-122.41"
        result = await weather_tools.get_forecast(37.77, -122.41)
        conversation_tools.cache_weather_data(cache_key, result, "forecast")
        conversation_tools.log_message("system", "Fetched fresh forecast for 37.77, -122.41")

        # Assert - Check cache
        cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=60)
        assert cached is not None
        assert "Clear skies" in cached
        assert "75°F" in cached

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_api_call(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test that cache miss results in API call.

        Arrange: Empty cache
        Act: Check cache (miss), fetch from API
        Assert: API called and data returned
        """
        # Arrange
        mock_api_client.get_alerts.return_value = {
            "features": [{"properties": {"event": "Flood Warning", "headline": "Flooding"}}]
        }

        # Act - Cache miss
        cache_key = "alerts_NY"
        cached = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
        assert cached is None

        # Act - Fetch from API
        result = await weather_tools.get_alerts("NY")
        conversation_tools.cache_weather_data(cache_key, result, "alerts")

        # Assert
        assert "Flood Warning" in result
        assert mock_api_client.get_alerts.call_count == 1

        # Verify now in cache
        cached_after = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
        assert cached_after is not None

    @pytest.mark.asyncio
    async def test_multiple_state_alerts_cached_separately(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test that alerts for different states are cached separately.

        Arrange: Mock API for multiple states
        Act: Fetch alerts for CA and NY
        Assert: Both cached separately
        """

        # Arrange
        def mock_get_alerts(state: str):
            if state == "CA":
                return {"features": [{"properties": {"event": "Fire Warning", "headline": "Fire"}}]}
            # NY
            return {"features": [{"properties": {"event": "Snow Warning", "headline": "Snow"}}]}

        mock_api_client.get_alerts.side_effect = mock_get_alerts

        # Act
        ca_result = await weather_tools.get_alerts("CA")
        conversation_tools.cache_weather_data("alerts_CA", ca_result, "alerts")

        ny_result = await weather_tools.get_alerts("NY")
        conversation_tools.cache_weather_data("alerts_NY", ny_result, "alerts")

        # Assert
        ca_cached = conversation_tools.get_cached_weather("alerts_CA")
        ny_cached = conversation_tools.get_cached_weather("alerts_NY")

        assert "Fire" in ca_cached
        assert "Snow" in ny_cached
        assert ca_cached != ny_cached

    @pytest.mark.asyncio
    async def test_cache_expiry_forces_refetch(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test that expired cache results in new API call.

        Arrange: Cache old data
        Act: Try to get with strict expiry
        Assert: Cache returns None, requiring fresh fetch
        """
        # Arrange - Cache some data
        mock_api_client.get_alerts.return_value = {
            "features": [
                {
                    "properties": {
                        "event": "Old Event",
                        "headline": "Old Headline",
                        "description": "Old description",
                        "instruction": "Old instruction",
                        "severity": "Minor",
                        "areaDesc": "Old Area",
                    }
                }
            ]
        }
        old_result = await weather_tools.get_alerts("CA")
        conversation_tools.cache_weather_data("alerts_CA", old_result, "alerts")

        # Manually expire the cache by setting max_age to 0
        cached = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=0)

        # Assert - Cache expired
        assert cached is None

        # Act - Fetch fresh
        mock_api_client.get_alerts.return_value = {
            "features": [
                {
                    "properties": {
                        "event": "New Event",
                        "headline": "New Headline",
                        "description": "New description",
                        "instruction": "New instruction",
                        "severity": "Severe",
                        "areaDesc": "New Area",
                    }
                }
            ]
        }
        new_result = await weather_tools.get_alerts("CA")

        # Assert - Got new data
        assert "New Event" in new_result
        assert "New Area" in new_result

    # ========================================
    # Conversation Logging Integration
    # ========================================

    def test_logging_throughout_fetch_lifecycle(self, conversation_tools):
        """Test logging at each stage of weather data lifecycle.

        Arrange: Create conversation tools
        Act: Log check cache, miss, fetch, cache
        Assert: All stages logged in order
        """
        conversation_tools.log_message("system", "Checking cache for alerts_CA")
        conversation_tools.log_message("system", "Cache miss - fetching fresh")
        conversation_tools.log_message("system", "Fetched fresh alerts for CA")
        conversation_tools.log_message("system", "Cached alerts_CA")

        log = conversation_tools.get_conversation_log()
        parsed = json.loads(log)

        assert len(parsed) == 4
        assert "Checking cache" in parsed[0]["content"]
        assert "Cache miss" in parsed[1]["content"]
        assert "Fetched fresh" in parsed[2]["content"]
        assert "Cached" in parsed[3]["content"]

    def test_get_all_cached_weather_shows_metadata(self, conversation_tools):
        """Test that cache summary shows useful metadata.

        Arrange: Cache multiple items
        Act: Get all cached weather
        Assert: Returns metadata for each item
        """
        conversation_tools.cache_weather_data("alerts_CA", "CA data", "alerts")
        conversation_tools.cache_weather_data("forecast_40.0_-74.0", "NY forecast", "forecast")

        result = conversation_tools.get_all_cached_weather()
        parsed = json.loads(result)

        # Should have 2 items
        assert len(parsed) == 2

        # Check each has required fields
        for item in parsed:
            assert "key" in item
            assert "type" in item
            assert "timestamp" in item
            assert "age_minutes" in item
            assert "data_preview" in item

        # Verify types
        types = [item["type"] for item in parsed]
        assert "alerts" in types
        assert "forecast" in types

    def test_clear_cache_logs_operation(self, conversation_tools):
        """Test clearing cache and logging the operation.

        Arrange: Cache some old data
        Act: Clear cache and log
        Assert: Cache cleared and logged
        """
        # Cache and expire
        conversation_tools.cache_weather_data("alerts_CA", "Old", "alerts")

        # Clear with zero expiry (clears all)
        removed = conversation_tools.clear_expired_cache(max_age_minutes=0)
        conversation_tools.log_message("system", f"Cleared {removed} expired entries")

        # Assert
        assert removed == 1
        log = conversation_tools.get_conversation_log()
        parsed = json.loads(log)
        assert "Cleared 1 expired entries" in parsed[0]["content"]

    # ========================================
    # End-to-End Scenarios
    # ========================================

    @pytest.mark.asyncio
    async def test_complete_user_session_workflow(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test complete user session with multiple requests and caching.

        Arrange: Mock API for multiple requests
        Act: User asks for weather multiple times
        Assert: Proper caching and logging throughout
        """
        # Setup mock
        mock_api_client.get_alerts.return_value = {
            "features": [
                {
                    "properties": {
                        "event": "Test Event",
                        "headline": "Test Alert",
                        "description": "Test description",
                        "instruction": "Test instruction",
                        "severity": "Moderate",
                        "areaDesc": "California",
                    }
                }
            ]
        }
        mock_api_client.get_forecast.return_value = {
            "properties": {
                "periods": [
                    {
                        "name": "Today",
                        "temperature": 70,
                        "temperatureUnit": "F",
                        "windSpeed": "10 mph",
                        "windDirection": "SW",
                        "shortForecast": "Sunny",
                        "detailedForecast": "Clear",
                    }
                ]
            }
        }

        # User's first request - CA alerts
        conversation_tools.log_message("user", "What are the alerts for California?")
        cache_key_alerts = "alerts_CA"
        cached_alerts = conversation_tools.get_cached_weather(cache_key_alerts, max_age_minutes=30)

        if not cached_alerts:
            alerts = await weather_tools.get_alerts("CA")
            conversation_tools.cache_weather_data(cache_key_alerts, alerts, "alerts")
            conversation_tools.log_message("system", "Fetched fresh alerts for CA")
        else:
            conversation_tools.log_message("system", "Returned cached alerts for CA")

        # User's second request - SF forecast
        conversation_tools.log_message("user", "What's the forecast for San Francisco?")
        cache_key_forecast = "forecast_37.77_-122.41"
        cached_forecast = conversation_tools.get_cached_weather(
            cache_key_forecast, max_age_minutes=60
        )

        if not cached_forecast:
            forecast = await weather_tools.get_forecast(37.77, -122.41)
            conversation_tools.cache_weather_data(cache_key_forecast, forecast, "forecast")
            conversation_tools.log_message("system", "Fetched fresh forecast for 37.77, -122.41")

        # User checks what's cached
        conversation_tools.log_message("user", "What weather data do you have cached?")
        all_cached = conversation_tools.get_all_cached_weather()
        parsed_cache = json.loads(all_cached)

        # Assertions
        assert len(parsed_cache) == 2
        assert any(item["key"] == "alerts_CA" for item in parsed_cache)
        assert any(item["key"] == "forecast_37.77_-122.41" for item in parsed_cache)

        # Check conversation log
        log = conversation_tools.get_conversation_log()
        parsed_log = json.loads(log)
        assert len(parsed_log) >= 3  # At least 3 user messages + system messages

        user_messages = [msg for msg in parsed_log if msg["role"] == "user"]
        assert len(user_messages) == 3

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_api_calls(
        self, weather_tools, conversation_tools, mock_api_client
    ):
        """Test that cache hits reduce API calls.

        Arrange: Mock API
        Act: Fetch same data twice
        Assert: API called once, second from cache
        """
        # Setup mock
        mock_api_client.get_alerts.return_value = {
            "features": [{"properties": {"event": "Test", "headline": "Alert"}}]
        }

        # First request - cache miss
        cache_key = "alerts_CA"
        cached_first = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
        assert cached_first is None

        result1 = await weather_tools.get_alerts("CA")
        conversation_tools.cache_weather_data(cache_key, result1, "alerts")
        conversation_tools.log_message("system", "Fetched fresh alerts for CA")

        # Second request - cache hit
        cached_second = conversation_tools.get_cached_weather(cache_key, max_age_minutes=30)
        assert cached_second is not None

        # Assert - API only called once
        assert mock_api_client.get_alerts.call_count == 1

        # Check logs show caching behavior
        log = conversation_tools.get_conversation_log()
        parsed = json.loads(log)
        assert len(parsed) == 1  # Only logged the fresh fetch, not the cache hit
