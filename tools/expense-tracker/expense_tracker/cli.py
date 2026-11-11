"""Command line interface: python -m expense_tracker <command>."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .core import Store, budget_report, format_try, month_key, parse_amount, summarize


def default_db() -> Path:
    return Path(os.environ.get("EXPENSE_DB", Path.home() / ".expense_tracker.db"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="expense-tracker", description="Track your spending in TL.")
    p.add_argument("--db", type=Path, default=None, help="database file (env EXPENSE_DB)")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add an expense")
    a.add_argument("amount", help="e.g. 125,50 or 1.250,75")
    a.add_argument("category")
    a.add_argument("note", nargs="?", default="")
    a.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default today)")

    ls = sub.add_parser("list", help="list expenses")
    ls.add_argument("--month", help="YYYY-MM")
    ls.add_argument("--category")

    d = sub.add_parser("delete", help="delete an expense by id")
    d.add_argument("id", type=int)

    s = sub.add_parser("summary", help="per-category totals and budget status")
    s.add_argument("--month", default=month_key(date.today()), help="YYYY-MM (default current)")

    b = sub.add_parser("budget", help="set a monthly budget for a category")
    b.add_argument("category")
    b.add_argument("amount")

    e = sub.add_parser("export", help="export expenses as CSV to stdout")
    e.add_argument("--month")
    return p


def main(argv: list[str] | None = None, out=None) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    store = Store(args.db or default_db())

    try:
        if args.cmd == "add":
            eid = store.add(parse_amount(args.amount), args.category, args.date, args.note)
            print(f"Added #{eid}: {format_try(parse_amount(args.amount))} [{args.category.lower()}]", file=out)
        elif args.cmd == "list":
            for x in store.list(args.month, args.category):
                print(f"#{x.id:<4} {x.day}  {format_try(x.amount_kurus):>14}  {x.category:<12} {x.note}", file=out)
        elif args.cmd == "delete":
            ok = store.delete(args.id)
            print("Deleted." if ok else "No such id.", file=out)
            return 0 if ok else 1
        elif args.cmd == "summary":
            totals = summarize(store.list(args.month))
            print(f"Summary for {args.month}", file=out)
            for cat, v in totals.items():
                print(f"  {cat:<14}{format_try(v):>16}", file=out)
            print(f"  {'TOTAL':<14}{format_try(sum(totals.values())):>16}", file=out)
            for cat, spent, lim, rem in budget_report(totals, store.budgets()):
                flag = "OVER" if rem < 0 else "ok"
                print(f"  budget {cat}: {format_try(spent)} / {format_try(lim)} ({flag}, left {format_try(rem)})", file=out)
        elif args.cmd == "budget":
            store.set_budget(args.category, parse_amount(args.amount))
            print(f"Budget for {args.category.lower()} set to {format_try(parse_amount(args.amount))}/month.", file=out)
        elif args.cmd == "export":
            out.write(store.to_csv(store.list(args.month)))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
