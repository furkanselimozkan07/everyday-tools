# tcmb-rates

Exchange rates from the Turkish central bank (TCMB, `today.xml` and the
dated archive) in your terminal. Pure standard library, Python 3.10+.
Rates are parsed with `Decimal`, cached on disk and work offline afterwards.
Inspired by the CLI ergonomics of [`forex-python`](https://github.com/MicroPyramid/forex-python)
(simple `convert` command), but written from scratch for TCMB data.

## Usage
```bash
cd tools/tcmb-rates
python -m tcmb_rates list                  # all currencies vs ₺
python -m tcmb_rates list USD EUR GBP
python -m tcmb_rates get USD               # all four rate kinds
python -m tcmb_rates convert 1.250,50 USD TRY
python -m tcmb_rates convert 100 EUR USD   # cross rate via TRY
python -m tcmb_rates --date 2026-11-08 get USD   # weekend -> last bulletin before it
python -m tcmb_rates --kind banknote_buying convert 100 USD TRY
python -m tcmb_rates --offline list        # cache only
```
```
$ python -m tcmb_rates convert 1.000 USD EUR
1.000,00 USD = 897,24 EUR  (2026-11-11)
```
Notes:
- Default rate is `forex_selling`; choose with `--kind` (`forex_buying`, `banknote_buying`, `banknote_selling`).
- Units are normalised (TCMB quotes JPY per 100).
- Numbers accept Turkish (`1.250,75`), plain (`1250.75`) and `1.000` (= one thousand).
- Cache: `~/.cache/tcmb-rates` (override with `TCMB_CACHE`). `today.xml` is refreshed once a day; if the network is down the stale cache is used.

## Tests
```bash
pip install pytest && python -m pytest   # no network needed
```
