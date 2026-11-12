"""python -m tcmb_rates {list,get,convert}"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .core import KINDS, convert, format_number, parse_number
from .fetch import load


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tcmb-rates", description="TCMB exchange rates.")
    p.add_argument("--date", type=date.fromisoformat, help="YYYY-MM-DD (default: latest)")
    p.add_argument("--offline", action="store_true", help="use cache only")
    p.add_argument("--kind", choices=KINDS, default="forex_selling",
                   help="rate to use (default forex_selling)")
    sub = p.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="show all rates against TRY")
    ls.add_argument("codes", nargs="*", help="only these currencies")
    g = sub.add_parser("get", help="rate of one currency")
    g.add_argument("code")
    c = sub.add_parser("convert", help="convert AMOUNT FROM TO, e.g. convert 100 USD TRY")
    c.add_argument("amount")
    c.add_argument("src")
    c.add_argument("dst")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bulletin, rates = load(args.date, offline=args.offline)
    except (OSError, LookupError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    try:
        if args.cmd == "list":
            codes = [c.upper() for c in args.codes] or sorted(rates)
            print(f"TCMB bulletin {bulletin.isoformat()} ({args.kind})")
            for code in codes:
                r = rates[code]
                print(f"  {code}  {format_number(r.per_unit(args.kind), 4):>10} ₺  {r.name}")
        elif args.cmd == "get":
            code = args.code.upper()
            if code not in rates:
                raise KeyError(f"unknown currency: {code}")
            r = rates[code]
            print(f"{code} – {r.name} (per {r.unit}) – {bulletin.isoformat()}")
            for k in KINDS:
                v = getattr(r, k)
                print(f"  {k:<16} {format_number(v, 4) if v is not None else '-'}")
        else:
            out = convert(parse_number(args.amount), args.src, args.dst, rates, args.kind)
            print(f"{format_number(parse_number(args.amount))} {args.src.upper()} = "
                  f"{format_number(out)} {args.dst.upper()}  ({bulletin.isoformat()})")
    except (KeyError, ValueError) as e:
        print(f"error: {e.args[0] if isinstance(e, KeyError) else e}", file=sys.stderr)
        return 2
    return 0
