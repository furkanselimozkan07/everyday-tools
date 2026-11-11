import io

from expense_tracker.cli import main


def run(db, *argv):
    buf = io.StringIO()
    code = main(["--db", str(db), *argv], out=buf)
    return code, buf.getvalue()


def test_cli_flow(tmp_path):
    db = tmp_path / "t.db"
    assert run(db, "add", "125,50", "yemek", "pizza", "--date", "2026-11-05")[0] == 0
    run(db, "budget", "yemek", "100")
    code, out = run(db, "summary", "--month", "2026-11")
    assert code == 0 and "125,50 ₺" in out and "OVER" in out
    assert "pizza" in run(db, "list")[1]
    assert "125.50" in run(db, "export")[1]
    assert run(db, "delete", "1")[0] == 0
    assert run(db, "delete", "1")[0] == 1


def test_cli_bad_amount(tmp_path):
    assert run(tmp_path / "t.db", "add", "abc", "x")[0] == 2
