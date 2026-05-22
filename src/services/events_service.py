"""
Events service — queries DB first, falls back to mock JSON if DB is empty.
"""
import json
from pathlib import Path
from typing import List

from src.models.schemas import EventResult, UserRequest, WeatherContext
from db import database as db

_MOCK_PATH = Path(__file__).parent.parent / "data" / "mock_events.json"


# ── helpers ────────────────────────────────────────────────────────────────────

def _interest_matches(tags: list, interests: list) -> bool:
    if not interests:
        return True
    tag_set = {t.lower() for t in tags}
    interest_map = {
        "live_music": {"live_music", "music", "concert", "jazz", "rock", "indie"},
        "comedy":     {"comedy", "improv", "standup"},
        "sports":     {"sports", "baseball", "hockey", "basketball", "football"},
        "museums":    {"museum", "arts", "art", "culture"},
        "food_market":{"food", "market", "vendors"},
    }
    for interest in interests:
        mapped = interest_map.get(interest, {interest})
        if mapped & tag_set:
            return True
    return False


def _weather_penalty(indoor: bool, weather: WeatherContext) -> float:
    if indoor:
        return 0.0
    return -2.0 if weather.condition in ("rainy", "cold", "stormy", "snowy") else 0.0


def _energy_bonus(vibes: list, energy_level: str) -> float:
    energy_vibe_map = {
        "high":   ["energetic", "fun", "loud"],
        "medium": ["social", "chill", "casual"],
        "low":    ["chill", "romantic", "sophisticated"],
    }
    preferred = set(energy_vibe_map.get(energy_level, []))
    return 1.0 if preferred & set(v.lower() for v in vibes) else 0.0


# ── DB path ────────────────────────────────────────────────────────────────────

def _score_db_event(ev: dict, request: UserRequest, weather: WeatherContext) -> float:
    score = 0.0
    tags = json.loads(ev.get("tags") or "[]")

    # Budget check (price_min is 0 for free events)
    if ev.get("price_min", 0) > request.budget:
        return -999.0

    # Neighborhood match
    if request.neighborhood not in ("Any", "any", "") and ev.get("neighborhood") == request.neighborhood:
        score += 3.0

    # Interest / category match
    category = ev.get("category", "")
    all_tags = [category] + tags
    if _interest_matches(all_tags, request.interests):
        score += 2.5

    # Weather penalty (assume outdoor if not specified)
    score += _weather_penalty(False, weather)

    # Energy
    score += _energy_bonus(tags, request.energy_level)

    return score


def _db_row_to_event_result(ev: dict) -> EventResult:
    tags = json.loads(ev.get("tags") or "[]")
    price = ev.get("price_min", 0)
    return EventResult(
        id=ev.get("id", ""),
        name=ev.get("name", ""),
        category=ev.get("category", "other"),
        neighborhood=ev.get("neighborhood", "Chicago"),
        venue=ev.get("venue_name", ""),
        address=ev.get("venue_address", ""),
        date=ev.get("event_date", ""),
        time=ev.get("event_time", ""),
        price=float(price),
        vibe=[],
        tags=tags,
        description=f"At {ev.get('venue_name', 'Chicago')}",
        solo_friendly=True,
        group_friendly=True,
        date_friendly=True,
        indoor=True,
        url=ev.get("url", ""),
    )


def _search_db(request: UserRequest, weather: WeatherContext, max_results: int) -> List[EventResult]:
    rows = db.get_upcoming_events(days=14)
    if not rows:
        return []

    scored = []
    for ev in rows:
        s = _score_db_event(ev, request, weather)
        if s > -999.0:
            scored.append((s, ev))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_db_row_to_event_result(r[1]) for r in scored[:max_results]]


# ── Mock fallback ──────────────────────────────────────────────────────────────

def _normalize_date_context(date_context: str) -> List[str]:
    dc = date_context.lower()
    if "tonight" in dc or "friday" in dc:
        return ["friday"]
    if "saturday" in dc:
        return ["saturday"]
    if "sunday" in dc:
        return ["sunday"]
    return ["friday", "saturday", "sunday"]


def _search_mock(request: UserRequest, weather: WeatherContext, max_results: int) -> List[EventResult]:
    with open(_MOCK_PATH) as f:
        all_events = json.load(f)

    valid_dates = _normalize_date_context(request.date_context)
    scored = []
    for ev in all_events:
        score = 0.0
        if ev.get("date") not in valid_dates:
            continue
        if ev.get("price", 0) > request.budget:
            continue
        if request.neighborhood not in ("Any", "any", "") and ev.get("neighborhood") == request.neighborhood:
            score += 3.0
        if _interest_matches([ev.get("category", "")] + ev.get("tags", []), request.interests):
            score += 2.5
        if request.vibe.lower() in [v.lower() for v in ev.get("vibe", [])]:
            score += 2.0
        score += _weather_penalty(ev.get("indoor", True), weather)
        score += _energy_bonus(ev.get("vibe", []), request.energy_level)
        scored.append((score, ev))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, ev in scored[:max_results]:
        results.append(EventResult(
            id=ev["id"], name=ev["name"], category=ev["category"],
            neighborhood=ev["neighborhood"], venue=ev["venue"],
            address=ev["address"], date=ev["date"], time=ev["time"],
            price=float(ev["price"]), vibe=ev.get("vibe", []),
            tags=ev.get("tags", []), description=ev.get("description", ""),
            solo_friendly=ev.get("solo_friendly", True),
            group_friendly=ev.get("group_friendly", True),
            date_friendly=ev.get("date_friendly", True),
            indoor=ev.get("indoor", True),
        ))
    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def search_events(
    request: UserRequest,
    weather: WeatherContext,
    max_results: int = 8,
) -> List[EventResult]:
    """Query DB for live events; fall back to mock data if DB is empty."""
    try:
        if db.get_events_count() > 0:
            results = _search_db(request, weather, max_results)
            if results:
                return results
    except Exception:
        pass
    return _search_mock(request, weather, max_results)
