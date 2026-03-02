import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.weather_manager import WeatherSkill, _wmo_description, _WMO_DESCRIPTIONS

@pytest.fixture
def weather_skill():
    return WeatherSkill()

def test_weather_skill_properties(weather_skill):
    assert weather_skill.name == "get_weather"
    assert weather_skill.display_name == "🌦️ Previsão do Tempo"
    assert weather_skill.description == "Obtém a previsão do tempo atual para uma cidade."
    assert "city" in weather_skill.parameters["required"]

# ── Testes de _wmo_description ────────────────────────────────────────

def test_wmo_description_known_clear():
    """Código 0 → Céu limpo."""
    assert _wmo_description(0) == "Céu limpo"

def test_wmo_description_known_cloudy():
    """Código 2 → Parcialmente nublado (era o bug reportado: 'condição 2')."""
    assert _wmo_description(2) == "Parcialmente nublado"

def test_wmo_description_known_rain():
    """Código 61 → Chuva leve."""
    assert _wmo_description(61) == "Chuva leve"

def test_wmo_description_boundary_code_99():
    """Código 99 (máximo WMO) → Trovoada com granizo intenso."""
    assert _wmo_description(99) == "Trovoada com granizo intenso"

def test_wmo_description_unknown_negative():
    """Código desconhecido negativo → fallback com o número."""
    result = _wmo_description(-1)
    assert "desconhecida" in result
    assert "-1" in result

def test_wmo_description_unknown_large():
    """Código fora do padrão WMO → fallback com o número."""
    result = _wmo_description(999)
    assert "desconhecida" in result
    assert "999" in result

def test_wmo_descriptions_table_not_empty():
    """Tabela deve conter pelo menos os códigos básicos."""
    assert 0 in _WMO_DESCRIPTIONS   # Céu limpo
    assert 3 in _WMO_DESCRIPTIONS   # Nublado
    assert 63 in _WMO_DESCRIPTIONS  # Chuva moderada
    assert 95 in _WMO_DESCRIPTIONS  # Trovoada

def test_wmo_descriptions_all_values_are_strings():
    """Todos os valores da tabela devem ser strings não vazias."""
    for code, desc in _WMO_DESCRIPTIONS.items():
        assert isinstance(desc, str), f"Código {code} não é string"
        assert len(desc) > 0, f"Código {code} tem descrição vazia"

# ── Testes de integração do execute() ────────────────────────────────

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
            with pytest.raises(Exception):
                await weather_skill.get_coordinates("Invalid City", retries=2, backoff=0.01)
            
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
            with pytest.raises(Exception):
                await weather_skill.get_forecast(-23.5, -46.6, retries=2, backoff=0.01)
            
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

@pytest.mark.asyncio
async def test_execute_city_not_found(weather_skill):
    with patch.object(weather_skill, "get_coordinates", return_value=(None, None, None)):
        res = await weather_skill.execute({}, "Nowhere")
        assert res["status"] == "error"
        assert "não encontrada" in res["error"]

@pytest.mark.asyncio
async def test_execute_forecast_error(weather_skill):
    with patch.object(weather_skill, "get_coordinates", return_value=(-23.5, -46.6, "São Paulo")):
        with patch.object(weather_skill, "get_forecast", return_value=None):
            res = await weather_skill.execute({}, "São Paulo")
            assert res["status"] == "error"
            assert "Erro de formatação ou sem dados" in res["error"]

@pytest.mark.asyncio
async def test_execute_success_condition_is_readable_string(weather_skill):
    """Task 2.1 + 2.2: payload deve ter 'condition' (string legível) e NÃO 'condition_code'."""
    forecast_data = {
        "temperature_2m": 25.0,
        "relative_humidity_2m": 60,
        "precipitation_probability": 10,
        "weather_code": 2,  # "Parcialmente nublado"
    }
    with patch.object(weather_skill, "get_coordinates", return_value=(-23.5, -46.6, "São Paulo")):
        with patch.object(weather_skill, "get_forecast", return_value=forecast_data):
            res = await weather_skill.execute({}, "São Paulo")

            assert res["status"] == "success"
            data = res["data"]
            assert data["location"] == "São Paulo"
            assert data["temperature"] == 25.0
            assert data["rain_probability"] == 10

            # Bug fix: deve ser string legível, não número
            assert "condition" in data
            assert isinstance(data["condition"], str)
            assert data["condition"] == "Parcialmente nublado"

            # Bug fix: campo antigo NÃO deve estar presente
            assert "condition_code" not in data

@pytest.mark.asyncio
async def test_execute_success_unknown_weather_code(weather_skill):
    """Código WMO desconhecido deve resultar em fallback legível, não crash."""
    forecast_data = {
        "temperature_2m": 20.0,
        "relative_humidity_2m": 55,
        "precipitation_probability": 0,
        "weather_code": 42,  # não existe na tabela WMO padrão
    }
    with patch.object(weather_skill, "get_coordinates", return_value=(-15.0, -47.0, "Brasília")):
        with patch.object(weather_skill, "get_forecast", return_value=forecast_data):
            res = await weather_skill.execute({}, "Brasília")

            assert res["status"] == "success"
            assert "desconhecida" in res["data"]["condition"]
            assert "42" in res["data"]["condition"]

@pytest.mark.asyncio
async def test_execute_api_error(weather_skill):
    with patch.object(weather_skill, "get_coordinates", side_effect=Exception("API failed")):
        res = await weather_skill.execute({}, "São Paulo")
        assert res["status"] == "error"
        assert "Erro de comunicação com a API" in res["error"]


