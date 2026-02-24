import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.weather_manager import WeatherSkill

@pytest.fixture
def weather_skill():
    return WeatherSkill()

def test_weather_skill_properties(weather_skill):
    assert weather_skill.name == "get_weather"
    assert weather_skill.display_name == "🌦️ Previsão do Tempo"
    assert weather_skill.description == "Obtém a previsão do tempo atual para uma cidade específica."
    assert "city" in weather_skill.parameters["required"]

@pytest.mark.asyncio
async def test_get_coordinates_empty_results(weather_skill):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": []
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        lat, lon, name = await weather_skill.get_coordinates("Nowhere", retries=1)
        
        assert lat is None
        assert lon is None
        assert name is None
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_get_coordinates_success(weather_skill):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"latitude": -23.5, "longitude": -46.6, "name": "São Paulo"}]
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        lat, lon, name = await weather_skill.get_coordinates("São Paulo", retries=1)
        
        assert lat == -23.5
        assert lon == -46.6
        assert name == "São Paulo"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_get_coordinates_retry_success(weather_skill):
    # Fails first time, succeeds second time
    mock_success = MagicMock()
    mock_success.json.return_value = {
        "results": [{"latitude": -23.5, "longitude": -46.6, "name": "São Paulo"}]
    }
    mock_success.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get") as mock_get:
        # First call raises an exception, second returns success
        mock_get.side_effect = [httpx.ReadTimeout("Timeout"), mock_success]
        
        # We also mock asyncio.sleep so the test runs fast
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            lat, lon, name = await weather_skill.get_coordinates("São Paulo", retries=2, backoff=0.01)
            
            assert lat == -23.5
            assert lon == -46.6
            assert name == "São Paulo"
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

@pytest.mark.asyncio
async def test_get_coordinates_total_failure(weather_skill):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection Error")
        
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            lat, lon, name = await weather_skill.get_coordinates("Invalid City", retries=2, backoff=0.01)
            
            assert lat is None
            assert lon is None
            assert name is None
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

@pytest.mark.asyncio
async def test_get_forecast_success(weather_skill):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "current": {"temperature_2m": 25.0, "relative_humidity_2m": 60, "weather_code": 3, "precipitation_probability": 10}
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        current = await weather_skill.get_forecast(-23.5, -46.6, retries=1)
        
        assert current["temperature_2m"] == 25.0
        assert current["relative_humidity_2m"] == 60
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_get_forecast_retry_success(weather_skill):
    mock_success = MagicMock()
    mock_success.json.return_value = {
        "current": {"temperature_2m": 25.0}
    }
    mock_success.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [httpx.ReadTimeout("Timeout"), mock_success]
        
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            current = await weather_skill.get_forecast(-23.5, -46.6, retries=2, backoff=0.01)
            
            assert current["temperature_2m"] == 25.0
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

@pytest.mark.asyncio
async def test_get_forecast_total_failure(weather_skill):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection Error")
        
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            current = await weather_skill.get_forecast(-23.5, -46.6, retries=2, backoff=0.01)
            
            assert current is None
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

@pytest.mark.asyncio
async def test_execute_city_not_found(weather_skill):
    with patch.object(weather_skill, "get_coordinates", return_value=(None, None, None)):
        res = await weather_skill.execute({}, "Nowhere")
        assert "error" in res
        assert "não encontrada" in res["error"]

@pytest.mark.asyncio
async def test_execute_forecast_error(weather_skill):
    with patch.object(weather_skill, "get_coordinates", return_value=(-23.5, -46.6, "São Paulo")):
        with patch.object(weather_skill, "get_forecast", return_value=None):
            res = await weather_skill.execute({}, "São Paulo")
            assert "error" in res
            assert "Erro ao obter dados" in res["error"]

@pytest.mark.asyncio
async def test_execute_success(weather_skill):
    with patch.object(weather_skill, "get_coordinates", return_value=(-23.5, -46.6, "São Paulo")):
        with patch.object(weather_skill, "get_forecast", return_value={"temperature_2m": 25.0, "precipitation_probability": 0}):
            res = await weather_skill.execute({}, "São Paulo")
            assert res["location"] == "São Paulo"
            assert res["temperature"] == 25.0
            assert res["rain_probability"] == 0
