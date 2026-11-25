"""Pure logic: SM-2 scheduling and deck parsing (no I/O besides reading text)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from datetime import date, timedelta

MIN_EASE = 1.3
DEFAULT_EASE = 2.5


@dataclass(frozen=True)
class Card:
    front: str
    back: str
    deck: str = "default"
    ease: float = DEFAULT_EASE
    interval: int = 0        # days
    reps: int = 0            # consecutive successful reviews
    due: date = date(1970, 1, 1)
    lapses: int = 0
    id: int | None = None


def sm2(card: Card, quality: int, today: date) -> Card:
    """Return the card after a review graded 0-5 (SuperMemo SM-2).

    quality < 3 counts as a lapse: repetitions restart and the card is due again
    tomorrow. Otherwise the interval grows 1 -> 6 -> interval * ease.
    """
    if not 0 <= quality <= 5:
        raise ValueError("quality must be between 0 and 5")
    ease = max(MIN_EASE, card.ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if quality < 3:
        return replace(card, ease=ease, reps=0, interval=1,
                       lapses=card.lapses + 1, due=today + timedelta(days=1))
    if card.reps == 0:
        interval = 1
    elif card.reps == 1:
        interval = 6
    else:
        interval = max(card.interval + 1, round(card.interval * ease))
    return replace(card, ease=ease, reps=card.reps + 1, interval=interval,
                   due=today + timedelta(days=interval))


def is_due(card: Card, today: date) -> bool:
    return card.due <= today


def parse_csv(text: str, deck: str = "default") -> list[Card]:
    """`front,back` rows. Delimiter (, ; or tab) is sniffed; a header row
    named front/back (or ön/arka, soru/cevap) is skipped."""
    text = text.lstrip("﻿")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    cards = []
    for i, row in enumerate(csv.reader(io.StringIO(text), dialect)):
        row = [c.strip() for c in row]
        if len(row) < 2 or not row[0] or not row[1]:
            continue
        if i == 0 and row[0].lower() in {"front", "ön", "on", "soru", "question"}:
            continue
        cards.append(Card(row[0], row[1], deck))
    return cards


def parse_markdown(text: str, deck: str = "default") -> list[Card]:
    """Two supported notations, mixable in one file:

    ``front :: back`` on a single line, or
    ``Q: question`` followed by ``A: answer`` (answer may span lines).
    """
    cards: list[Card] = []
    q: str | None = None
    a: list[str] = []

    def flush() -> None:
        nonlocal q, a
        if q and a:
            cards.append(Card(q, "\n".join(a).strip(), deck))
        q, a = None, []

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(("Q:", "S:")):
            flush()
            q = line[2:].strip()
        elif line.startswith(("A:", "C:")) and q is not None:
            a = [line[2:].strip()]
        elif " :: " in line and not line.startswith("#"):
            flush()
            f, b = line.split(" :: ", 1)
            if f.strip() and b.strip():
                cards.append(Card(f.strip(), b.strip(), deck))
        elif a and line:
            a.append(line)
        elif not line:
            flush()
    flush()
    return cards


def parse_deck(filename: str, text: str, deck: str | None = None) -> list[Card]:
    name = deck or filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if filename.lower().endswith((".md", ".markdown", ".txt")):
        return parse_markdown(text, name)
    return parse_csv(text, name)
