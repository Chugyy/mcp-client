import random
from typing import Any

# Données des grandes villes
CITIES = {
    "paris": {"lat": 48.8566, "lon": 2.3522, "country": "France"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "country": "USA"},
    "london": {"lat": 51.5074, "lon": -0.1278, "country": "UK"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "Japan"},
    "sydney": {"lat": -33.8688, "lon": 151.2093, "country": "Australia"},
    "berlin": {"lat": 52.5200, "lon": 13.4050, "country": "Germany"},
    "rome": {"lat": 41.9028, "lon": 12.4964, "country": "Italy"},
    "madrid": {"lat": 40.4168, "lon": -3.7038, "country": "Spain"},
    "moscow": {"lat": 55.7558, "lon": 37.6173, "country": "Russia"},
    "beijing": {"lat": 39.9042, "lon": 116.4074, "country": "China"},
}

WEATHER_CONDITIONS = [
    "Sunny with clear skies",
    "Partly cloudy",
    "Cloudy with occasional sunshine",
    "Light rain expected",
    "Heavy rain showers",
    "Thunderstorms possible",
    "Foggy conditions",
    "Windy with gusts up to 40 km/h",
    "Snow expected",
    "Clear night skies",
]

ALERTS = [
    "Heat advisory in effect",
    "High wind warning",
    "Flood watch",
    "Winter storm warning",
    "Severe thunderstorm watch",
    "Air quality alert",
    "No active alerts",
]

async def get_alerts(city: str) -> str:
    """Get random weather alerts for a city.

    Args:
        city: City name (e.g. Paris, New York)
    """
    city_lower = city.lower()
    if city_lower not in CITIES:
        available = ", ".join(CITIES.keys())
        return f"City '{city}' not found. Available cities: {available}"

    city_data = CITIES[city_lower]
    alert = random.choice(ALERTS)

    return f"""
Weather Alert for {city.title()}, {city_data['country']}

Alert: {alert}
Severity: {random.choice(['Minor', 'Moderate', 'Severe'])}
Description: {alert} - Please stay informed and take necessary precautions.
Valid until: {random.randint(1, 48)} hours
"""

async def get_forecast(city: str) -> str:
    """Get random weather forecast for a city.

    Args:
        city: City name (e.g. Paris, New York)
    """
    city_lower = city.lower()
    if city_lower not in CITIES:
        available = ", ".join(CITIES.keys())
        return f"City '{city}' not found. Available cities: {available}"

    city_data = CITIES[city_lower]
    forecasts = []

    periods = ["Today", "Tonight", "Tomorrow", "Tomorrow Night", "Day After Tomorrow"]

    for period in periods:
        temp = random.randint(-10, 35)
        wind_speed = random.randint(5, 50)
        condition = random.choice(WEATHER_CONDITIONS)

        forecast = f"""
{period}:
Temperature: {temp}°C
Wind: {wind_speed} km/h {random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])}
Humidity: {random.randint(30, 95)}%
Forecast: {condition}
Location: {city.title()}, {city_data['country']} (Lat: {city_data['lat']}, Lon: {city_data['lon']})
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)
