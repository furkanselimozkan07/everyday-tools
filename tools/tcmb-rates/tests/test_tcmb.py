import sys
import urllib.error
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tcmb_rates import cli, fetch  # noqa: E402
from tcmb_rates.core import (convert, format_number, parse_number, parse_xml,  # noqa: E402
                             url_for)

XML = (Path(__file__).parent / "sample.xml").read_bytes()


def test_parse():
    d, rates = parse_xml(XML)
    assert d == date(2026, 11, 11)
    assert rates["USD"].forex_selling == Decimal("50.2282")
    assert rates["XDR"].forex_selling is None
    assert rates["TRY"].per_unit() == 1


def test_unit_and_fallback():
    _, rates = parse_xml(XML)
    assert rates["JPY"].per_unit("forex_buying") == Decimal("31.4666") / 100
    assert rates["XDR"].per_unit() == Decimal("67.8422")


def test_convert():
    _, rates = parse_xml(XML)
    assert convert(Decimal(100), "usd", "TRY", rates) == Decimal("5022.82")
    eur = convert(Decimal(1), "USD", "EUR", rates)
    assert Decimal("0.5") < eur < Decimal("1.5")
    with pytest.raises(KeyError):
        convert(Decimal(1), "XXX", "TRY", rates)


def test_numbers():
    assert parse_number("1.250,75") == Decimal("1250.75")
    assert parse_number("1250.75") == Decimal("1250.75")
    assert parse_number("1.000") == 1000
    assert parse_number("1.234.567") == 1234567
    assert parse_number("0.500") == Decimal("0.5")
    assert parse_number("1,5") == Decimal("1.5")
    with pytest.raises(ValueError):
        parse_number("abc")
    assert format_number(Decimal("1250.75")) == "1.250,75"


def test_url():
    assert url_for() .endswith("/today.xml")
    assert url_for(date(2026, 11, 3)).endswith("/202611/03112026.xml")


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("TCMB_CACHE", str(tmp_path))
    return tmp_path


def test_weekend_falls_back_and_caches(cache):
    calls = []

    def dl(url):
        calls.append(url)
        if "09112026" in url or "08112026" in url:  # Sun / Sat -> no bulletin
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        return XML

    d, rates = fetch.load(date(2026, 11, 8), downloader=dl)
    assert "USD" in rates
    n = len(calls)
    fetch.load(date(2026, 11, 8), downloader=dl)  # cached now
    assert len(calls) == n


def test_offline_missing(cache):
    with pytest.raises(LookupError):
        fetch.load(offline=True)


def test_network_down_uses_stale_cache(cache):
    (cache / "today.xml").write_bytes(XML)
    import os
    os.utime(cache / "today.xml", (0, 0))

    def dl(url):
        raise urllib.error.URLError("down")

    assert "USD" in fetch.load(downloader=dl)[1]


def test_cli(cache, capsys):
    (cache / "today.xml").write_bytes(XML)
    assert cli.main(["--offline", "convert", "100", "USD", "TRY"]) == 0
    assert "5.022,82 TRY" in capsys.readouterr().out
    assert cli.main(["--offline", "list", "usd", "jpy"]) == 0
    assert "JAPON" in capsys.readouterr().out
    assert cli.main(["--offline", "get", "XDR"]) == 0
    assert cli.main(["--offline", "get", "ZZZ"]) == 2
