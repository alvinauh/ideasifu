"""SQLite persistence layer for IdeaSifu's community/social feature.

Tables:
  sessions      — anonymous users (UUID token, credit balance, dojo quota)
  shared_ideas  — ideas a session has opted to share with the community
  contributions — structured peer feedback from one session to another's idea

The DB file lives at /data/ideasifu.db inside the container (see docker-compose
volume mount) or ./ideasifu.db for local dev. Override via IDEASIFU_DB_PATH.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get("IDEASIFU_DB_PATH", "/data/ideasifu.db")

DOJO_FREE_QUOTA = 3        # Dojo section generations a fresh session gets free
CONTRIBUTION_CREDITS = 3   # Credits awarded for a quality-approved contribution


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist. Called once at app startup."""
    with _db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                token       TEXT PRIMARY KEY,
                credits     INTEGER NOT NULL DEFAULT 0,
                dojo_quota  INTEGER NOT NULL DEFAULT 3,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS shared_ideas (
                id            TEXT PRIMARY KEY,
                session_token TEXT NOT NULL,
                title         TEXT NOT NULL,
                statement     TEXT NOT NULL,
                angle         TEXT NOT NULL DEFAULT '',
                shared_at     TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_token) REFERENCES sessions(token)
            );

            CREATE TABLE IF NOT EXISTS contributions (
                id                TEXT PRIMARY KEY,
                idea_id           TEXT NOT NULL,
                contributor_token TEXT NOT NULL,
                type              TEXT NOT NULL CHECK(type IN ('challenge','extend','source')),
                text              TEXT NOT NULL,
                quality_ok        INTEGER NOT NULL DEFAULT 0,
                quality_reason    TEXT NOT NULL DEFAULT '',
                credits_awarded   INTEGER NOT NULL DEFAULT 0,
                created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (idea_id) REFERENCES shared_ideas(id),
                FOREIGN KEY (contributor_token) REFERENCES sessions(token)
            );
        """)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_or_create_session(token: str) -> dict:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO sessions (token, credits, dojo_quota) VALUES (?, 0, ?)",
                (token, DOJO_FREE_QUOTA),
            )
            return {"token": token, "credits": 0, "dojo_quota": DOJO_FREE_QUOTA}
        return dict(row)


def get_session(token: str) -> dict | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        return dict(row) if row else None


def consume_dojo_quota(token: str) -> bool:
    """Decrement dojo_quota (or credits if quota=0). Returns True if allowed."""
    with _db() as conn:
        row = conn.execute(
            "SELECT dojo_quota, credits FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return False
        if row["dojo_quota"] > 0:
            conn.execute(
                "UPDATE sessions SET dojo_quota = dojo_quota - 1 WHERE token = ?",
                (token,),
            )
            return True
        if row["credits"] > 0:
            conn.execute(
                "UPDATE sessions SET credits = credits - 1 WHERE token = ?",
                (token,),
            )
            return True
        return False


def award_credits(token: str, amount: int) -> int:
    """Add `amount` credits to a session. Returns new balance."""
    with _db() as conn:
        conn.execute(
            "UPDATE sessions SET credits = credits + ? WHERE token = ?",
            (amount, token),
        )
        row = conn.execute(
            "SELECT credits FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        return row["credits"] if row else 0


# ---------------------------------------------------------------------------
# Shared ideas helpers
# ---------------------------------------------------------------------------

def share_idea(
    idea_id: str,
    session_token: str,
    title: str,
    statement: str,
    angle: str,
) -> dict:
    with _db() as conn:
        existing = conn.execute(
            "SELECT id FROM shared_ideas WHERE id = ?", (idea_id,)
        ).fetchone()
        if existing:
            row = conn.execute(
                """SELECT id, title, statement, angle, shared_at,
                          (SELECT COUNT(*) FROM contributions c WHERE c.idea_id = s.id) AS contribution_count
                   FROM shared_ideas s WHERE id = ?""",
                (idea_id,),
            ).fetchone()
            return dict(row)
        conn.execute(
            """INSERT INTO shared_ideas (id, session_token, title, statement, angle)
               VALUES (?, ?, ?, ?, ?)""",
            (idea_id, session_token, title, statement, angle),
        )
        return {
            "id": idea_id,
            "title": title,
            "statement": statement,
            "angle": angle,
            "shared_at": "",
            "contribution_count": 0,
        }


def get_shared_ideas(limit: int = 20, offset: int = 0) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            """SELECT s.id, s.title, s.statement, s.angle, s.shared_at,
                      COUNT(c.id) AS contribution_count
               FROM shared_ideas s
               LEFT JOIN contributions c ON c.idea_id = s.id
               GROUP BY s.id
               ORDER BY s.shared_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def count_shared_ideas() -> int:
    with _db() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM shared_ideas").fetchone()
        return row["n"] if row else 0


def get_shared_idea(idea_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute(
            """SELECT s.id, s.title, s.statement, s.angle, s.shared_at,
                      COUNT(c.id) AS contribution_count
               FROM shared_ideas s
               LEFT JOIN contributions c ON c.idea_id = s.id
               WHERE s.id = ?
               GROUP BY s.id""",
            (idea_id,),
        ).fetchone()
        return dict(row) if row else None


def is_idea_shared(idea_id: str) -> bool:
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM shared_ideas WHERE id = ?", (idea_id,)
        ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Contributions helpers
# ---------------------------------------------------------------------------

def add_contribution(
    contrib_id: str,
    idea_id: str,
    contributor_token: str,
    type_: str,
    text: str,
    quality_ok: bool,
    quality_reason: str,
    credits_awarded: int,
) -> dict:
    with _db() as conn:
        conn.execute(
            """INSERT INTO contributions
               (id, idea_id, contributor_token, type, text,
                quality_ok, quality_reason, credits_awarded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contrib_id, idea_id, contributor_token, type_, text,
                1 if quality_ok else 0, quality_reason, credits_awarded,
            ),
        )
    return {
        "id": contrib_id,
        "idea_id": idea_id,
        "type": type_,
        "text": text,
        "quality_ok": quality_ok,
        "quality_reason": quality_reason,
        "credits_awarded": credits_awarded,
    }


def get_contributions_for_idea(idea_id: str) -> list[dict]:
    """Return contributions for an idea (anonymized — no contributor token exposed)."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT id, type, text, quality_ok, credits_awarded, created_at
               FROM contributions WHERE idea_id = ? ORDER BY created_at ASC""",
            (idea_id,),
        ).fetchall()
        return [dict(r) for r in rows]
