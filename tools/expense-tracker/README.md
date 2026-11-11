# expense-tracker

A tiny offline expense tracker for the terminal. Amounts are in Turkish lira
(₺) and stored as integer kuruş in a local SQLite file, so there are no
floating-point errors. No dependencies beyond Python 3.10+.

## Usage
```bash
cd tools/expense-tracker
python -m expense_tracker add 125,50 yemek "pizza"       # Turkish number format works
python -m expense_tracker add 1.250,75 kira --date 2026-11-01
python -m expense_tracker list --month 2026-11
python -m expense_tracker budget yemek 3000               # monthly budget
python -m expense_tracker summary                          # current month + budget status
python -m expense_tracker export --month 2026-11 > nov.csv
python -m expense_tracker delete 3
```
Example summary:
```
Summary for 2026-11
  kira           1.250,75 ₺
  yemek            125,50 ₺
  TOTAL          1.376,25 ₺
  budget yemek: 125,50 ₺ / 3.000,00 ₺ (ok, left 2.874,50 ₺)
```
The database lives in `~/.expense_tracker.db`; override with `--db` or `EXPENSE_DB`.

## Tests
```bash
pip install pytest && python -m pytest
```

## Layout
`core.py` holds storage and pure aggregation logic; `cli.py` is the argparse front end.
