# PAC tools: one source of truth for the website, the print run and the rulebook

```
python tools/setup.py          # once: fetches the PAC art + text (needs git)
python tools/sync.py           # rebuild EVERYTHING
python tools/sync.py print --print-out "C:/.../PAC Board Game v2 (bball stars)"   # + copy PDFs/xlsx there
python tools/sync.py data site # only refresh the website data (js/data.js)
python tools/sync.py check     # JS engine vs Python sim parity (needs node); should say "bad 0"
```
Needs Python 3.10+ with `openpyxl pillow playwright` (`pip install openpyxl pillow playwright && playwright install chromium`).
Everything is relative to this folder, so the repo can live anywhere. The website is the repo root (`index.html`, `js/`, `css/`).

## Where to change things
| Change | Edit | Then run |
|---|---|---|
| Item text, price/tier, copies | `pac-sim/items.py` (+ `itemfx.py` for behaviour) | `sync.py` |
| Pokémon card text/stats | `pac-core-cards-draft.xlsx` (Cards sheet), `pac-data/tweaks*.json` | `sync.py` |
| Duel / synergy rules | `pac-sim/engine.py`, `duel.py`, `itemfx.py` AND the JS port `js/engine.js` | `sync.py check` must stay at bad 0 |
| Prices (Unique/Legendary 12/25, price boxes) | `pac-digital/export_data.py` and `pac-print/build.py` (`cost_trade`) | `sync.py` |
| Reference-card wording | `pac-print/build2.py` | `sync.py print` |
| Rulebook wording | `rulebook/build_rulebook.py` (rules text) | `sync.py rulebook` |
| Game flow (picks, markets, bots) | `js/game.js`, `js/bots.js`; mirror the rule in the rulebook + reference cards | `sync.py` |

## What each step makes
- `items`  : `pac-items-core.xlsx`, `items_core.json` (from items.py + the measured lifts in `pac-sim/itemlift*.json`)
- `cards`  : `pac-pick-cards-draft.xlsx`, `pac-print/pool_cards.json`
- `data`   : `pac-digital/build/data.js|json` (every card and item, prices, texts)
- `site`   : copies data.js to `js/data.js`
- `print`  : `pac-print/out/PAC_*.pdf` (core, items, unique, legendary, additional, hatch, reference, synergies, each with _BACKS)
- `rulebook`: `rulebook/Pokémon Auto Chess Board Game — Draft Rulebook.pdf` (counts, prices, synergy and item tables come from the data)

Not rebuilt by sync (hand-made, rarely change): trackers and tokens (`pac-print/build4-7.py`; run them with `PAC_ROOT=tools python pac-print/build5.py`, then `render.py`).
The Python sim (`pac-sim/`) is the balance source of truth; the JS engine is a line-by-line port.
