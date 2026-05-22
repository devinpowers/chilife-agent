"""
OpenWeatherMap API → SQLite pipeline.

Fetches current conditions + 5-day forecast for Chicago,
cleans with pandas, stores in weather_observations.
Falls back gracefully if OWM_API_KEY not set.
"""
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

import requests
import pandas as pd

logger = logging.getLogger(__name__)

API_KEY  = os.getenv("OWM_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5"
LAT, LON = 41.8781, -87.6298   # Chicago

_CONDITION_MAP = {
    "Thunderstorm": "stormy",
    "Drizzle":      "rainy",
    "Rain":         "rainy",
    "Snow":         "snowy",
    "Mist":         "foggy",
    "Smoke":        "foggy",
    "Haze":         "foggy",
    "Dust":         "foggy",
    "Fog":          "foggy",
    "Sand":         "foggy",
    "Ash":          "foggy",
    "Squall":       "windy",
    "Tornado":      "stormy",
    "Clear":        "clear",
    "Clouds":       "cloudy",
}


def _k_to_f(k: float) -> float:
    return round((k - 273.15) * 9 / 5 + 32, 1)


def _mps_to_mph(mps: float) -> float:
    return round(mps * 2.237, 1)


def _fetch_current() -> Optional[Dict]:
    if not API_KEY:
        return None
    try:
        resp = requests.get(f"{BASE_URL}/weather", params={
            "lat": LAT, "lon": LON, "appid": API_KEY,
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("OWM current weather error: %s", exc)
        return None


def _fetch_forecast() -> Optional[Dict]:
    if not API_KEY:
        return None
    try:
        resp = requests.get(f"{BASE_URL}/forecast", params={
            "lat": LAT, "lon": LON, "appid": API_KEY, "cnt": 40,
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("OWM forecast error: %s", exc)
        return None


def _clean_current(raw: Dict) -> Dict:
    main     = raw.get("main", {})
    weather  = (raw.get("weather") or [{}])[0]
    wind     = raw.get("wind", {})
    now_iso  = datetime.now(timezone.utc).isoformat()
    cond     = weather.get("main", "Clear")
    return {
        "observed_at":  now_iso,
        "forecast_for": None,
        "temp_f":       _k_to_f(main.get("temp", 273.15)),
        "feels_like_f": _k_to_f(main.get("feels_like", 273.15)),
        "condition":    _CONDITION_MAP.get(cond, cond.lower()),
        "description":  weather.get("description", "").capitalize(),
        "humidity":     int(main.get("humidity", 0)),
        "wind_mph":     _mps_to_mph(wind.get("speed", 0)),
        "is_forecast":  0,
        "fetched_at":   now_iso,
    }


def _clean_forecast(raw: Dict) -> pd.DataFrame:
    items = raw.get("list", [])
    rows = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in items:
        main    = item.get("main", {})
        weather = (item.get("weather") or [{}])[0]
        wind    = item.get("wind", {})
        dt_txt  = item.get("dt_txt", "")            # "2025-05-24 12:00:00"
        cond    = weather.get("main", "Clear")
        rows.append({
            "observed_at":  now_iso,
            "forecast_for": dt_txt[:10],             # date portion only
            "temp_f":       _k_to_f(main.get("temp", 273.15)),
            "feels_like_f": _k_to_f(main.get("feels_like", 273.15)),
            "condition":    _CONDITION_MAP.get(cond, cond.lower()),
            "description":  weather.get("description", "").capitalize(),
            "humidity":     int(main.get("humidity", 0)),
            "wind_mph":     _mps_to_mph(wind.get("speed", 0)),
            "is_forecast":  1,
            "fetched_at":   now_iso,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # One row per day: take the noon observation if available, else first of day
    df["hour"] = pd.to_datetime(df["observed_at"]).dt.hour
    df = (
        df.sort_values(["forecast_for", "hour"])
          .drop_duplicates(subset=["forecast_for"], keep="first")
          .drop(columns=["hour"])
    )
    return df.reset_index(drop=True)


def fetch_and_clean() -> List[Dict]:
    """
    Returns list of weather row dicts ready for insert_weather().
    Index 0 is current conditions; rest are daily forecasts.
    Empty list if no API key.
    """
    if not API_KEY:
        logger.info("OWM_API_KEY not set — skipping weather fetch")
        return []

    results: List[Dict] = []

    current_raw = _fetch_current()
    if current_raw:
        results.append(_clean_current(current_raw))

    forecast_raw = _fetch_forecast()
    if forecast_raw:
        df = _clean_forecast(forecast_raw)
        results.extend(df.to_dict("records"))

    logger.info("OpenWeatherMap: %d weather rows fetched", len(results))
    return results
