import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import json, statistics as st, sys, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from items import ITEMS, ORDER, EXCLUDED

LIFT = sys.argv[1] if len(sys.argv) > 1 else 'itemlift4.json'
SLOPE = 0.0125   # win-rate points per gold (card tier curve: Tier II to V is about +0.29 over ~21 gold)
o = json.load(open(LIFT)); lift = {k: (m, se) for k, m, se in json.load(open('itemlift3.json'))['lift']}
lift.update({k: (m, se) for k, m, se in o['lift']})
MANUAL = {'GOLD_BOW': 12, 'RED_SCALE': 8, 'AMULET_COIN': 12, 'FIRE_SHARD': 3, 'OLD_AMBER': 2, 'FOSSIL_GEM': 2, 'ARTIFICIAL_GEM': 2}
SKIP_NOTE = {'OLD_AMBER': 'Not simulated: too few Fossil families; priced by hand.', 'FOSSIL_GEM': 'Not simulated: priced by hand.', 'ARTIFICIAL_GEM': 'Not simulated: needs items; priced by hand.', 'GOLD_BOW': 'Not simulated: holder is an extra lineup slot.', 'RED_SCALE': 'Not simulated: +1 gold income per round.',
             'AMULET_COIN': 'Not simulated: +1 gold per KO.',
             'FIRE_SHARD': 'Not simulated: costs 2 points, permanent +1 ATK +1 speed on a Fire Pokemon.'}
# empirical-Bayes shrink toward the category mean
bycat = collections.defaultdict(list)
for k, (m, se) in list(lift.items()): bycat[ITEMS[k]['cat']].append((m, se))
prior = {}
for c, l in bycat.items():
    mu = st.mean(m for m, s in l); var = st.pvariance([m for m, s in l]) if len(l) > 1 else .0004
    tau2 = max(var - st.mean(s * s for m, s in l), 1e-4); prior[c] = (mu, tau2)
def shrunk(k):
    m, se = lift[k]; mu, t2 = prior[ITEMS[k]['cat']]; w = t2 / (t2 + se * se); return mu + w * (m - mu)
def tier(p): return 'I' if p <= 2 else 'II' if p <= 4 else 'III' if p <= 7 else 'IV' if p <= 13 else 'V'
def copies(p): return 6 if p <= 2 else 4 if p <= 4 else 3 if p <= 7 else 2 if p <= 13 else 1
SK = dict(hp='HP', atk='ATK', df='DEF', sdf='SP.DEF', spd='SPEED', ap='AP', ch='start charge', sh='shield', crit="crit tokens")
lift['GOLDEN_RAZZ_BERRY'] = lift['GOLDEN_NANAB_BERRY']
rows = []
for k in ORDER:
    it = ITEMS[k]
    if k in MANUAL: p = MANUAL[k]; l = ''
    else: p = max(1, round(shrunk(k) / SLOPE)); l = round(lift[k][0] * 100, 1)
    if k == 'GOLD_BOTTLE_CAP': p = max(p, 6)
    note = SKIP_NOTE.get(k, '')
    if it['flags'].get('food'): note = (note + ' Used up after the battle.').strip()
    if it['flags'].get('perm'): note = (note + ' Used up when given.').strip()
    if it['flags'].get('econ_gold') or it['flags'].get('econ_ko'): note = (note + ' Gold part not simulated.').strip()
    stats = ', '.join(f"{SK[a]} {v:+g}" for a, v in it['stats'].items())
    rows.append([tier(p), p, copies(p), it['name'], it['cat'], it['text'], stats, l, note])
order = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4}
rows.sort(key=lambda r: (order[r[0]], r[1], r[4], r[3]))
CORE = {'Component', 'Stone', 'Crafted', 'Tool', 'Gem'}
SHINY = {'Dynamax Band', 'Shiny Stone', 'Eviolite', 'Gold Mask', 'Gold Bottle Cap', 'Absorb Bulb', 'Sacred Ash', 'Star Piece', 'Gold Bow', 'Red Scale', 'Rare Candy'}
COPIES = {'Component': 4, 'Crafted': 2, 'Stone': 2, 'Tool': 1, 'Gem': 1}   # halved print run
for r in rows:
    r[2] = 1 if r[3] in SHINY else COPIES.get(r[4], r[2])
for r in rows:
    if r[3] in SHINY: r[4] = 'Shiny'
CORE = CORE | {'Shiny'}
EXTRA = ['Amulet Coin']
core_rows = [r for r in rows if r[4] in CORE]
extra_rows = [r for r in rows if r[3] in EXTRA]
wb = Workbook()
def sheet(ws, head, data, widths):
    ws.append(head)
    for c in ws[1]: c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='305496')
    for r in data: ws.append(r)
    for i, w in enumerate(widths): ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
