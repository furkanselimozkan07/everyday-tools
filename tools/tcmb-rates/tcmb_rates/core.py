"""Pure logic: parse TCMB XML, convert amounts, format numbers (no network)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

BASE_URL = "https://www.tcmb.gov.tr/kurlar"
KINDS = ("forex_buying", "forex_selling", "banknote_buying", "banknote_selling")


@dataclass(frozen=True)
class Rate:
    code: str
    name: str
    unit: int
    forex_buying: Decimal | None
    forex_selling: Decimal | None
    banknote_buying: Decimal | None
    banknote_selling: Decimal | None

    def per_unit(self, kind: str = "forex_selling") -> Decimal:
        """TRY value of ONE unit of this currency (TCMB quotes e.g. JPY per 100)."""
        if kind not in KINDS:
            raise ValueError(f"unknown rate kind: {kind}")
        value = getattr(self, kind)
        if value is None:  # e.g. XDR only has a buying rate
            value = self.forex_buying or self.forex_selling
        if value is None:
            raise ValueError(f"{self.code} has no usable rate")
        return value / self.unit


def url_for(day: date | None = None) -> str:
    """today.xml, or the archive URL for a given day."""
    if day is None:
        return f"{BASE_URL}/today.xml"
    return f"{BASE_URL}/{day:%Y%m}/{day:%d%m%Y}.xml"


def _dec(text: str | None) -> Decimal | None:
    if text is None or not text.strip():
        return None
    try:
        return Decimal(text.strip())
    except InvalidOperation:
        return None


def parse_xml(data: str | bytes) -> tuple[date, dict[str, Rate]]:
    """Parse a TCMB bulletin into (bulletin date, {CODE: Rate}). TRY is added as 1:1."""
    root = ET.fromstring(data)
    d, m, y = root.attrib["Tarih"].split(".")
    bulletin = date(int(y), int(m), int(d))
    rates: dict[str, Rate] = {
        "TRY": Rate("TRY", "TÜRK LİRASI", 1, *(Decimal(1),) * 4)
    }
    for cur in root.iter("Currency"):
        code = cur.attrib["Kod"].upper()
        get = lambda tag: _dec(cur.findtext(tag))  # noqa: E731
        rates[code] = Rate(
            code=code,
            name=(cur.findtext("Isim") or code).strip(),
            unit=int(cur.findtext("Unit") or 1),
            forex_buying=get("ForexBuying"),
            forex_selling=get("ForexSelling"),
            banknote_buying=get("BanknoteBuying"),
            banknote_selling=get("BanknoteSelling"),
        )
    return bulletin, rates


def convert(amount: Decimal, src: str, dst: str, rates: dict[str, Rate],
            kind: str = "forex_selling") -> Decimal:
    """Convert via TRY. Selling rate is what a bank charges you to buy foreign currency."""
    src, dst = src.upper(), dst.upper()
    for code in (src, dst):
        if code not in rates:
            raise KeyError(f"unknown currency: {code}")
    return amount * rates[src].per_unit(kind) / rates[dst].per_unit(kind)


def parse_number(text: str) -> Decimal:
    """Accept '1.250,75' (Turkish), '1250.75', '1,5' and '1.000' (= one thousand)."""
    t = text.strip().replace(" ", "")
    if re.fullmatch(r"[1-9]\d{0,2}(\.\d{3})+", t):  # dots only as thousand separators
        t = t.replace(".", "")
    elif "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        raise ValueError(f"not a number: {text!r}") from None


def format_number(value: Decimal, places: int = 2) -> str:
    """Turkish formatting: 1.250,75"""
    s = f"{value:,.{places}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def previous_days(day: date, count: int = 7):
    """Yield day, day-1, ... (bulletins don't exist on weekends/holidays)."""
    for i in range(count):
        yield day - timedelta(days=i)
