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
