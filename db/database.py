"""
SQLite database layer for ChiLife Agent.
Tables: user_preferences, plan_history, feedback

Locally:  db/chilife.db (created on first run)
On Azure: same file, but stored on an Azure Files persistent volume
          mounted at /data — set SQLITE_DIR=/data in Container Apps env vars.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow overriding the directory so Azure can mount a persistent volume here
_db_dir = Path(os.getenv("SQLITE_DIR", Path(__file__).parent))
DB_PATH = _db_dir / "chilife.db"


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id          TEXT PRIMARY KEY,
                favorite_neighborhoods TEXT DEFAULT '[]',
                favorite_vibes   TEXT DEFAULT '[]',
                disliked_options TEXT DEFAULT '[]',
                last_budget      INTEGER DEFAULT 50,
                last_group_context TEXT DEFAULT 'solo',
                updated_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS plan_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                plan_id     TEXT NOT NULL,
                title       TEXT,
                vibe        TEXT,
                neighborhood TEXT,
                budget_estimate INTEGER,
                confidence_score REAL,
                summary     TEXT,
                full_plan   TEXT,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id         TEXT NOT NULL,
                user_id         TEXT NOT NULL,
                rating          TEXT,
                saved_neighborhood TEXT,
                saved_vibe      TEXT,
                disliked_option TEXT,
                timestamp       TEXT
            );

            -- ── Live data tables ──────────────────────────────────────────────

            CREATE TABLE IF NOT EXISTS events (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                category        TEXT,
                subcategory     TEXT,
                venue_name      TEXT,
                venue_address   TEXT,
                neighborhood    TEXT,
                latitude        REAL DEFAULT 0,
                longitude       REAL DEFAULT 0,
                event_date      TEXT,
                event_time      TEXT,
                price_min       REAL DEFAULT 0,
                price_max       REAL DEFAULT 0,
                url             TEXT,
                image_url       TEXT,
                tags            TEXT DEFAULT '[]',
                source          TEXT DEFAULT 'ticketmaster',
                fetched_at      TEXT,
                is_active       INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS weather_observations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at     TEXT NOT NULL,
                forecast_for    TEXT,
                temp_f          REAL,
                feels_like_f    REAL,
                condition       TEXT,
                description     TEXT,
                humidity        INTEGER,
                wind_mph        REAL,
                is_forecast     INTEGER DEFAULT 0,
                fetched_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS places (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                category        TEXT,
                subcategory     TEXT,
                neighborhood    TEXT,
                address         TEXT,
                price_range     TEXT,
                price_avg       REAL DEFAULT 0,
                rating          REAL DEFAULT 0,
                description     TEXT,
                tags            TEXT DEFAULT '[]',
                vibe            TEXT DEFAULT '[]',
                solo_friendly   INTEGER DEFAULT 1,
                date_friendly   INTEGER DEFAULT 1,
                group_friendly  INTEGER DEFAULT 1,
                indoor          INTEGER DEFAULT 1,
                reservations    INTEGER DEFAULT 0,
                source          TEXT DEFAULT 'manual',
                fetched_at      TEXT DEFAULT (datetime('now')),
                is_active       INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS fetch_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source          TEXT NOT NULL,
                status          TEXT NOT NULL,
                records_upserted INTEGER DEFAULT 0,
                error_message   TEXT,
                fetched_at      TEXT DEFAULT (datetime('now'))
            );
        """)


# ── user_preferences ──────────────────────────────────────────────────────────

def get_user_preferences(user_id: str) -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return {}
    return {
        "user_id": row["user_id"],
        "favorite_neighborhoods": json.loads(row["favorite_neighborhoods"]),
        "favorite_vibes": json.loads(row["favorite_vibes"]),
        "disliked_options": json.loads(row["disliked_options"]),
        "last_budget": row["last_budget"],
        "last_group_context": row["last_group_context"],
        "updated_at": row["updated_at"],
    }


