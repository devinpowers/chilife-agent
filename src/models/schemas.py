"""
Pydantic models for ChiLife Agent data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input / Request
# ---------------------------------------------------------------------------

class UserRequest(BaseModel):
    """Everything the user submits from the Streamlit UI."""
    neighborhood: str = "Any"
    date_context: str = "tonight"          # tonight / this weekend / saturday / sunday
    vibe: str = "anything"                 # chill / energetic / romantic / adventurous / fun
    budget: int = 50                       # dollars per person
    group_context: str = "solo"            # solo / date / friends
    food_preference: str = "anything"      # anything / vegetarian / mexican / japanese / italian
    interests: List[str] = Field(default_factory=list)  # live_music, comedy, sports, coffee, bars, restaurants, museums
    max_travel_miles: float = 5.0
    energy_level: str = "medium"           # low / medium / high
    user_id: str = "default"


# ---------------------------------------------------------------------------
# Context assembled by the agent
# ---------------------------------------------------------------------------

class WeatherContext(BaseModel):
    condition: str      # sunny / cloudy / rainy / cold / warm
    temp_f: int
    feels_like_f: int
    recommendation: str  # short human-readable note


class EventResult(BaseModel):
    id: str
    name: str
    category: str
    neighborhood: str
    venue: str
    address: str
    date: str
    time: str
    price: float
    vibe: List[str]
    tags: List[str]
    description: str
    solo_friendly: bool
    group_friendly: bool
    date_friendly: bool
    indoor: bool


class PlaceResult(BaseModel):
    id: str
    name: str
    category: str
    subcategory: str
    neighborhood: str
    address: str
    price_range: str
    price_avg: float
    vibe: List[str]
    tags: List[str]
    description: str
    hours: dict
    solo_friendly: bool
    date_friendly: bool
    group_friendly: bool
    indoor: bool
    reservations: bool


class AgentContext(BaseModel):
    """Everything the agent gathered before reasoning."""
    request: UserRequest
    weather: WeatherContext
    matching_events: List[EventResult] = Field(default_factory=list)
    matching_places: List[PlaceResult] = Field(default_factory=list)
    user_preferences: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Output / Plans
# ---------------------------------------------------------------------------

class Plan(BaseModel):
    """A single suggested plan for the evening/weekend."""
    plan_id: str
    title: str
    vibe: str
    neighborhood: str
    budget_estimate: int          # dollars per person
    confidence_score: float       # 0.0 – 1.0
    summary: str                  # 2-3 sentence overview
    why_it_fits: str              # explanation tied to user's request
    itinerary: List[str]          # ordered steps, e.g. ["7pm – Dinner at Lula Cafe", "9pm – ..."]
    events: List[EventResult] = Field(default_factory=list)
    places: List[PlaceResult] = Field(default_factory=list)
    weather_note: Optional[str] = None


class PlanSet(BaseModel):
    """Three plans returned to the UI."""
    plans: List[Plan]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    llm_used: bool = False


# ---------------------------------------------------------------------------
# Feedback / Memory
# ---------------------------------------------------------------------------

class Feedback(BaseModel):
    plan_id: str
    user_id: str
    rating: str          # thumbs_up / thumbs_down
    saved_neighborhood: Optional[str] = None
    saved_vibe: Optional[str] = None
    disliked_option: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class UserPreferences:
    user_id: str
    favorite_neighborhoods: List[str] = field(default_factory=list)
    favorite_vibes: List[str] = field(default_factory=list)
    disliked_options: List[str] = field(default_factory=list)
    last_budget: int = 50
    last_group_context: str = "solo"
    updated_at: Optional[str] = None
