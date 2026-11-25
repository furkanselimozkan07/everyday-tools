# flashcards

Spaced-repetition flashcards in your terminal, using the SM-2 algorithm
(the one behind early Anki/SuperMemo). Pure standard library, Python 3.10+,
progress stored in a local SQLite file. Deck import ideas (CSV and a simple
`front :: back` notation) are inspired by [Anki](https://apps.ankiweb.net/)'s
text import and [`mochi`](https://mochi.cards/)-style Markdown cards; the code is original.

## Usage
```bash
cd tools/flashcards
python -m flashcards import examples/ingilizce.csv
python -m flashcards import examples/veri-yapilari.md --deck veri
python -m flashcards add "TCP katmanı?" "Taşıma katmanı" --deck ag
python -m flashcards due            # how many cards are due today
python -m flashcards review --deck veri --limit 10 --shuffle
python -m flashcards stats
python -m flashcards rm veri
```
During `review` press Enter to reveal the answer, then grade:
`1` again, `2` hard, `3` good, `4` easy (`q` quits; progress is saved after every card).

## Deck formats
- **CSV** (`front,back`; `,` `;` or tab, optional header row such as `front,back` or `soru,cevap`).
- **Markdown/txt**: `front :: back` lines, or `Q:`/`A:` blocks (`S:`/`C:` for Turkish soru/cevap;
  answers may span several lines). Lines starting with `#` are ignored.

Re-importing a deck updates the back text of existing cards but keeps their schedule.
The deck name defaults to the file name.

## Scheduling
New cards are due immediately. Successful reviews: 1 day → 6 days → interval × ease.
A grade of "again" resets the card to 1 day and counts a lapse. Ease never drops below 1.3.

## Storage
`~/.local/share/flashcards/cards.db`; override with `--db` or `FLASHCARDS_DB`.

## Tests
```bash
pip install pytest && python -m pytest
```
