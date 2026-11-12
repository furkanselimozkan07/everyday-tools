"""Network + on-disk cache. Each bulletin is cached by its requested date."""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from .core import Rate, parse_xml, previous_days, url_for


def cache_dir() -> Path:
    base = os.environ.get("TCMB_CACHE") or Path.home() / ".cache" / "tcmb-rates"
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download(url: str, timeout: float = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "tcmb-rates/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load(day: date | None = None, offline: bool = False,
         downloader=_download) -> tuple[date, dict[str, Rate]]:
    """Rates for `day` (None = latest). For a past day without a bulletin
    (weekend/holiday) the most recent earlier bulletin is used."""
    cdir = cache_dir()
    today = date.today()
    candidates = previous_days(day or today, 7) if day else [None]
    for cand in candidates:
        key = "today" if cand is None else cand.isoformat()
        f = cdir / f"{key}.xml"
        # 'today' goes stale daily, so only trust it when it is fresh or offline.
        fresh = f.exists() and (offline or cand is not None or
                                date.fromtimestamp(f.stat().st_mtime) == today)
        if fresh:
            return parse_xml(f.read_bytes())
        if offline:
            continue
        try:
            data = downloader(url_for(cand))
        except urllib.error.HTTPError as e:
            if e.code == 404 and cand is not None:
                continue
            raise
        except urllib.error.URLError:
            if f.exists():  # network down: fall back to stale cache
                return parse_xml(f.read_bytes())
            raise
        parsed = parse_xml(data)
        f.write_bytes(data)
        if day and cand != day:  # remember the fallback under the requested date too
            (cdir / f"{day.isoformat()}.xml").write_bytes(data)
        return parsed
    raise LookupError("no bulletin found" + (" in cache" if offline else " for that period"))
