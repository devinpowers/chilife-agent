"""
Places service — loads and filters mock Chicago venues/restaurants.
"""
import json
from pathlib import Path
from typing import List

from src.models.schemas import PlaceResult, UserRequest, WeatherContext

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_places.json"

# Map user-facing interest strings to place categories/tags
_INTEREST_CATEGORY_MAP = {
    "coffee": ["coffee"],
    "bars": ["bar"],
    "restaurants": ["restaurant"],
    "museums": ["museum"],
    "live_music": ["bar", "restaurant"],   # places with music ambiance
    "comedy": ["bar"],
    "sports": ["bar"],
}

_FOOD_TAG_MAP = {
    "mexican": ["tacos", "mexican"],
    "japanese": ["ramen", "japanese"],
    "italian": ["italian", "pizza"],
    "vegetarian": ["vegetarian-friendly", "seasonal"],
    "burgers": ["burgers"],
    "seafood": ["oysters", "seafood"],
}


def _load_places() -> List[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


def _normalize_day(date_context: str) -> str:
    dc = date_context.lower()
    if "saturday" in dc:
        return "saturday"
    if "sunday" in dc:
        return "sunday"
    return "friday"


def _is_open(place: dict, day: str) -> bool:
    hours = place.get("hours", {})
    return day in hours


def _group_matches(place: dict, group_context: str) -> bool:
    gc = group_context.lower()
    if gc == "solo":
        return place.get("solo_friendly", True)
    if gc == "date":
        return place.get("date_friendly", True)
    if gc == "friends":
        return place.get("group_friendly", True)
    return True


def _budget_ok(place: dict, budget: int) -> bool:
    avg = place.get("price_avg", 0)
    return avg <= budget


def _weather_ok(place: dict, weather: WeatherContext) -> bool:
    if place.get("indoor", True):
        return True
    return weather.condition not in ("rainy", "cold")


def search_places(
    request: UserRequest,
    weather: WeatherContext,
    max_results: int = 10,
) -> List[PlaceResult]:
    """Filter and rank mock places based on the user's request."""
    all_places = _load_places()
    day = _normalize_day(request.date_context)

    scored: List[tuple[float, dict]] = []
    for pl in all_places:
        score = 0.0

        # Skip closed places
        if not _is_open(pl, day):
            continue

        # Budget
        if not _budget_ok(pl, request.budget):
            continue

        # Neighborhood preference
        if request.neighborhood not in ("Any", "any", "") and pl.get("neighborhood") == request.neighborhood:
            score += 3.0

        # Interest match
        for interest in request.interests:
            allowed_cats = _INTEREST_CATEGORY_MAP.get(interest, [])
            if pl.get("category") in allowed_cats:
                score += 2.0
                break

        # Food preference
        if request.food_preference not in ("anything", ""):
            wanted_tags = _FOOD_TAG_MAP.get(request.food_preference.lower(), [request.food_preference.lower()])
            place_tags = [t.lower() for t in pl.get("tags", [])]
            if any(wt in place_tags for wt in wanted_tags):
                score += 3.0

        # Group context
        if _group_matches(pl, request.group_context):
            score += 1.5

        # Vibe match
        if request.vibe.lower() in [v.lower() for v in pl.get("vibe", [])]:
            score += 2.0

        # Weather penalty
        if not _weather_ok(pl, weather):
            score -= 2.5

        # Energy match
        energy_vibe_map = {
            "high": ["energetic", "fun", "social"],
            "medium": ["social", "chill", "casual"],
            "low": ["chill", "romantic", "sophisticated"],
        }
        preferred_vibes = energy_vibe_map.get(request.energy_level, [])
        if any(v in preferred_vibes for v in pl.get("vibe", [])):
            score += 1.0

        scored.append((score, pl))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s[1] for s in scored[:max_results]]
    return [PlaceResult(**pl) for pl in top]
