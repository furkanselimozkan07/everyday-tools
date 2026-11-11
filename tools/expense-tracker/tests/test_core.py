from datetime import date

import pytest

from expense_tracker.core import Store, budget_report, format_try, parse_amount, summarize


@pytest.mark.parametrize("text,expected", [
    ("125,50", 12550), ("1.250,75", 125075), ("12.5", 1250), ("₺40", 4000), ("7 TL", 700),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "nan", ""])
def test_parse_amount_invalid(bad):
    with pytest.raises(ValueError):
        parse_amount(bad)


def test_format_try():
    assert format_try(125050) == "1.250,50 ₺"
    assert format_try(5) == "0,05 ₺"
    assert format_try(-100) == "-1,00 ₺"


def test_store_add_list_filter_delete():
    s = Store()
    a = s.add(1000, "Yemek", date(2026, 11, 3), "öğle")
    s.add(2000, "ulaşım", date(2026, 10, 30))
    assert len(s.list()) == 2
    assert [e.id for e in s.list(month="2026-11")] == [a]
    assert s.list(category="YEMEK")[0].note == "öğle"
    assert s.delete(a) and not s.delete(a)


def test_summary_and_budget():
    s = Store()
    s.add(1000, "yemek", date(2026, 11, 1))
    s.add(500, "yemek", date(2026, 11, 2))
    s.add(3000, "kitap", date(2026, 11, 2))
    totals = summarize(s.list(month="2026-11"))
    assert list(totals) == ["kitap", "yemek"]
    s.set_budget("yemek", 1000)
    s.set_budget("yemek", 1200)  # upsert
    assert budget_report(totals, s.budgets()) == [("yemek", 1500, 1200, -300)]


def test_csv_export():
    s = Store()
    s.add(12550, "yemek", date(2026, 11, 1), "a, b")
    out = s.to_csv(s.list())
    assert out.splitlines()[0] == "id,date,amount_try,category,note"
    assert '1,2026-11-01,125.50,yemek,"a, b"' in out
