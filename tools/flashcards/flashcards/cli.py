"""python -m flashcards {import,add,review,due,stats,rm}"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import date
from pathlib import Path

from . import store
from .core import Card, parse_deck, sm2

GRADES = {"1": 1, "2": 3, "3": 4, "4": 5}  # again / hard / good / easy
HELP = "[1] again  [2] hard  [3] good  [4] easy  [q] quit"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flashcards", description="SM-2 spaced repetition.")
    p.add_argument("--db", help="database file (default $FLASHCARDS_DB or ~/.local/share/flashcards/cards.db)")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("import", help="import a .csv/.md/.txt deck")
    i.add_argument("file")
    i.add_argument("--deck", help="deck name (default: file name)")
    a = sub.add_parser("add", help="add a single card")
    a.add_argument("front")
    a.add_argument("back")
    a.add_argument("--deck", default="default")
    r = sub.add_parser("review", help="review due cards interactively")
    r.add_argument("--deck")
    r.add_argument("--limit", type=int, default=20)
    r.add_argument("--shuffle", action="store_true")
    d = sub.add_parser("due", help="count due cards")
    d.add_argument("--deck")
    sub.add_parser("stats", help="per-deck totals")
    rm = sub.add_parser("rm", help="delete a whole deck")
    rm.add_argument("deck")
    return p


def review(con, deck, limit, shuffle, today, inp=input, out=print) -> int:
    cards = store.due_cards(con, today, deck, limit)
    if shuffle:
        random.shuffle(cards)
    if not cards:
        out("Nothing due. 🎉")
        return 0
    done = 0
    for n, c in enumerate(cards, 1):
        out(f"\n[{n}/{len(cards)}] ({c.deck})  {c.front}")
        inp("  (Enter to show answer) ")
        out(f"  → {c.back}")
        while True:
            ans = inp(f"  {HELP}: ").strip().lower()
            if ans == "q":
                out(f"\nStopped. Reviewed {done} card(s).")
                return 0
            if ans in GRADES:
                break
        new = sm2(c, GRADES[ans], today)
        store.save_review(con, new)
        done += 1
        out(f"  next review in {new.interval} day(s) ({new.due.isoformat()})")
    out(f"\nDone! Reviewed {done} card(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    today = date.today()
    con = store.connect(args.db)
    try:
        if args.cmd == "import":
            path = Path(args.file)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            cards = parse_deck(path.name, text, args.deck)
            if not cards:
                print("error: no cards found in file", file=sys.stderr)
                return 1
            added, updated = store.add_cards(con, cards, today)
            print(f"{added} added, {updated} updated (deck '{cards[0].deck}')")
        elif args.cmd == "add":
            store.add_cards(con, [Card(args.front, args.back, args.deck)], today)
            print("added")
        elif args.cmd == "review":
            try:
                return review(con, args.deck, args.limit, args.shuffle, today)
            except (EOFError, KeyboardInterrupt):
                print("\nInterrupted; progress is saved.")
        elif args.cmd == "due":
            print(len(store.due_cards(con, today, args.deck)))
        elif args.cmd == "stats":
            rows = store.stats(con, today)
            if not rows:
                print("no cards yet")
            print(f"{'deck':<20}{'total':>6}{'due':>6}{'new':>6}{'mature':>8}")
            for r in rows:
                print(f"{r['deck']:<20}{r['total']:>6}{r['due']:>6}{r['new']:>6}{r['mature']:>8}")
        elif args.cmd == "rm":
            print(f"deleted {store.delete_deck(con, args.deck)} card(s)")
    finally:
        con.close()
    return 0
