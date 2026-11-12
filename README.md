# everyday-tools
Practical everyday tools for students: finance, study helpers, file and PDF utilities and more.
Each tool is self-contained in `tools/<name>/` (README, code, tests). See [ROADMAP.md](ROADMAP.md).

| Tool | Description | Status |
|------|-------------|--------|
| [expense-tracker](tools/expense-tracker) | SQLite-backed expense CLI with categories, monthly summaries, budgets and CSV export (₺) | v1 |
| [tcmb-rates](tools/tcmb-rates) | TCMB exchange-rate CLI: list, get, convert (Decimal, dated archive, offline cache) | v1 |

## Development
```bash
cd tools/<name> && pip install pytest && python -m pytest
```
CI runs the tests of every tool. License: MIT.
