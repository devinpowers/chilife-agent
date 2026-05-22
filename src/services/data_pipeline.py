"""
Data pipeline orchestrator.

Checks staleness of each data source and refreshes as needed:
  - Places:  seed once (on empty table)
  - Weather: refresh every 3 hours
  - Events:  refresh every 6 hours

Call run() on app startup (wrapped in a background thread).
All results are logged to the fetch_log table.
"""
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

from db import database as db
from src.services import ticketmaster_service, openweather_service

logger = logging.getLogger(__name__)

_WEATHER_STALE_HOURS = 3
_EVENTS_STALE_HOURS  = 6
_PLACES_JSON = Path(__file__).parent.parent / "data" / "chicago_places.json"

_running = False
_lock = threading.Lock()


def _is_stale(last_fetch_iso: str | None, hours: int) -> bool:
    if not last_fetch_iso:
        return True
    try:
        last = datetime.fromisoformat(last_fetch_iso.replace("Z", "+00:00"))
        last = last.replace(tzinfo=None)
        return datetime.utcnow() - last > timedelta(hours=hours)
    except Exception:
        return True


# ── Places ─────────────────────────────────────────────────────────────────────

def _seed_places() -> None:
    count = db.get_places_count()
    if count > 0:
        logger.info("Places: %d rows already in DB — skipping seed", count)
        return
    try:
        raw = json.loads(_PLACES_JSON.read_text())
        now = datetime.utcnow().isoformat()
        rows = []
        for p in raw:
            rows.append({
                "id":            p["id"],
                "name":          p["name"],
                "category":      p.get("category", ""),
                "subcategory":   p.get("subcategory", ""),
                "neighborhood":  p.get("neighborhood", ""),
                "address":       p.get("address", ""),
                "price_range":   p.get("price_range", ""),
                "price_avg":     float(p.get("price_avg", 0)),
                "rating":        float(p.get("rating", 0)),
                "description":   p.get("description", ""),
                "tags":          json.dumps(p.get("tags", [])),
                "vibe":          json.dumps(p.get("vibe", [])),
                "solo_friendly": int(p.get("solo_friendly", 1)),
                "date_friendly": int(p.get("date_friendly", 1)),
                "group_friendly":int(p.get("group_friendly", 1)),
                "indoor":        int(p.get("indoor", 1)),
                "reservations":  int(p.get("reservations", 0)),
                "source":        "manual",
                "fetched_at":    now,
            })
        n = db.upsert_places(rows)
        db.log_fetch("places", "success", n)
        logger.info("Places: seeded %d rows", n)
    except Exception as exc:
        db.log_fetch("places", "error", 0, str(exc))
        logger.error("Places seed error: %s", exc)


# ── Weather ────────────────────────────────────────────────────────────────────

def _refresh_weather() -> None:
    last = db.get_last_fetch("weather")
    if not _is_stale(last, _WEATHER_STALE_HOURS):
        logger.info("Weather: fresh (last fetch %s) — skipping", last)
        return
    try:
        rows = openweather_service.fetch_and_clean()
        if rows:
            n = db.insert_weather(rows)
            db.log_fetch("weather", "success", n)
            logger.info("Weather: inserted %d rows", n)
        else:
            db.log_fetch("weather", "skipped", 0, "No API key or empty response")
    except Exception as exc:
        db.log_fetch("weather", "error", 0, str(exc))
        logger.error("Weather refresh error: %s", exc)


# ── Events ─────────────────────────────────────────────────────────────────────

def _refresh_events() -> None:
    last = db.get_last_fetch("ticketmaster")
    if not _is_stale(last, _EVENTS_STALE_HOURS):
        logger.info("Events: fresh (last fetch %s) — skipping", last)
        return
    try:
        rows = ticketmaster_service.fetch_and_clean()
        if rows:
            n = db.upsert_events(rows)
            db.log_fetch("ticketmaster", "success", n)
            logger.info("Events: upserted %d rows", n)
        else:
            db.log_fetch("ticketmaster", "skipped", 0, "No API key or empty response")
    except Exception as exc:
        db.log_fetch("ticketmaster", "error", 0, str(exc))
        logger.error("Events refresh error: %s", exc)


# ── Public API ─────────────────────────────────────────────────────────────────

def run() -> None:
    """Run the full pipeline (places seed + weather + events)."""
    global _running
    with _lock:
        if _running:
            logger.info("Pipeline already running — skipping")
            return
        _running = True
    try:
        db.init_db()
        _seed_places()
        _refresh_weather()
        _refresh_events()
    finally:
        with _lock:
            _running = False


def run_in_background() -> None:
    """Launch run() in a daemon thread so it doesn't block the UI."""
    t = threading.Thread(target=run, daemon=True, name="data-pipeline")
    t.start()
