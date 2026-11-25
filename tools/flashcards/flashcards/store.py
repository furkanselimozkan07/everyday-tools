"""SQLite persistence. DB path: $FLASHCARDS_DB or ~/.local/share/flashcards/cards.db"""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path

from .core import Card

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY, deck TEXT NOT NULL, front TEXT NOT NULL, back TEXT NOT NULL,
  ease REAL NOT NULL, interval INTEGER NOT NULL, reps INTEGER NOT NULL,
  due TEXT NOT NULL, lapses INTEGER NOT NULL DEFAULT 0,
  UNIQUE(deck, front)
);
"""


def default_path() -> Path:
    env = os.environ.get("FLASHCARDS_DB")
    return Path(env) if env else Path.home() / ".local/share/flashcards/cards.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    p = Path(path) if path else default_path()
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _row(r: sqlite3.Row) -> Card:
    return Card(r["front"], r["back"], r["deck"], r["ease"], r["interval"], r["reps"],
                date.fromisoformat(r["due"]), r["lapses"], r["id"])


def add_cards(con: sqlite3.Connection, cards: list[Card], today: date) -> tuple[int, int]:
    """Insert new cards (due today). Existing (deck, front) pairs keep their
    schedule but get the new back text. Returns (added, updated)."""
    added = updated = 0
    for c in cards:
        cur = con.execute("UPDATE cards SET back=? WHERE deck=? AND front=?",
                          (c.back, c.deck, c.front))
        if cur.rowcount:
            updated += 1
            continue
        con.execute("INSERT INTO cards(deck,front,back,ease,interval,reps,due,lapses) "
                    "VALUES(?,?,?,?,?,?,?,0)",
                    (c.deck, c.front, c.back, c.ease, c.interval, c.reps, today.isoformat()))
        added += 1
    con.commit()
    return added, updated


def due_cards(con: sqlite3.Connection, today: date, deck: str | None = None,
              limit: int | None = None) -> list[Card]:
    q = "SELECT * FROM cards WHERE due<=?"
    args: list = [today.isoformat()]
    if deck:
        q += " AND deck=?"
        args.append(deck)
    q += " ORDER BY due, id"
    if limit:
        q += " LIMIT ?"
        args.append(limit)
    return [_row(r) for r in con.execute(q, args)]


def save_review(con: sqlite3.Connection, card: Card) -> None:
    con.execute("UPDATE cards SET ease=?, interval=?, reps=?, due=?, lapses=? WHERE id=?",
                (card.ease, card.interval, card.reps, card.due.isoformat(), card.lapses, card.id))
    con.commit()


def stats(con: sqlite3.Connection, today: date) -> list[dict]:
    rows = con.execute(
        "SELECT deck, COUNT(*) total, SUM(due<=?) due, SUM(reps=0) new, "
        "SUM(interval>=21) mature FROM cards GROUP BY deck ORDER BY deck",
        (today.isoformat(),))
    return [dict(r) for r in rows]


def delete_deck(con: sqlite3.Connection, deck: str) -> int:
    n = con.execute("DELETE FROM cards WHERE deck=?", (deck,)).rowcount
    con.commit()
    return n
