from datetime import date, timedelta

import pytest

from flashcards import store
from flashcards.cli import main, review
from flashcards.core import Card, parse_csv, parse_deck, parse_markdown, sm2

T = date(2026, 11, 25)


def test_sm2_interval_progression():
    c = Card("a", "b")
    c = sm2(c, 4, T)
    assert (c.interval, c.reps, c.due) == (1, 1, T + timedelta(days=1))
    c = sm2(c, 4, T)
    assert c.interval == 6
    c = sm2(c, 4, T)
    assert c.interval == round(6 * c.ease) and c.reps == 3


def test_sm2_ease_changes():
    assert sm2(Card("a", "b"), 5, T).ease == pytest.approx(2.6)
    assert sm2(Card("a", "b"), 4, T).ease == pytest.approx(2.5)
    assert sm2(Card("a", "b", ease=1.3), 0, T).ease == 1.3  # floor


def test_sm2_lapse_resets():
    c = Card("a", "b", ease=2.5, interval=30, reps=5)
    n = sm2(c, 1, T)
    assert n.reps == 0 and n.interval == 1 and n.lapses == 1


def test_sm2_invalid():
    with pytest.raises(ValueError):
        sm2(Card("a", "b"), 6, T)


def test_parse_csv_header_and_semicolon():
    cards = parse_csv("Front;Back\nkedi;cat\nköpek;dog\n", "tr")
    assert [(c.front, c.back) for c in cards] == [("kedi", "cat"), ("köpek", "dog")]
    assert cards[0].deck == "tr"


def test_parse_markdown_mixed():
    text = "Q: a?\nA: line1\nline2\n\nx :: y\n# h :: skip\n"
    cards = parse_markdown(text)
    assert cards[0].back == "line1\nline2"
    assert (cards[1].front, cards[1].back) == ("x", "y")
    assert len(cards) == 2


def test_parse_deck_name_from_file():
    assert parse_deck("dir/bio.md", "a :: b")[0].deck == "bio"
    assert parse_deck("x.csv", "a,b", "custom")[0].deck == "custom"


def test_store_roundtrip_and_upsert():
    con = store.connect(":memory:")
    assert store.add_cards(con, [Card("q", "a")], T) == (1, 0)
    assert store.add_cards(con, [Card("q", "a2"), Card("r", "s")], T) == (1, 1)
    cards = store.due_cards(con, T)
    assert len(cards) == 2 and cards[0].back == "a2"
    store.save_review(con, sm2(cards[0], 4, T))
    assert len(store.due_cards(con, T)) == 1
    assert len(store.due_cards(con, T + timedelta(days=1))) == 2
    s = store.stats(con, T)[0]
    assert s["total"] == 2 and s["due"] == 1 and s["new"] == 1
    assert store.delete_deck(con, "default") == 2


def test_review_session_scripted():
    con = store.connect(":memory:")
    store.add_cards(con, [Card("q1", "a1"), Card("q2", "a2")], T)
    inputs = iter(["", "x", "3", "", "q"])
    out: list[str] = []
    review(con, None, 20, False, T, inp=lambda _="": next(inputs), out=out.append)
    assert len(store.due_cards(con, T)) == 1
    assert any("next review in 1 day" in l for l in out)


def test_cli_import_and_stats(tmp_path, capsys):
    db = str(tmp_path / "c.db")
    f = tmp_path / "deck.md"
    f.write_text("a :: b\nc :: d\n", encoding="utf-8")
    assert main(["--db", db, "import", str(f)]) == 0
    assert "2 added" in capsys.readouterr().out
    assert main(["--db", db, "due"]) == 0
    assert capsys.readouterr().out.strip() == "2"
    assert main(["--db", db, "stats"]) == 0
    assert "deck" in capsys.readouterr().out
    assert main(["--db", db, "import", str(tmp_path / "nope.csv")]) == 1