H = ['Tier', 'Price', 'Copies', 'Item', 'Category', 'Effect (draft)', 'Stat bonuses', 'Measured lift (win pts)', 'Note']
W = [6, 6, 7, 22, 13, 80, 28, 11, 34]
sheet(wb.active, H, core_rows, W); wb.active.title = 'Items'
sheet(wb.create_sheet('Suggested extras'), H, extra_rows, W)
sheet(wb.create_sheet('Full list (reference)'), H, rows, W)
RULES = [
 ('Slots', 'Each Pokemon holds up to 3 items. Items are attached and removed freely between rounds (free, simultaneous). Fainted Pokemon keep their items.'),
 ('Shop', 'Items are bought with gold from the shared shop. Item tiers use the same level gates as cards (II from level 3, III from 4, IV from 5, V from 6). The item market always shows 2 items of each item tier, drawn from that tier\'s item deck; same worst-first buying order. A player who passes cannot buy for the rest of the round.'),
 ('Copies', 'Print run: Components 4 copies each, Crafted 2, Synergy stones 2, Tools 1, Synergy gems 1, Shiny items 1 (212 cards).'),
 ('Trade-in', 'Items cannot be sold for coins; like cards, an item can be traded in as payment for a new item or card.'),
 ('Pricing', 'Price = measured win-rate lift of the item on a random Pokemon (paired duels, same lineups with and without the item) divided by 1 win-rate point per gold, then shrunk toward its category average. 1 point per gold comes from the card tier curve. Items that need a matching type (stones, tools, gems) were measured only in lineups that already had 1-3 cards of that type.'),
 ('Battle timing', 'Everything on both sides is revealed at battle start, so items are public. Item bonuses apply when the holder enters; "own turn" counts mean that Pokemon\'s own turns after entering.'),
 ('Types from items', 'Stones and tools give the holder an extra type: it counts toward your synergy level for the whole battle (fixed) and the holder gets that synergy\'s bonuses. Gems add +1 to a synergy count without making the holder that type.'),
 ('Berries', 'Reusable: each berry triggers once per battle and is back next battle. (Variant for later: make them single use.)'),
 ('Food', 'Used up after one battle. A cheap gold sink that gives a one-battle bonus.'),
 ('Permanent', 'Sweets and milk are used up when given and change a Pokemon\'s stats for the rest of the game; they stay on the card if you trade it in.'),
 ('TMs', 'Replace the holder\'s charge power with the TM move (scaled by the holder\'s star level). One TM per Pokemon.'),
 ('Weather rocks', 'Whole-lineup effects, active if any Pokemon in your lineup holds the rock; the same effect does not stack with a second rock.'),
 ('Stacking', 'Numeric item effects add up when a Pokemon holds several; unique effects (revive, once-per-battle triggers) happen once per Pokemon.'),
 ('No duplicates', 'A Pokemon cannot hold two of the same item.'),
 ('Pick bundles', 'Additional picks (I-IV) deal each Pokemon with a random item of the same tier (any item, gems too). Unchosen starter items are discarded; other unchosen items go to the bottom of the item deck. Unique and Legendary picks deal no items.'),
 ('Wonder Box', 'At battle start the holder borrows the top Tier III and Tier II items (max 3 held; Tier II only if there is room); they return to the bottom of their decks after the battle.'),
 ('Not simulated', 'Gold Bow, Red Scale, Amulet Coin, Fire Shard and the gold parts of Nanab/Golden berries and Payday/Gold Bottle Cap are priced by hand until the economy simulator exists.'),
]
sheet(wb.create_sheet('Item rules'), ['Topic', 'Rule (draft)'], RULES, [18, 120])
sheet(wb.create_sheet('Excluded'), ['PAC items left out', 'Why'], EXCLUDED, [90, 70])
cnt = collections.Counter((r[0], r[4]) for r in rows)
cats = sorted({r[4] for r in rows})
summ = [[c] + [cnt[(t, c)] for t in 'I II III IV V'.split()] + [sum(cnt[(t, c)] for t in 'I II III IV V'.split())] for c in cats]
summ.append(['Total'] + [sum(1 for r in rows if r[0] == t) for t in 'I II III IV V'.split()] + [len(rows)])
sheet(wb.create_sheet('Counts'), ['Category', 'I', 'II', 'III', 'IV', 'V', 'Total'], summ, [18, 6, 6, 6, 6, 6, 8])
wb.save(f'{ROOT}/pac-items-core.xlsx'); print(len(core_rows), 'core;', len(extra_rows), 'extras')
import csv
with open(f'{ROOT}/items_core.json', 'w') as fh: json.dump(dict(core=core_rows, extra=extra_rows), fh)
print(len(rows), 'items'); print(summ[-1])
