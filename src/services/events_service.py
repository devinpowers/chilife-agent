"""
Events service — loads and filters mock Chicago events.
"""
import json
from pathlib import Path
from typing import List

from src.models.schemas import EventResult, UserRequest, WeatherContext

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_events.json"


def _load_events() -> List[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


def _normalize_date_context(date_context: str) -> List[str]:
    """Map user date context to event date tags."""
    dc = date_context.lower()
    if "tonight" in dc or "friday" in dc:
        return ["friday"]
    if "saturday" in dc:
        return ["saturday"]
    if "sunday" in dc:
        return ["sunday"]
    if "weekend" in dc:
        return ["friday", "saturday", "sunday"]
    return ["friday", "saturday", "sunday"]


def _interest_matches(event: dict, interests: List[str]) -> bool:
    """Return True if any user interest overlaps event category/tags."""
    if not interests:
        return True
    interest_map = {
        "live_music": ["live_music"],
        "comedy": ["comedy"],
        "sports": ["sports"],
        "museums": ["museum", "arts"],
        "food_market": ["food_market"],
    }
    event_categories = {event["category"]}
    for tag in event.get("tags", []):
        event_categories.add(tag)

    for interest in interests:
        mapped = interest_map.get(interest, [interest])
        if any(m in event_categories for m in mapped):
            return True
    return False


def _group_matches(event: dict, group_context: str) -> bool:
    gc = group_context.lower()
    if gc == "solo":
        return event.get("solo_friendly", True)
    if gc == "date":
        return event.get("date_friendly", True)
    if gc == "friends":
        return event.get("group_friendly", True)
    return True


def _weather_ok(event: dict, weather: WeatherContext) -> bool:
    """Penalize outdoor events in bad weather — but don't hard-filter, just score."""
    if event.get("indoor", True):
        return True
    return weather.condition not in ("rainy", "cold")


def search_events(
    request: UserRequest,
    weather: WeatherContext,
    max_results: int = 8,
) -> List[EventResult]:
    """Filter and rank mock events based on the user's request."""
    all_events = _load_events()
    valid_dates = _normalize_date_context(request.date_context)

    scored: List[tuple[float, dict]] = []
    for ev in all_events:
        score = 0.0

        # Date match
        if ev.get("date") not in valid_dates:
            continue

        # Budget
        if ev.get("price", 0) > request.budget:
            continue

        # Neighborhood preference
        if request.neighborhood not in ("Any", "any", "") and ev.get("neighborhood") == request.neighborhood:
            score += 3.0

        # Interests
        if _interest_matches(ev, request.interests):
            score += 2.5

        # Group context
        if _group_matches(ev, request.group_context):
            score += 1.5

        # Vibe match
        if request.vibe.lower() in [v.lower() for v in ev.get("vibe", [])]:
            score += 2.0

        # Weather penalty for outdoor events
        if not _weather_ok(ev, weather):
            score -= 2.0

        # Energy match
        energy_vibe_map = {
            "high": ["energetic", "fun", "loud"],
            "medium": ["social", "chill", "casual"],
            "low": ["chill", "romantic", "sophisticated"],
        }
        preferred_vibes = energy_vibe_map.get(request.energy_level, [])
        if any(v in preferred_vibes for v in ev.get("vibe", [])):
            score += 1.0

        scored.append((score, ev))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s[1] for s in scored[:max_results]]
    return [EventResult(**ev) for ev in top]
