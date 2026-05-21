"""
Weather service — returns mocked Chicago weather for the MVP.
In production this would call OpenWeatherMap or similar.
"""
import random
from datetime import datetime
from src.models.schemas import WeatherContext


# Realistic Chicago weather profiles by month
_SEASONAL_PROFILES = {
    # month -> list of possible conditions
    1:  [("cold", 18, 10), ("cold", 12, 2), ("cold", 5, -5)],
    2:  [("cold", 22, 14), ("cold", 15, 5), ("cold", 8, 0)],
    3:  [("cloudy", 38, 30), ("rainy", 40, 32), ("cold", 28, 18)],
    4:  [("rainy", 52, 46), ("cloudy", 55, 48), ("sunny", 60, 54)],
    5:  [("sunny", 68, 63), ("cloudy", 65, 58), ("rainy", 60, 55)],
    6:  [("sunny", 78, 74), ("sunny", 82, 77), ("warm", 75, 70)],
    7:  [("warm", 85, 82), ("sunny", 88, 84), ("sunny", 80, 76)],
    8:  [("warm", 84, 80), ("sunny", 82, 78), ("cloudy", 78, 74)],
    9:  [("sunny", 72, 67), ("cloudy", 68, 62), ("rainy", 65, 58)],
    10: [("cloudy", 55, 48), ("rainy", 50, 43), ("cold", 45, 38)],
    11: [("cold", 38, 30), ("rainy", 40, 33), ("cold", 32, 24)],
    12: [("cold", 28, 18), ("cold", 22, 12), ("cold", 18, 8)],
}

_RECOMMENDATIONS = {
    "sunny":  "Great night for a patio or outdoor event.",
    "warm":   "Warm evening — perfect for outdoor dining or a rooftop bar.",
    "cloudy": "Mild and overcast — ideal for a cozy indoor venue.",
    "rainy":  "Rainy out — stick to indoor spots and bring a jacket.",
    "cold":   "Bundle up. Great excuse to find a warm bar or restaurant.",
}


def get_weather(date_context: str = "tonight") -> WeatherContext:
    """
    Return a mocked WeatherContext appropriate for current month.
    date_context is accepted but not used in mock (always returns 'current' weather).
    """
    month = datetime.now().month
    profiles = _SEASONAL_PROFILES.get(month, _SEASONAL_PROFILES[6])
    condition, temp, feels = random.choice(profiles)

    return WeatherContext(
        condition=condition,
        temp_f=temp,
        feels_like_f=feels,
        recommendation=_RECOMMENDATIONS[condition],
    )
