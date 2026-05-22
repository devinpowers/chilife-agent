"""
Weather service — reads from weather_observations DB first,
falls back to seasonal mock if DB is empty (no API key set yet).
"""
import random
from datetime import datetime
from src.models.schemas import WeatherContext
from db import database as db

_RECOMMENDATIONS = {
    "clear":   "Beautiful night — perfect for a patio or rooftop.",
    "sunny":   "Great night for a patio or outdoor event.",
    "warm":    "Warm evening — perfect for outdoor dining or a rooftop bar.",
    "cloudy":  "Mild and overcast — ideal for a cozy indoor venue.",
    "rainy":   "Rainy out — stick to indoor spots and bring a jacket.",
    "stormy":  "Stormy weather — stay inside with a good drink.",
    "snowy":   "Snow on the ground — cozy bar weather.",
    "foggy":   "Foggy and moody — great night for a dimly lit cocktail bar.",
    "windy":   "Gusty out — probably better to stay indoors.",
    "cold":    "Bundle up. Great excuse to find a warm bar or restaurant.",
}

# Seasonal mock fallback (month → list of (condition, temp_f, feels_like_f))
_SEASONAL_PROFILES = {
    1:  [("cold", 18, 10), ("cold", 12, 2),  ("cold", 5, -5)],
    2:  [("cold", 22, 14), ("cold", 15, 5),  ("cold", 8, 0)],
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


def _mock_weather() -> WeatherContext:
    month = datetime.now().month
    profiles = _SEASONAL_PROFILES.get(month, _SEASONAL_PROFILES[6])
    condition, temp, feels = random.choice(profiles)
    return WeatherContext(
        condition=condition,
        temp_f=temp,
        feels_like_f=feels,
        recommendation=_RECOMMENDATIONS.get(condition, "Dress for the weather."),
    )


def get_weather(date_context: str = "tonight") -> WeatherContext:
    """Return current Chicago weather from DB, or mock if DB is empty."""
    try:
        row = db.get_current_weather()
        if row:
            condition = row.get("condition", "clear")
            return WeatherContext(
                condition=condition,
                temp_f=float(row.get("temp_f", 65)),
                feels_like_f=float(row.get("feels_like_f", 65)),
                recommendation=_RECOMMENDATIONS.get(condition, "Dress for the weather."),
            )
    except Exception:
        pass
    return _mock_weather()


def get_forecast() -> list:
    """Return next 5 days of forecast dicts from DB."""
    try:
        rows = db.get_weather_forecast(days=5)
        if rows:
            return rows
    except Exception:
        pass
    return []
