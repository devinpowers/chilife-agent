"""
Memory service — persists and retrieves user preferences and feedback via SQLite.
"""
from typing import Any, Dict, List, Optional

from db.database import (
    get_user_preferences,
    upsert_user_preferences,
    save_plan,
    get_plan_history,
    save_feedback as db_save_feedback,
    get_feedback,
)
from src.models.schemas import Plan, Feedback


def load_preferences(user_id: str) -> Dict[str, Any]:
    """Return the user's stored preferences, or empty dict if new user."""
    return get_user_preferences(user_id)


def save_preferences(user_id: str, prefs: Dict[str, Any]) -> None:
    upsert_user_preferences(user_id, prefs)


def record_plan(user_id: str, plan: Plan) -> None:
    """Persist a generated plan to the history table."""
    save_plan(user_id, plan.model_dump(mode="json"))


def record_plans(user_id: str, plans: List[Plan]) -> None:
    for plan in plans:
        record_plan(user_id, plan)


def record_feedback(feedback: Feedback) -> None:
    """Save user feedback and update preferences accordingly."""
    db_save_feedback(feedback.model_dump(mode="json"))

    # Load current prefs and update based on what the user saved
    prefs = get_user_preferences(feedback.user_id) or {
        "user_id": feedback.user_id,
        "favorite_neighborhoods": [],
        "favorite_vibes": [],
        "disliked_options": [],
        "last_budget": 50,
        "last_group_context": "solo",
    }

    if feedback.saved_neighborhood:
        if feedback.saved_neighborhood not in prefs["favorite_neighborhoods"]:
            prefs["favorite_neighborhoods"].append(feedback.saved_neighborhood)

    if feedback.saved_vibe:
        if feedback.saved_vibe not in prefs["favorite_vibes"]:
            prefs["favorite_vibes"].append(feedback.saved_vibe)

    if feedback.disliked_option:
        if feedback.disliked_option not in prefs["disliked_options"]:
            prefs["disliked_options"].append(feedback.disliked_option)

    upsert_user_preferences(feedback.user_id, prefs)


def get_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    return get_plan_history(user_id, limit)
