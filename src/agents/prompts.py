"""
Prompt templates for the LifestyleAgent.
"""
from src.models.schemas import AgentContext


def build_system_prompt() -> str:
    return """You are ChiLife Agent, a personal AI lifestyle concierge for Chicago.

Your job is to suggest 3 distinct, highly-personalized evening or weekend plans
based on the user's mood, budget, neighborhood, group context, food preferences,
and interests.

Each plan must feel like a hand-crafted recommendation from a local Chicago friend —
not a generic list. Include specific venue names, times, and the vibe.

Respond with valid JSON only. Do not include any text outside the JSON.
"""


def build_plan_prompt(ctx: AgentContext) -> str:
    req = ctx.request
    weather = ctx.weather
    events_text = _summarize_events(ctx.matching_events)
    places_text = _summarize_places(ctx.matching_places)
    prefs_text = _summarize_prefs(ctx.user_preferences)

    return f"""
CURRENT CONDITIONS
==================
Weather: {weather.condition}, {weather.temp_f}°F (feels like {weather.feels_like_f}°F)
Note: {weather.recommendation}

USER REQUEST
============
Neighborhood: {req.neighborhood}
Date/Time: {req.date_context}
Vibe: {req.vibe}
Budget: ${req.budget} per person
Group: {req.group_context}
Food preference: {req.food_preference}
Interests: {", ".join(req.interests) if req.interests else "open to anything"}
Energy level: {req.energy_level}
Max travel: {req.max_travel_miles} miles

SAVED PREFERENCES
=================
{prefs_text}

AVAILABLE EVENTS
================
{events_text}

AVAILABLE PLACES
================
{places_text}

TASK
====
Generate exactly 3 plans. Each plan must be distinct in vibe, neighborhood, or activity type.

Return a JSON array with exactly 3 plan objects. Each object must have:
{{
  "plan_id": "plan_1" | "plan_2" | "plan_3",
  "title": "short catchy title",
  "vibe": "one word vibe",
  "neighborhood": "primary Chicago neighborhood",
  "budget_estimate": <integer dollars per person>,
  "confidence_score": <float 0.0–1.0, how well it fits the request>,
  "summary": "2-3 sentence description",
  "why_it_fits": "1-2 sentences explaining why this fits the user's specific request",
  "itinerary": ["7:00 PM – Step 1", "9:00 PM – Step 2", "11:00 PM – Step 3"],
  "weather_note": "optional note about weather impact on this plan"
}}
"""


def _summarize_events(events) -> str:
    if not events:
        return "No events found matching filters."
    lines = []
    for ev in events[:6]:
        lines.append(
            f"- [{ev.category}] {ev.name} @ {ev.venue}, {ev.neighborhood} | "
            f"{ev.date} {ev.time} | ${ev.price} | Vibe: {', '.join(ev.vibe)}"
        )
    return "\n".join(lines)


def _summarize_places(places) -> str:
    if not places:
        return "No places found matching filters."
    lines = []
    for pl in places[:8]:
        lines.append(
            f"- [{pl.category}/{pl.subcategory}] {pl.name} @ {pl.neighborhood} | "
            f"{pl.price_range} (~${pl.price_avg}/person) | Vibe: {', '.join(pl.vibe)}"
        )
    return "\n".join(lines)


def _summarize_prefs(prefs: dict) -> str:
    if not prefs:
        return "New user — no saved preferences yet."
    parts = []
    if prefs.get("favorite_neighborhoods"):
        parts.append(f"Favorite neighborhoods: {', '.join(prefs['favorite_neighborhoods'])}")
    if prefs.get("favorite_vibes"):
        parts.append(f"Favorite vibes: {', '.join(prefs['favorite_vibes'])}")
    if prefs.get("disliked_options"):
        parts.append(f"Previously disliked: {', '.join(prefs['disliked_options'])}")
    return "\n".join(parts) if parts else "No strong preferences saved yet."