def upsert_user_preferences(user_id: str, data: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE user_preferences
                SET favorite_neighborhoods = ?,
                    favorite_vibes = ?,
                    disliked_options = ?,
                    last_budget = ?,
                    last_group_context = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (
                json.dumps(data.get("favorite_neighborhoods", [])),
                json.dumps(data.get("favorite_vibes", [])),
                json.dumps(data.get("disliked_options", [])),
                data.get("last_budget", 50),
                data.get("last_group_context", "solo"),
                now,
                user_id,
            ))
        else:
            conn.execute("""
                INSERT INTO user_preferences
                    (user_id, favorite_neighborhoods, favorite_vibes, disliked_options,
                     last_budget, last_group_context, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                json.dumps(data.get("favorite_neighborhoods", [])),
                json.dumps(data.get("favorite_vibes", [])),
                json.dumps(data.get("disliked_options", [])),
                data.get("last_budget", 50),
                data.get("last_group_context", "solo"),
                now,
            ))


# ── plan_history ──────────────────────────────────────────────────────────────

def save_plan(user_id: str, plan: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO plan_history
                (user_id, plan_id, title, vibe, neighborhood, budget_estimate,
                 confidence_score, summary, full_plan, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            plan.get("plan_id", ""),
            plan.get("title", ""),
            plan.get("vibe", ""),
            plan.get("neighborhood", ""),
            plan.get("budget_estimate", 0),
            plan.get("confidence_score", 0.0),
            plan.get("summary", ""),
            json.dumps(plan),
            datetime.utcnow().isoformat(),
        ))


def get_plan_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM plan_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── feedback ──────────────────────────────────────────────────────────────────

def save_feedback(feedback: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO feedback
                (plan_id, user_id, rating, saved_neighborhood, saved_vibe,
                 disliked_option, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback.get("plan_id", ""),
            feedback.get("user_id", "default"),
            feedback.get("rating", ""),
            feedback.get("saved_neighborhood"),
            feedback.get("saved_vibe"),
            feedback.get("disliked_option"),
            datetime.utcnow().isoformat(),
        ))


def get_feedback(user_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── events ─────────────────────────────────────────────────────────────────────

def upsert_events(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO events
                (id, name, category, subcategory, venue_name, venue_address,
                 neighborhood, latitude, longitude, event_date, event_time,
                 price_min, price_max, url, image_url, tags, source, fetched_at, is_active)
            VALUES
                (:id, :name, :category, :subcategory, :venue_name, :venue_address,
                 :neighborhood, :latitude, :longitude, :event_date, :event_time,
                 :price_min, :price_max, :url, :image_url, :tags, :source, :fetched_at, 1)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, category=excluded.category,
                subcategory=excluded.subcategory, venue_name=excluded.venue_name,
                neighborhood=excluded.neighborhood, event_date=excluded.event_date,
                event_time=excluded.event_time, price_min=excluded.price_min,
                price_max=excluded.price_max, tags=excluded.tags,
                fetched_at=excluded.fetched_at, is_active=1
        """, rows)
    return len(rows)


def get_upcoming_events(days: int = 14, neighborhood: Optional[str] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT * FROM events
        WHERE is_active = 1
          AND event_date >= date('now')
          AND event_date <= date('now', ? || ' days')
    """
    params: list = [str(days)]
    if neighborhood:
        query += " AND neighborhood = ?"
        params.append(neighborhood)
    query += " ORDER BY event_date ASC, price_min ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_events_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM events WHERE is_active = 1").fetchone()[0]


# ── weather_observations ───────────────────────────────────────────────────────

def insert_weather(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO weather_observations
                (observed_at, forecast_for, temp_f, feels_like_f, condition,
                 description, humidity, wind_mph, is_forecast, fetched_at)
            VALUES
                (:observed_at, :forecast_for, :temp_f, :feels_like_f, :condition,
                 :description, :humidity, :wind_mph, :is_forecast, :fetched_at)
        """, rows)
    return len(rows)


def get_current_weather() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM weather_observations
            WHERE is_forecast = 0
            ORDER BY fetched_at DESC LIMIT 1
        """).fetchone()
    return dict(row) if row else None


def get_weather_forecast(days: int = 5) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM weather_observations
            WHERE is_forecast = 1
              AND forecast_for >= date('now')
            ORDER BY forecast_for ASC
            LIMIT ?
        """, (days,)).fetchall()
    return [dict(r) for r in rows]


def get_last_weather_fetch() -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT fetched_at FROM weather_observations ORDER BY fetched_at DESC LIMIT 1"
        ).fetchone()
    return row["fetched_at"] if row else None


# ── places ─────────────────────────────────────────────────────────────────────

def upsert_places(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO places
                (id, name, category, subcategory, neighborhood, address,
                 price_range, price_avg, rating, description, tags, vibe,
                 solo_friendly, date_friendly, group_friendly, indoor,
                 reservations, source, fetched_at, is_active)
            VALUES
                (:id, :name, :category, :subcategory, :neighborhood, :address,
                 :price_range, :price_avg, :rating, :description, :tags, :vibe,
                 :solo_friendly, :date_friendly, :group_friendly, :indoor,
                 :reservations, :source, :fetched_at, 1)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, description=excluded.description,
                tags=excluded.tags, vibe=excluded.vibe,
                price_avg=excluded.price_avg, fetched_at=excluded.fetched_at
        """, rows)
    return len(rows)


def get_places(neighborhood: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM places WHERE is_active = 1"
    params: list = []
    if neighborhood:
        query += " AND neighborhood = ?"
        params.append(neighborhood)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY rating DESC, name ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_places_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM places WHERE is_active = 1").fetchone()[0]


# ── fetch_log ──────────────────────────────────────────────────────────────────

def log_fetch(source: str, status: str, records: int = 0, error: str = None) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO fetch_log (source, status, records_upserted, error_message, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (source, status, records, error, datetime.utcnow().isoformat()))


def get_last_fetch(source: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT fetched_at FROM fetch_log
            WHERE source = ? AND status = 'success'
            ORDER BY fetched_at DESC LIMIT 1
        """, (source,)).fetchone()
    return row["fetched_at"] if row else None
