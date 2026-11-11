"""Storage and pure aggregation logic (no printing, easy to test)."""
from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    amount_kurus INTEGER NOT NULL,
    category TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    monthly_kurus INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class Expense:
    id: int
    day: date
    amount_kurus: int
    category: str
    note: str

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_kurus) / 100


def parse_amount(text: str) -> int:
    """Parse '125,50', '1.250,75' or '12.5' into kuruş (integer). Must be > 0."""
    s = text.strip().replace("₺", "").replace("TL", "").replace(" ", "")
    if "," in s:  # Turkish format: '.' thousands, ',' decimal
        s = s.replace(".", "").replace(",", ".")
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"invalid amount: {text!r}") from None
    if not value.is_finite() or value <= 0:
        raise ValueError(f"amount must be positive: {text!r}")
    return int((value * 100).to_integral_value())


def format_try(kurus: int) -> str:
    """Format kuruş as Turkish lira, e.g. 125050 -> '1.250,50 ₺'."""
    sign = "-" if kurus < 0 else ""
    lira, k = divmod(abs(kurus), 100)
    return f"{sign}{lira:,}".replace(",", ".") + f",{k:02d} ₺"


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def summarize(expenses: list[Expense]) -> dict[str, int]:
    """Total kuruş per category, largest first."""
    totals: dict[str, int] = {}
    for e in expenses:
        totals[e.category] = totals.get(e.category, 0) + e.amount_kurus
    return dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))


def budget_report(totals: dict[str, int], budgets: dict[str, int]) -> list[tuple[str, int, int, int]]:
    """Rows of (category, spent, limit, remaining) for every budgeted category."""
    return [(c, totals.get(c, 0), lim, lim - totals.get(c, 0)) for c, lim in sorted(budgets.items())]


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def add(self, amount_kurus: int, category: str, day: date | None = None, note: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO expenses(day, amount_kurus, category, note) VALUES (?,?,?,?)",
            ((day or date.today()).isoformat(), amount_kurus, category.strip().lower(), note),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def delete(self, expense_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def list(self, month: str | None = None, category: str | None = None) -> list[Expense]:
        sql, args = "SELECT id, day, amount_kurus, category, note FROM expenses WHERE 1=1", []
        if month:
            sql += " AND substr(day,1,7)=?"
            args.append(month)
        if category:
            sql += " AND category=?"
            args.append(category.strip().lower())
        sql += " ORDER BY day, id"
        return [Expense(i, date.fromisoformat(d), a, c, n) for i, d, a, c, n in self.conn.execute(sql, args)]

    def set_budget(self, category: str, monthly_kurus: int) -> None:
        self.conn.execute(
            "INSERT INTO budgets VALUES (?,?) ON CONFLICT(category) DO UPDATE SET monthly_kurus=excluded.monthly_kurus",
            (category.strip().lower(), monthly_kurus),
        )
        self.conn.commit()

    def budgets(self) -> dict[str, int]:
        return dict(self.conn.execute("SELECT category, monthly_kurus FROM budgets"))

    def to_csv(self, expenses: list[Expense]) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "date", "amount_try", "category", "note"])
        for e in expenses:
            w.writerow([e.id, e.day.isoformat(), f"{e.amount:.2f}", e.category, e.note])
        return buf.getvalue()
