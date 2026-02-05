import httpx
import logging

class WeatherManager:
    def __init__(self):
        self.logger = logging.getLogger("WeatherManager")
        self.geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"

    async def get_coordinates(self, city_name):
        """Fetches lat/lon for a city name."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.geo_url, params={"name": city_name, "count": 1, "language": "pt", "format": "json"})
                data = response.json()
                
                if "results" in data and data["results"]:
                    place = data["results"][0]
                    return place["latitude"], place["longitude"], place["name"]
                return None, None, None
        except Exception as e:
            self.logger.error(f"Error fetching coordinates: {e}")
            return None, None, None

    async def get_forecast(self, lat, lon):
        """Fetches current weather for lat/lon."""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": ["temperature_2m", "relative_humidity_2m", "precipitation_probability", "weather_code"],
                "timezone": "auto"
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self.weather_url, params=params)
                data = response.json()
                return data.get("current", {})
        except Exception as e:
            self.logger.error(f"Error fetching forecast: {e}")
            return None

    def _get_wmo_emoji(self, code):
        """Maps WMO weather codes to emojis."""
        if code is None: return "❓"
        if code == 0: return "☀️" # Clear sky
        if code in [1, 2, 3]: return "⛅" # Partly cloudy
        if code in [45, 48]: return "🌫️" # Fog
        if code in [51, 53, 55, 61, 63, 65]: return "🌧️" # Rain
        if code in [71, 73, 75]: return "❄️" # Snow
        if code in [95, 96, 99]: return "⛈️" # Thunderstorm
        return "🌡️" # Default

    async def get_weather_card(self, city_name):
        """Orchestrates the fetch and returns a formatted string."""
        lat, lon, name = await self.get_coordinates(city_name)
        
        if not lat:
            return f"\n⚠️ Não consegui encontrar a cidade **{city_name}**. Tente verificar o nome."

        current = await self.get_forecast(lat, lon)
        if not current:
            return f"\n⚠️ Erro ao obter dados do clima para **{name}**."

        temp = current.get("temperature_2m")
        prob_rain = current.get("precipitation_probability", 0)
        code = current.get("weather_code")
        emoji = self._get_wmo_emoji(code)

        card = (
            f"\n🌍 **Previsão para {name}:**\n"
            f"🌡️ **Agora**: {temp}°C {emoji}\n"
            f"☔ **Chuva**: {prob_rain}%\n"
        )
        return card
