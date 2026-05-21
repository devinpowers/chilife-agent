"""
LifestyleAgent — the core reasoning loop for ChiLife Agent.

Loop:
  1. Observe  — receive UserRequest
  2. Gather   — load prefs, get weather, search events & places
  3. Reason   — call LLM (or fallback to rule-based engine)
  4. Generate — return PlanSet with 3 plans
  5. Save     — persist plans and feedback to memory
"""
import json
import os
import uuid
from typing import Optional

from src.agents.prompts import build_system_prompt, build_plan_prompt
from src.models.schemas import (
    AgentContext,
    Plan,
    PlanSet,
    UserRequest,
    Feedback,
)
from src.services.events_service import search_events
from src.services.places_service import search_places
from src.services.weather_service import get_weather
from src.services.memory_service import (
    load_preferences,
    record_plans,
    record_feedback,
)


class LifestyleAgent:
    """
    Orchestrates the full observe → gather → reason → generate → save loop.
    Uses an OpenAI-compatible client when OPENAI_API_KEY is set;
    falls back to a deterministic rule-based engine otherwise.
    """

    def __init__(self):
        self._client = self._init_llm_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_plans(self, request: UserRequest) -> PlanSet:
        """Main entry point called by the Streamlit app."""

        # 1. OBSERVE
        print(f"[Agent] Observing request from user={request.user_id}")

        # 2. GATHER context
        ctx = self._gather_context(request)

        # 3. REASON + 4. GENERATE
        if self._client:
            plan_set = self._llm_generate(ctx)
        else:
            plan_set = self._rule_based_generate(ctx)

        # 5. SAVE plans to history
        record_plans(request.user_id, plan_set.plans)

        return plan_set

    def save_feedback(self, feedback: Feedback) -> None:
        """Persist user feedback and update memory."""
        record_feedback(feedback)

    # ------------------------------------------------------------------
    # Context gathering
    # ------------------------------------------------------------------

    def _gather_context(self, request: UserRequest) -> AgentContext:
        weather = get_weather(request.date_context)
        events = search_events(request, weather)
        places = search_places(request, weather)
        prefs = load_preferences(request.user_id)

        print(
            f"[Agent] Gathered: weather={weather.condition} {weather.temp_f}°F, "
            f"events={len(events)}, places={len(places)}"
        )

        return AgentContext(
            request=request,
            weather=weather,
            matching_events=events,
            matching_places=places,
            user_preferences=prefs,
        )

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _init_llm_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[Agent] No OPENAI_API_KEY found — using rule-based fallback.")
            return None
        try:
            from openai import OpenAI  # type: ignore
            base_url = os.getenv("OPENAI_BASE_URL")
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return OpenAI(**kwargs)
        except ImportError:
            print("[Agent] openai package not installed — using rule-based fallback.")
            return None

    def _llm_generate(self, ctx: AgentContext) -> PlanSet:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        system_prompt = build_system_prompt()
        user_prompt = build_plan_prompt(ctx)

        print(f"[Agent] Calling LLM model={model}")
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            plans_data = json.loads(raw)
            plans = [Plan(**p) for p in plans_data]
            return PlanSet(plans=plans, llm_used=True)

        except Exception as exc:
            print(f"[Agent] LLM call failed ({exc}), falling back to rule-based.")
            return self._rule_based_generate(ctx)

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _rule_based_generate(self, ctx: AgentContext) -> PlanSet:
        """
        Deterministic plan generator that works without an API key.
        Builds 3 plans from the top-scored events and places.
        """
        print("[Agent] Generating rule-based plans.")
        req = ctx.request
        events = ctx.matching_events
        places = ctx.matching_places
        weather = ctx.weather

        plans = []

        # Plan 1 — Best event + nearby food/bar
        plan1 = self._build_event_plan(
            plan_id="plan_1",
            ctx=ctx,
            event_idx=0,
            place_idx=0,
            label="Top Pick",
        )
        plans.append(plan1)

        # Plan 2 — Dinner + second event or second bar
        plan2 = self._build_dining_plan(
            plan_id="plan_2",
            ctx=ctx,
            place_idx=1,
            event_idx=1,
            label="Dinner First",
        )
        plans.append(plan2)

        # Plan 3 — Explore a different neighborhood / low-key option
        plan3 = self._build_explore_plan(
            plan_id="plan_3",
            ctx=ctx,
            label="Low-Key Alternative",
        )
        plans.append(plan3)

        return PlanSet(plans=plans, llm_used=False)

    # ------------------------------------------------------------------
    # Plan builder helpers for rule-based engine
    # ------------------------------------------------------------------

    def _build_event_plan(
        self, plan_id: str, ctx: AgentContext, event_idx: int, place_idx: int, label: str
    ) -> Plan:
        req = ctx.request
        events = ctx.matching_events
        places = ctx.matching_places
        weather = ctx.weather

        event = events[event_idx] if event_idx < len(events) else None
        place = places[place_idx] if place_idx < len(places) else None

        if event:
            neighborhood = event.neighborhood
            vibe = event.vibe[0] if event.vibe else req.vibe
            budget = int(event.price + (place.price_avg if place else 20))
            itinerary = []
            if place:
                itinerary.append(f"7:00 PM – {place.name} ({place.subcategory}, {place.neighborhood})")
            itinerary.append(f"{event.time} – {event.name} @ {event.venue}")
            itinerary.append("After – Grab drinks nearby and recap the show")
            summary = (
                f"Start with {place.name} in {place.neighborhood} before heading to "
                f"{event.name} at {event.venue}. "
                f"{event.description}"
            ) if place else f"Head straight to {event.name} at {event.venue}. {event.description}"
            why = f"This matches your {req.vibe} vibe and fits your ${req.budget} budget. {weather.recommendation}"
        else:
            # No events, build purely from places
            return self._build_dining_plan(plan_id, ctx, 0, 0, label)

        return Plan(
            plan_id=plan_id,
            title=f"{label}: {event.name}" if event else label,
            vibe=vibe,
            neighborhood=neighborhood,
            budget_estimate=min(budget, req.budget),
            confidence_score=0.88,
            summary=summary,
            why_it_fits=why,
            itinerary=itinerary,
            events=[event] if event else [],
            places=[place] if place else [],
            weather_note=weather.recommendation if not event.indoor else None,
        )

    def _build_dining_plan(
        self, plan_id: str, ctx: AgentContext, place_idx: int, event_idx: int, label: str
    ) -> Plan:
        req = ctx.request
        places = ctx.matching_places
        events = ctx.matching_events
        weather = ctx.weather

        place = places[place_idx] if place_idx < len(places) else None
        bar = self._find_bar(places, exclude_idx=place_idx)
        event = events[event_idx] if event_idx < len(events) else None

        if place:
            neighborhood = place.neighborhood
            vibe = place.vibe[0] if place.vibe else req.vibe
            budget = int(place.price_avg + (bar.price_avg if bar else 15))
            itinerary = [f"7:00 PM – Dinner at {place.name} ({place.subcategory})"]
            if event:
                itinerary.append(f"{event.time} – {event.name} @ {event.venue}")
            elif bar:
                itinerary.append(f"9:30 PM – Cocktails at {bar.name}")
            itinerary.append("Late – Explore the neighborhood")
            summary = f"Dinner at {place.name}, known for {', '.join(place.tags[:3])}. {place.description}"
            why = f"Centered on your food preference ({req.food_preference}) in a {req.vibe} setting. Budget ~${budget}/person."
        else:
            neighborhood = req.neighborhood
            vibe = req.vibe
            budget = req.budget
            itinerary = ["Explore the neighborhood", "Find a local bar or restaurant"]
            summary = "Flexible evening exploring Chicago's neighborhoods."
            why = "Based on your preferences, a relaxed exploration night suits you."

        return Plan(
            plan_id=plan_id,
            title=f"{label}: {place.name}" if place else label,
            vibe=vibe,
            neighborhood=neighborhood,
            budget_estimate=min(budget, req.budget),
            confidence_score=0.80,
            summary=summary,
            why_it_fits=why,
            itinerary=itinerary,
            events=[event] if event else [],
            places=[p for p in [place, bar] if p],
            weather_note=weather.recommendation,
        )

    def _build_explore_plan(self, plan_id: str, ctx: AgentContext, label: str) -> Plan:
        req = ctx.request
        places = ctx.matching_places
        events = ctx.matching_events
        weather = ctx.weather

        # Pick places from a different neighborhood than the top result
        top_neighborhood = places[0].neighborhood if places else req.neighborhood
        alt_places = [p for p in places if p.neighborhood != top_neighborhood]
        alt_events = [e for e in events if e.neighborhood != top_neighborhood]

        place = alt_places[0] if alt_places else (places[-1] if places else None)
        event = alt_events[0] if alt_events else None

        neighborhood = place.neighborhood if place else "Chicago"
        vibe = "chill" if req.energy_level == "low" else "adventurous"
        budget = int((place.price_avg if place else 20) + (event.price if event else 10))

        itinerary = []
        if event and event.time <= "3:00 PM":
            itinerary.append(f"{event.time} – {event.name} (daytime)")
        if place:
            itinerary.append(f"6:30 PM – {place.name} in {place.neighborhood}")
        if event and event.time > "3:00 PM":
            itinerary.append(f"{event.time} – {event.name} @ {event.venue}")
        itinerary.append("Wander and discover the neighborhood on foot")

        summary = f"A more exploratory evening, venturing into {neighborhood}. " + (
            f"{place.description}" if place else ""
        )
        why = f"Mix it up from your usual spots. {weather.recommendation}"

        return Plan(
            plan_id=plan_id,
            title=f"{label}: {neighborhood} Night",
            vibe=vibe,
            neighborhood=neighborhood,
            budget_estimate=min(max(budget, 20), req.budget),
            confidence_score=0.72,
            summary=summary,
            why_it_fits=why,
            itinerary=itinerary if itinerary else ["Explore the neighborhood freely"],
            events=[event] if event else [],
            places=[place] if place else [],
            weather_note=weather.recommendation,
        )

    def _find_bar(self, places, exclude_idx: int):
        for i, p in enumerate(places):
            if i != exclude_idx and p.category == "bar":
                return p
        return None
