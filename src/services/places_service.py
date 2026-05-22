"""
Places service — queries DB first (seeded from chicago_places.json),
falls back to original mock_places.json if DB is empty.
"""
import json
from pathlib import Path
from typing import List

from src.models.schemas import PlaceResult, UserRequest, WeatherContext
from db import database as db

_MOCK_PATH = Path(__file__).parent.parent / "data" / "mock_places.json"

_INTEREST_CATEGORY_MAP = {
    "coffee":      {"coffee"},
    "bars":        {"bar"},
    "restaurants": {"restaurant"},
    "museums":     {"museum"},
    "live_music":  {"bar", "restaurant"},
    "comedy":      {"bar"},
    "sports":      {"bar"},
}

_FOOD_TAG_MAP = {
    "mexican":    ["tacos", "mexican"],
    "japanese":   ["ramen", "japanese"],
    "italian":    ["italian", "pizza"],
    "vegetarian": ["vegetarian-friendly", "seasonal"],
    "burgers":    ["burgers"],
    "seafood":    ["oysters", "seafood"],
    "mediterranean": ["mediterranean", "mezze"],
}


def _weather_penalty(indoor: bool, weather: WeatherContext) -> float:
    if indoor:
        return 0.0
    return -2.5 if weather.condition in ("rainy", "cold", "stormy", "snowy") else 0.0


def _energy_bonus(vibes: list, energy_level: str) -> float:
    energy_vibe_map = {
        "high":   ["energetic", "fun", "social"],
        "medium": ["social", "chill", "casual"],
        "low":    ["chill", "romantic", "sophisticated"],
    }
    preferred = set(energy_vibe_map.get(energy_level, []))
    return 1.0 if preferred & set(v.lower() for v in vibes) else 0.0


# ── DB path ────────────────────────────────────────────────────────────────────

def _score_db_place(pl: dict, request: UserRequest, weather: WeatherContext) -> float:
    score = 0.0
    tags = json.loads(pl.get("tags") or "[]")
    vibe = json.loads(pl.get("vibe") or "[]")

    # Budget
    if float(pl.get("price_avg", 0)) > request.budget:
        return -999.0

    # Neighborhood
    if request.neighborhood not in ("Any", "any", "") and pl.get("neighborhood") == request.neighborhood:
        score += 3.0

    # Interest → category
    category = pl.get("category", "")
    for interest in request.interests:
        if category in _INTEREST_CATEGORY_MAP.get(interest, set()):
            score += 2.0
            break

    # Food preference
    if request.food_preference not in ("anything", ""):
        wanted = _FOOD_TAG_MAP.get(request.food_preference.lower(), [request.food_preference.lower()])
        tag_lower = [t.lower() for t in tags]
        if any(w in tag_lower for w in wanted):
            score += 3.0

    # Group context
    gc = request.group_context.lower()
    if gc == "solo"    and pl.get("solo_friendly"):  score += 1.5
    if gc == "date"    and pl.get("date_friendly"):  score += 1.5
    if gc == "friends" and pl.get("group_friendly"): score += 1.5

    # Vibe
    if request.vibe.lower() in [v.lower() for v in vibe]:
        score += 2.0

    # Rating bonus
    score += float(pl.get("rating", 0)) * 0.2

    # Weather penalty
    score += _weather_penalty(bool(pl.get("indoor", 1)), weather)

    # Energy
    score += _energy_bonus(vibe, request.energy_level)

    return score


def _db_row_to_place_result(pl: dict) -> PlaceResult:
    tags = json.loads(pl.get("tags") or "[]")
    vibe = json.loads(pl.get("vibe") or "[]")
    return PlaceResult(
        id=pl["id"],
        name=pl["name"],
        category=pl.get("category", ""),
        neighborhood=pl.get("neighborhood", ""),
        address=pl.get("address", ""),
        price_range=pl.get("price_range", "$"),
        price_avg=float(pl.get("price_avg", 0)),
        vibe=vibe,
        tags=tags,
        description=pl.get("description", ""),
        solo_friendly=bool(pl.get("solo_friendly", 1)),
        date_friendly=bool(pl.get("date_friendly", 1)),
        group_friendly=bool(pl.get("group_friendly", 1)),
        indoor=bool(pl.get("indoor", 1)),
        reservations=bool(pl.get("reservations", 0)),
    )


def _search_db(request: UserRequest, weather: WeatherContext, max_results: int) -> List[PlaceResult]:
    rows = db.get_places()
    if not rows:
        return []

    scored = []
    for pl in rows:
        s = _score_db_place(pl, request, weather)
        if s > -999.0:
            scored.append((s, pl))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_db_row_to_place_result(r[1]) for r in scored[:max_results]]


# ── Mock fallback ──────────────────────────────────────────────────────────────

def _search_mock(request: UserRequest, weather: WeatherContext, max_results: int) -> List[PlaceResult]:
    with open(_MOCK_PATH) as f:
        all_places = json.load(f)

    scored = []
    for pl in all_places:
        score = 0.0
        if pl.get("price_avg", 0) > request.budget:
            continue
        if request.neighborhood not in ("Any", "any", "") and pl.get("neighborhood") == request.neighborhood:
            score += 3.0
        for interest in request.interests:
            if pl.get("category") in _INTEREST_CATEGORY_MAP.get(interest, set()):
                score += 2.0
                break
        if request.food_preference not in ("anything", ""):
            wanted = _FOOD_TAG_MAP.get(request.food_preference.lower(), [request.food_preference.lower()])
            if any(w in [t.lower() for t in pl.get("tags", [])] for w in wanted):
                score += 3.0
        if request.vibe.lower() in [v.lower() for v in pl.get("vibe", [])]:
            score += 2.0
        score += _weather_penalty(pl.get("indoor", True), weather)
        score += _energy_bonus(pl.get("vibe", []), request.energy_level)
        scored.append((score, pl))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, pl in scored[:max_results]:
        results.append(PlaceResult(
            id=pl["id"], name=pl["name"], category=pl["category"],
            neighborhood=pl["neighborhood"], address=pl["address"],
            price_range=pl.get("price_range", "$"),
            price_avg=float(pl.get("price_avg", 0)),
            vibe=pl.get("vibe", []), tags=pl.get("tags", []),
            description=pl.get("description", ""),
            solo_friendly=pl.get("solo_friendly", True),
            date_friendly=pl.get("date_friendly", True),
            group_friendly=pl.get("group_friendly", True),
            indoor=pl.get("indoor", True),
            reservations=pl.get("reservations", False),
        ))
    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def search_places(
    request: UserRequest,
    weather: WeatherContext,
    max_results: int = 10,
) -> List[PlaceResult]:
    """Query DB places (seeded on startup); fall back to mock if DB empty."""
    try:
        if db.get_places_count() > 0:
            results = _search_db(request, weather, max_results)
            if results:
                return results
    except Exception:
        pass
    return _search_mock(request, weather, max_results)
