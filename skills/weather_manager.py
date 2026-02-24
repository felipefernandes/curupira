from .base import BaseSkill
import httpx
import logging
import asyncio
from typing import Any, Dict

class WeatherSkill(BaseSkill):
    def __init__(self):
        self.logger = logging.getLogger("WeatherSkill")
        self.geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def display_name(self) -> str:
        return "🌦️ Previsão do Tempo"

    @property
    def description(self) -> str:
        return "Obtém a previsão do tempo atual para uma cidade específica."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "O nome da cidade (ex: 'São Paulo', 'Rio de Janeiro')."
                }
            },
            "required": ["city"]
        }

    async def execute(self, context: Dict[str, Any], city: str) -> Dict[str, Any]:
        lat, lon, name = await self.get_coordinates(city)
        
        if not lat:
            return {"error": f"Cidade '{city}' não encontrada."}

        current = await self.get_forecast(lat, lon)
        if not current:
            return {"error": f"Erro ao obter dados meteorológicos para '{name}'."}

        # Return structured data for the LLM to process
        return {
            "location": name,
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "rain_probability": current.get("precipitation_probability", 0),
            "condition_code": current.get("weather_code")
        }

    async def get_coordinates(self, city_name, retries=3, backoff=2):
        """Fetches lat/lon for a city name with retry logic."""
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.geo_url, 
                        params={"name": city_name, "count": 1, "language": "pt", "format": "json"},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "results" in data and data["results"]:
                        place = data["results"][0]
                        return place["latitude"], place["longitude"], place["name"]
                    return None, None, None
            except Exception as e:
                self.logger.warning(f"Error fetching coordinates (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff * (attempt + 1))
        
        self.logger.error(f"Failed to fetch coordinates for {city_name} after {retries} attempts.")
        return None, None, None

    async def get_forecast(self, lat, lon, retries=3, backoff=2):
        """Fetches current weather for lat/lon with retry logic."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation_probability", "weather_code"],
            "timezone": "auto"
        }
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.weather_url, params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    return data.get("current", {})
            except Exception as e:
                self.logger.warning(f"Error fetching forecast (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff * (attempt + 1))
        
        self.logger.error(f"Failed to fetch forecast for lat:{lat}, lon:{lon} after {retries} attempts.")
        return None
