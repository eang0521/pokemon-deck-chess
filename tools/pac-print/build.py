import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re, json, os, html, sys, collections, openpyxl
sys.path.insert(0, f'{ROOT}/pac-print')
from custom_icons import SVG as CUSTOM

A = f'{ROOT}/keldaancommunity/pokemonautochess/app/public/src/assets'
W = f'{ROOT}/pac-print'
os.makedirs(W + '/out', exist_ok=True)
# write custom svgs to disk
for k, v in CUSTOM.items():
    if v: open(f'{W}/assets/{k}.svg', 'w').write(v)

def ic(name, cls='i'):
    """icon <img> by name"""
    p = None
    for cand in (f'{W}/assets/{name}.svg', f'{A}/icons/{name}.png', f'{A}/icons/{name}.svg', f'{A}/types/{name}.svg', f'{A}/ui/{name}.svg', f'{A}/ui/{name}.png'):
        if os.path.exists(cand): p = cand; break
    if p is None: raise KeyError(name)
    return f'<img class="{cls}" src="file://{p}">'

TIERCOL = {'UNIQUE': '#1f9d9a', 'LEGENDARY': '#c2392b', 'I': '#848b89', 'II': '#4f9d5d', 'III': '#3f79c6', 'IV': '#8a5bc8', 'V': '#d9a61e'}
TYPECOL = {'NORMAL': '#c9c3a8', 'GRASS': '#8ed06a', 'FIRE': '#f6a35b', 'WATER': '#78b8f0', 'ELECTRIC': '#f7d85a', 'FIGHTING': '#d9805a', 'PSYCHIC': '#f58fb8',
           'DARK': '#8b7f78', 'STEEL': '#b8c2cc', 'GROUND': '#d8c07a', 'POISON': '#c28ad8', 'DRAGON': '#8f8af2', 'FIELD': '#d8b878', 'MONSTER': '#a0b86a',
           'HUMAN': '#e8b9a0', 'AQUATIC': '#6fc9d8', 'BUG': '#b8d65a', 'FLYING': '#b8c6f5', 'FLORA': '#a0dc88', 'ROCK': '#cfc09a', 'GHOST': '#a591d0',
           'FAIRY': '#f7b6d8', 'ICE': '#bfeaf7', 'FOSSIL': '#d8b98a', 'SOUND': '#c8d8a0', 'ARTIFICIAL': '#b8c8d8', 'BABY': '#fbe3b8', 'LIGHT': '#fff2a8',
           'WILD': '#e8a870', 'AMORPHOUS': '#c8a8d8', 'GOURMET': '#f0c070'}

# ------------------------------------------------------------------ rich text
STAT = {'SP.DEF': 'SPE_DEF', 'DEF': 'DEF', 'ATK': 'ATK', 'SPEED': 'SPEED', 'SHIELD': 'SHIELD', 'HP': 'HP', 'AP': 'AP'}
STATUS = [(r'ARMOR BREAK', 'ARMOR_BREAK'), (r'FLY AWAY', 'fly_away'), (r'PARALY\w*', 'PARALYSIS'), (r'FLINCH\w*', 'FLINCH'), (r'BURN\w*', 'BURN'), (r'SLEEP\w*', 'SLEEP'),
          (r'CONFUS\w*', 'CONFUSION'), (r'CHARM\w*', 'CHARM'), (r'WOUND\w*', 'WOUND'), (r'FATIGUE\w*', 'FATIGUE'), (r'FREEZE\w*|FROZEN', 'FREEZE'), (r'PROTECT\w*', 'PROTECT'),
          (r'LOCK(?:ED)?\b', 'LOCKED'), (r'SILENCE\w*', 'SILENCE'), (r'POISON\w*', 'POISONED'), (r'CURSE\w*', 'CURSE'), (r'SWARM', 'SWARM'), (r'SPLASH', 'SPLASH'), (r'BATON', 'BATON')]
TYPEWORDS = ['PSYCHIC', 'GRASS', 'ELECTRIC', 'WATER', 'STEEL', 'GHOST', 'FLYING', 'FIRE', 'FAIRY', 'DARK', 'NORMAL', 'FIGHTING', 'ICE', 'ROCK', 'BUG']

def _tok(x):
    x = float(x); w = int(x)
    return ('½' if w == 0 else f'{w}½') if x - w >= .5 else str(w)

def crit_tokens(p):
    v = round(float(p) / 10) / 2
    return 0.5 if v < 1 else float(int(v))   # whole tokens (half only below 1); old crit % -> crit tokens per attack (1 token = 20%)

def crit_words(t):
    t = re.sub(r'\s*\(every \d+\w* attack crits\)', '', t)
    def rep(m):
        x = crit_tokens(m.group(2)); g = m.group(1) or ''
        body = 'a crit token every 2nd attack' if x == .5 else f"{_tok(x)} crit token{'' if x == 1 else 's'} per attack"
        if g: return g + body
        return ('gains ' if m.string[:m.start()].endswith('and ') else 'gain ') + body
    t = re.sub(r'(gain )?\+?(\d+)%\s*(?:\[?CRIT_CHANCE\]?\s*)?crit(?: chance)?', rep, t)
    t = re.sub(r'(^|\. )gain ', lambda m: m.group(1) + 'Gain ', t)
    return t

def rich(t):
    t = html.escape(crit_words(t))
    ph = []
    def hold(s):
        ph.append(s); return f'\x00{len(ph)-1}\x00'
    # AP-scaled numbers
    t = re.sub(r'✦/2\s*(\d+)', lambda m: hold(f'<span class="ap">{ic("AP","i ap")}<sub>/2</sub><b>+{m.group(1)}</b></span>'), t)
    t = re.sub(r'✦(\d+)', lambda m: hold(f'<span class="ap">{ic("AP","i ap")}<b>+{m.group(1)}</b></span>'), t)
    # damage types
    for w in ('SPECIAL', 'PHYSICAL', 'TRUE'):
        t = re.sub(rf'\b{w}\b', lambda m, w=w: hold(ic('ATK' if w == 'PHYSICAL' else w, 'i dm')), t)
    # statuses
    for pat, icon in STATUS:
        t = re.sub(rf'(?<![A-Za-z])({pat})(?![A-Za-z])', lambda m, icon=icon: hold(f'<span class="st">{ic(icon,"i")}<u>{m.group(1)}</u></span>'), t)
    # types
    for w in TYPEWORDS:
        t = re.sub(rf'(?<![A-Za-z]){w}(?![A-Za-z])', lambda m, w=w: hold(f'<span class="st">{ic(w,"i")}</span>'), t)
    # stats (number before -> icon only)
    for w in ('SP\\.DEF', 'DEF', 'ATK', 'SPEED', 'SHIELD', 'HP', 'AP'):
        key = w.replace('\\', '')
        t = re.sub(rf'(?<![A-Za-z✦]){w}(?![A-Za-z])', lambda m, key=key: hold(ic(STAT[key], 'i')), t)
    # lowercase stats (items)
    for w, icon in (('shield', 'SHIELD'), ('speed', 'SPEED'), ('charge', 'PP'), ('HP', 'HP')):
        t = re.sub(rf'(?<=\d)%?\s+{w}\b', lambda m, icon=icon: hold(('%' if '%' in m.group(0) else '') + ic(icon, 'i')), t)
    t = re.sub(r'(?<=\d)\s+charges?\b', lambda m: hold(ic('PP', 'i')), t)
    t = re.sub(r'\x00(\d+)\x00', lambda m: ph[int(m.group(1))], t)
    # replace held placeholders that were nested
    for _ in range(3): t = re.sub(r'\x00(\d+)\x00', lambda m: ph[int(m.group(1))], t)
    return t

CSS = '''
@font-face{font-family:Jost;src:url(file://%(A)s/ui/Jost-VF.ttf);font-weight:100 900}
@page{size:8.5in 11in;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:8.5in}
body{font-family:Jost,'DejaVu Sans',sans-serif;color:#1d2a29;background:#fff}
.page{position:relative;width:8.5in;height:11in;padding:.25in;display:grid;grid-template-columns:repeat(5,1.6in);grid-template-rows:repeat(5,2.1in);page-break-after:always;overflow:hidden}
.page>.card,.page>.bk{zoom:.94118;align-self:center;justify-self:center}
.card{width:1.7in;height:2.2in;position:relative;overflow:hidden;background:#fff;border:0.5px solid #c8cdcc}
.strip{height:.055in;background:var(--tc)}
.strip.cp{height:.125in;display:flex;align-items:center;justify-content:flex-end;gap:.07in;padding:0 .07in;color:#fff;font-weight:800;font-size:6pt;letter-spacing:.03em;text-shadow:0 0 2px rgba(0,0,0,.35)}
.strip.cp span{display:inline-flex;align-items:center;gap:.02in}.strip.cp img{width:.1in;height:.1in}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:.04in;padding:.045in .07in 0;height:.31in}
.top .nm{flex:1;min-width:0;padding-top:.01in}
.top .nm h1{white-space:normal;line-height:.95}
.top .syn{margin:0;flex:none;max-width:.8in;flex-wrap:wrap;justify-content:flex-end;gap:.01in}
.top .syn img.i{width:.245in;height:.245in}
.top .syn.s4{max-width:.62in}.top .syn.s4 img.i{width:.195in;height:.195in}
.mid{display:flex;gap:.08in;padding:.03in .07in .03in;height:.67in;border-bottom:.5px solid #cfd4d3}
.mid .por{width:.6in;height:.6in}
.sl{flex:1;display:grid;grid-template-columns:1fr 1fr;align-content:space-between;align-items:center;padding:.01in 0;column-gap:.02in}.sl .stat:first-child{grid-column:1/3;justify-self:center}.sl .stat{justify-content:flex-start}
.sl .stat{font-size:9pt;gap:.05in;line-height:1}.sl .stat img{width:.12in;height:.12in}
.tag{position:absolute;left:.07in;bottom:.045in;font-size:5.6pt;font-weight:800;letter-spacing:.07em;color:#fff;background:var(--tc);border-radius:.03in;padding:.012in .05in}
.arc{font-size:5.4pt;font-weight:800;line-height:1.15;text-align:right;max-width:.8in;color:#4a5a58;padding-top:.02in}
.cost{position:absolute;right:.07in;bottom:.035in;display:flex;align-items:center;gap:.025in;font-weight:800;font-size:8pt;color:#5a4410;background:#fdf1cf;border-radius:.1in;padding:0 .06in 0 .035in}
.cost img{width:.11in;height:.11in}
.pw.cd{padding-bottom:.16in}
.por{width:.56in;height:.56in;border-radius:.05in;overflow:hidden;flex:none;background:var(--pc)}
.por img{width:100%%;height:100%%;image-rendering:pixelated;display:block}
.nm{display:flex;flex-direction:column;min-width:0;flex:1}
.nm h1{font-weight:800;line-height:1;white-space:nowrap;letter-spacing:-.01em}
.nm .tier{font-size:5.6pt;white-space:nowrap;font-weight:700;color:#7d8685;letter-spacing:.06em;margin-top:.02in}
.syn{display:flex;gap:.012in;margin-top:.03in}
.syn img.i{width:.29in;height:.29in}
.syn.s4 img.i{width:.215in;height:.215in}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:0 .02in;padding:.02in .09in .03in;border-bottom:.5px solid #cfd4d3}
.stat{display:flex;align-items:center;gap:.03in;font-weight:800;font-size:10pt;line-height:1.15}
.stat img{width:.16in;height:.16in}
.pw{padding:.04in .08in 0}
.pwn{font-weight:800;font-size:8pt;display:flex;align-items:center;justify-content:space-between;gap:.03in;line-height:1.1;margin-bottom:.025in}.pnm{display:flex;align-items:center;gap:.03in;min-width:0;white-space:nowrap}
.pwn img.star{width:.1in;height:.1in}
.pwr{display:flex;align-items:center;gap:.04in;margin:.02in 0 .025in}
.pill{flex:none;display:inline-flex;align-items:center;gap:.02in;background:#e3ebf6;border-radius:.1in;padding:0 .05in;font-weight:800;font-size:7.5pt;color:#26508f}
.pill img{width:.1in;height:.1in}
.dbl{width:.12in;height:.1in;opacity:.6}
.role{font-size:5pt;font-weight:700;letter-spacing:.07em;color:#8a9190;margin-left:auto;text-transform:uppercase}
.tx{font-size:6.1pt;line-height:1.34;font-weight:500}
.tx img.i{width:.115in;height:.115in;vertical-align:-.025in}
.tx img.dm{width:.11in;height:.11in}
.tx b{font-weight:800;font-size:6.8pt}
.tx .ap{white-space:nowrap}
.tx .ap img{margin-right:.005in}
.tx sub{font-size:4.6pt;font-weight:800;vertical-align:baseline;margin:0 .01in 0 -.005in;color:#6a3aa0}
.tx .st{white-space:nowrap}
.tx .st u{text-decoration:none;font-weight:800;font-size:5.4pt;letter-spacing:.02em;margin-left:.008in}
.dish{margin-top:.03in;background:#fdeed6;border:.5px dashed #d79a40;border-radius:.05in;padding:.012in .035in;font-size:4.6pt;line-height:1.1;color:#5c3a00}
.dish .dh{display:flex;align-items:center;gap:.025in;font-size:6pt}.dish .dh span{font-weight:600;font-size:4.8pt;color:#8a6a30;margin-left:auto}
.dish img.i{width:.1in;height:.1in;vertical-align:-.02in}.dish .dl img.i{width:.085in;height:.085in}.dish .dl{font-weight:600}.dish .dl em{font-style:normal;font-weight:900;font-size:4.6pt;background:#d79a40;color:#fff;border-radius:.02in;padding:0 .02in;margin-right:.02in}
/* item cards */
.ihd{display:flex;gap:.06in;align-items:center;padding:.08in .08in .02in}
.iimg{width:.52in;height:.52in;background:#eef0f0;border-radius:.06in;display:flex;align-items:center;justify-content:center;flex:none}
.iimg img{width:.44in;height:.44in;image-rendering:pixelated}
.itx{padding:.05in .09in}
.itx .tx{font-size:8pt;line-height:1.38}
.unh{display:inline-block;background:#2c3a38;color:#fff;font-size:6pt;letter-spacing:.05em;padding:.01in .05in;border-radius:.03in;margin-right:.02in}
.itx .tx img.i{width:.14in;height:.14in}
.price{margin-left:auto;display:flex;align-items:center;gap:.02in;font-weight:800;font-size:8pt}
.price img{width:.13in;height:.13in}
.chips{display:flex;flex-wrap:wrap;gap:.03in;padding:.0in .09in}
.chip{display:inline-flex;align-items:center;gap:.02in;background:#f2f4f4;border-radius:.1in;padding:0 .045in;font-weight:800;font-size:8pt}
.chip img{width:.14in;height:.14in}
img.i{width:.11in;height:.11in}
.dishc .lv{font-size:5.5pt;line-height:1.2;margin-top:.012in}
.dishc .lv img.i{width:.09in;height:.09in}
.ihead{display:flex;flex-wrap:nowrap;align-items:center;justify-content:center;gap:.045in;height:.3in;padding:0 .05in;background:#f1f3f3;border-bottom:.045in solid var(--tc);overflow:hidden}
.hc{display:inline-flex;align-items:center;gap:.012in;font-weight:800;font-size:7.5pt;white-space:nowrap}
.hc img.i{width:.17in;height:.17in}.hc img.flag{width:.13in;height:.17in}
.hc i{font-style:normal;font-size:6.2pt}
.tight{gap:.02in}.tight .hc{font-size:6pt}.tight .hc img.i{width:.13in;height:.13in}.tight .hc i{font-size:5.4pt}
/* backs */
.bk{width:1.7in;height:2.2in;background:#fff;padding:.05in}
.bk .in{width:100%%;height:100%%;border-radius:.1in;background:var(--tc);border:.03in solid var(--tc);position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center}
.bk .in:before{content:'';position:absolute;inset:.02in;border:.012in solid rgba(255,255,255,.75);border-radius:.08in}
.logo{width:1.2in;height:1.23in;position:relative}
.logo img{width:100%%;height:100%%}
.logo .num{position:absolute;left:36%%;width:28%%;top:68%%;height:27%%;background:#111;border-radius:.045in;display:flex;align-items:center;justify-content:center}
.logo .num span{color:#f6c423;font-weight:900;font-size:13pt;line-height:1;letter-spacing:-.02em}
.bk .lab{text-align:center;margin-top:.12in;color:#fff;font-weight:800;font-size:11pt;letter-spacing:.35em;padding-left:.35em}
/* ref cards */
.rh{padding:.07in .08in .03in;display:flex;align-items:center;gap:.05in;border-bottom:.5px solid #cfd4d3;font-weight:800;font-size:9pt}
.rh img{width:.2in;height:.2in}
.rows{padding:.06in .08in;display:flex;flex-direction:column;gap:.04in}
.rw{display:flex;gap:.05in;align-items:flex-start;font-size:5.9pt;line-height:1.24;font-weight:500}
.rw>img{width:.17in;height:.17in;flex:none;margin-top:-.005in}
.rw b{font-weight:800}
.rw .tx{font-size:6pt}
.rw div img.i,.rw div img.dm{width:.12in;height:.12in;vertical-align:-.025in}
.rw div .st u{text-decoration:none;font-weight:800;font-size:5.6pt}
.rw div .st{white-space:nowrap}
.rw div .ap{white-space:nowrap}
.rw div sub{font-size:4.4pt;font-weight:800;color:#6a3aa0;vertical-align:baseline}
.lv{display:flex;gap:.035in;font-size:6.4pt;line-height:1.3;margin-top:.02in}
.lv>em{flex:none;font-style:normal;font-weight:900;color:#fff;background:var(--tc);border-radius:.03in;width:.17in;text-align:center;height:.115in;line-height:.115in;font-size:5pt;margin-top:.005in}
.lv>span{flex:1}
.lv img.i{width:.105in;height:.105in;vertical-align:-.02in}
.lv img.dm{width:.1in;height:.1in}
.lv b{font-weight:800}
.lv .ap{white-space:nowrap}
.lv .st{white-space:nowrap}
.lv .st u{text-decoration:none;font-weight:800;font-size:5.4pt}
.lv sub{font-size:4.2pt;font-weight:800;vertical-align:baseline;color:#6a3aa0}
.th{font-size:6pt;font-weight:700;color:#5d6665;margin:.01in 0 .03in .08in}
'''

def page_html(body, extra=''):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS % {"A": A}}{extra}</style></head><body>{body}</body></html>'

def cutmarks():
    L = []
    xs = [.25 + 1.6 * k for k in range(6)]; ys = [.25 + 2.1 * k for k in range(6)]
    for x in xs:
        L.append(f'<line x1="{x}" y1=".06" x2="{x}" y2=".21"/><line x1="{x}" y1="10.79" x2="{x}" y2="10.94"/>')
    for y in ys:
        L.append(f'<line x1=".06" y1="{y}" x2=".21" y2="{y}"/><line x1="8.29" y1="{y}" x2="8.44" y2="{y}"/>')
    return ('<svg style="position:absolute;left:0;top:0;width:8.5in;height:11in;pointer-events:none" viewBox="0 0 8.5 11" '
            'stroke="#000" stroke-width=".008" fill="none">' + ''.join(L) + '</svg>')

def pages(cells, back=False):
    out = []
    for i in range(0, len(cells), 25):
        chunk = cells[i:i + 25]
        chunk += ['<div class="card" style="border:none"></div>'] * (25 - len(chunk)) if not back else ['<div class="bk"></div>'] * (25 - len(chunk))
        if back:  # mirror columns for long-edge duplex printing
            rows = [chunk[r * 5:(r + 1) * 5][::-1] for r in range(5)]
            chunk = [c for r in rows for c in r]
        out.append('<div class="page">' + cutmarks() + ''.join(chunk) + '</div>')
    return ''.join(out)

def fit_name(n):
    L = len(n)
    return 14 if L <= 7 else 12.5 if L <= 9 else 11 if L <= 11 else 9.5 if L <= 13 else 9

def portrait(dex):
    cands = [f'{A}/portraits/{dex}/Normal.png', f'{A}/portraits/{dex.replace("-", "/")}/Normal.png', f'{A}/portraits/{dex.split("-")[0]}/Normal.png']
    for c in cands:
        if os.path.exists(c): return c
    return f'{A}/ui/missing-portrait.png'

# ------------------------------------------------------------------ data
wb = openpyxl.load_workbook(f'{ROOT}/pac-core-cards-draft.xlsx')
REMOVED = {x.replace('_', ' ').title() for x in json.load(open(f'{ROOT}/pac-data/removed.json'))}
CARDS = [r for r in list(wb['Cards'].iter_rows(values_only=True))[1:] if r[2] and r[2] not in REMOVED]
SYNS = [r for r in list(wb['Synergies'].iter_rows(values_only=True))[1:] if r[0]]
DISHES = [r for r in list(wb['Gourmet dishes'].iter_rows(values_only=True))[1:] if r[0]]
CARD2DISH = {}
for r in DISHES:
    for nm in (r[2] or '').split(', '): CARD2DISH[nm.strip()] = r[1]

def short_dish(t):
    t = re.sub(r'random \+1 stat boost\(s\) \([^)]*\)', 'random +1 stat', t)
    t = t.replace('stat boost(s)', 'stat').replace(' on entry', ' on entry').replace('enters with', 'enters +').replace('its first attack inflicts', '1st attack:')
    t = re.sub(r'\((\d) turns?\)', r'(\1t)', t).replace('every 5th attack', 'every 5th').replace('PROTECT until its first turn', 'PROTECT first turn')
    return t
DISHROW = {}
for r in DISHES:
    for nm in (r[2] or '').split(', '): DISHROW[nm.strip()] = r
def dish_html(name):
    r = DISHROW[name]; l = [short_dish(x) for x in r[3:6]]
    return (f'<div class="dish"><div class="dh">{ic("DISH")}<b>{html.escape(r[1])}</b><span>served to next card</span></div>'
            f'<div class="dl"><em>I</em>{rich(l[0])} <em>II</em>{rich(l[1])} <em>III</em>{rich(l[2])}</div></div>')

PMIN = {'I': 1, 'II': 3, 'III': 5, 'IV': 8, 'V': 15}
TRADEV = {'I': 0, 'II': 2, 'III': 4, 'IV': 7, 'V': 14}
import math
def cost_trade(tier, pool, val):
    if pool == 'unique': return '—', 12
    if pool == 'legendary': return '—', 25
    if pool == 'hatch': return '—', TRADEV[tier]
    p = math.ceil(val - 1e-9)
    if pool in ('add', 'hatch'): p = max(p, PMIN.get(tier, 1))
    return p, TRADEV[tier]
def cp_strip(price, trade):
    return f'<div class="strip cp"><span style="font-size:7.5pt">{ic("COIN")}{price} ({trade})</span></div>'

NAMEFLAG = []
RENAME = {'Alcremie Vanilla': 'Alcremie', 'Kommo O': 'Kommo-o', 'Hakamo O': 'Hakamo-o', 'Jangmo O': 'Jangmo-o'}
def clean_pw(t):
    t = re.sub(r'\s*\((?:scales with[^)]*|more hits with high SPEED)\)', '', t)
    t = t.replace(' (always crit, ignores all blocking)', ' (always crit)')
    t = re.sub(r'\b1 extra basic attack\(s\)', '1 extra basic attack', t)
    t = re.sub(r'\b(\d+) (\w+)\(s\)', lambda m: m.group(1) + ' ' + m.group(2) + ('' if m.group(1) == '1' else 's'), t)
    t = re.sub(r'\ban? ATK attack', 'a basic attack', t)
    t = t.replace('for each stat boost you have (ATK, SPEED, DEF, SP.DEF, AP)', 'for each time you have gained a stat this duel')
    return t

def card_front(r):
    tier, dex, name, stars, val, pac, syn, hp, atk, df, sdf, spd, pp, pwname, role, pwtext, note = r[:17]
    pwtext = clean_pw(pwtext)
    pool = r[17] if len(r) > 17 else 'core'
    tlabel = {'add': f'ADD · TIER {tier}', 'hatch': f'HATCH · TIER {tier}', 'unique': 'UNIQUE', 'legendary': 'LEGENDARY'}.get(pool, f'TIER {tier}')
    types = [s.strip().upper() for s in syn.split('/') if s.strip()]
    arc = (name == 'Arceus')
    pc = TYPECOL.get(types[0] if types else '', '#ccd')
    synh = ('<div class="arc">Copies your 3 highest synergies</div>' if arc else ''.join(ic(t) for t in types)); syncls = 'syn s4' if (len(types) > 3 or len(name) > 13) else 'syn'
    stats = [('HP', hp), ('ATK', atk), ('PP', pp), ('DEF', df), ('SPE_DEF', sdf), ('SPEED', spd)]
    sh = ''.join(f'<div class="stat">{ic(k)}<span>{v}</span></div>' for k, v in stats)
    star = ''.join(ic('STAR', 'star') for _ in range(int(stars or 1)))
    dish = ''
    if 'GOURMET' in types and name in CARD2DISH:
        dish = dish_html(name)
    name = RENAME.get(name, name)
    if name == 'Silvally': dish = '<div class="dish"><div class="dh"><b>Memory</b></div><div class="dl">Give it a type Stone: Silvally swaps Normal for that type.</div></div>'
    price, trade = cost_trade(tier, pool, val)
    sl = ''.join(f'<div class="stat">{ic(k)}<span>{v}</span></div>' for k, v in [('HP', hp), ('ATK', atk), ('SPEED', spd), ('DEF', df), ('SPE_DEF', sdf)])
    synw = (min(len(types), 3) * .195 if len(types) > 3 else len(types) * .245) + .01
    avail = 1.56 - .05 - synw
    lw = max(len(w) for w in name.split()) if name.split() else 1
    nf1 = min(13, avail * 72 / ((0.68 if len(types) >= 3 else 0.62) * max(1, len(name))))
    if nf1 >= 10.5: nf, nl = nf1, 1
    elif ' ' in name: nf, nl = min(11, max(7.5, avail * 72 / (0.62 * lw))), 2
    else: nf, nl = max(7.0, nf1), 1
    NAMEFLAG.append((name, pool, round(nf, 1), nl, len(types)))
    return (f'<div class="card" style="--tc:{TIERCOL[tier]};--pc:{pc}"><div class="strip"></div>'
            f'<div class="top"><div class="nm"><h1 style="font-size:{nf}pt;{"white-space:nowrap" if nl==1 else ""}">{html.escape(name)}</h1></div><div class="{"syn s4" if len(types) > 3 else "syn"}">{synh}</div></div>'
            f'<div class="mid"><div class="por"><img src="file://{portrait(dex)}"></div><div class="sl">{sl}</div></div>'
            f'<div class="pw cd"><div class="pwn"><span class="pnm" style="font-size:{8 if len(pwname) <= 9 else 7 if len(pwname) <= 12 else 6.2}pt;{"white-space:normal;line-height:1.05" if len(pwname) > 17 else ""}">{html.escape(pwname)}{star}</span><span class="pill">{pp}{ic("PP")}<svg class="dbl" viewBox="0 0 20 16"><path d="M2 2l6 6-6 6M10 2l6 6-6 6" stroke="#566" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span></div>'
            f'<div class="tx" style="font-size:{(7.6 if len(pwtext)<=55 else 7.0 if len(pwtext)<=85 else 6.5 if len(pwtext)<=115 else 6.0 if len(pwtext)<=135 else 5.5) - ((0.9 + (0.5 if len(pwtext) > 55 else 0)) if dish else 0)}pt">{rich(pwtext)}</div>{dish}</div>'
            f'<div class="tag">{tlabel}</div><div class="cost">{ic("COIN")}{price} ({trade})</div></div>')

def back(tier, pool='core'):
    num = {'UNIQUE': 'U', 'LEGENDARY': 'L'}.get(tier, tier)
    badge = '' if (tier == 'I' and pool == 'core') else f'<div class="num"><span>{num}</span></div>'
    lab = {'add': f'ADDITIONAL {tier}', 'hatch': f'HATCH {tier}', 'unique': 'UNIQUE', 'legendary': 'LEGENDARY'}.get(pool, f'TIER {tier}')
    return (f'<div class="bk" style="--tc:{TIERCOL[tier]}"><div class="in"><div class="logo"><img src="file://{W}/assets/logo.png">{badge}</div>'
            f'<div class="lab" style="font-size:{11 if len(lab) < 10 else 8}pt">{lab}</div></div></div>')

# items
sys.path.insert(0, f'{ROOT}/pac-sim')
from items import ITEMS as ITEMDEF
ITEMNAME = {v['name']: v for v in ITEMDEF.values()}
FLAGCHIPS = {
 'reaper': [('CRIT_POWER', '')], 'dodge': [('LUCK', '1/7')], 'lens': [('TRUE', 'back')], 'helmet': [('CRIT', '✕')],
 'immune_neg': [('SAFEGUARD', '')], 'scope': [('PP', 'steal')], 'nullify': [('SILENCE', ''), ('ATK', '/PP')],
 'abshield': [('SAFEGUARD', ''), ('SHIELD', '3')], 'vest': [('POISONED', '½'), ('BURN', '0')], 'flameorb': [('BURN', 'self'), ('ATK', '+50%')],
 'greenorb': [('HP', '/2t')], 'nomicon': [('BURN', 'SP'), ('SPE_DEF', '-1')], 'soul': [('AP', '/t')], 'aqua': [('PP', '/cast')],
 'bigeater': [('DISH', '+½')], 'cover': [('PROTECT', '1HP')], 'boots': [('FLINCH', '0'), ('SPLASH', '0')], 'loaded': [('SPLASH', '½')],
 'mach': [('SPEED', '/4t')], 'armorbreak': [('ARMOR_BREAK', 'hit')], 'charm30': [('PROTECT', '½')], 'smoke': [('SHIELD', '+4'), ('PARALYSIS', '½')],
 'upgrade': [('SPEED', '/2atk')], 'blueorb': [('ELECTRIC', '3rd')], 'cheap': [('PP', '-1')], 'explosive': [('SPECIAL', 'boom')], 'gracidea': [('BATON', '+1')],
 'stardust': [('SHIELD', '/cast')], 'twist': [('ATK', '/status')], 'dst': [('PP', '/2atk')], 'doll': [('SHIELD', '-1')], 'wide': [('SPLASH', '/2atk')], 'metronome': [('PP', '/5t')], 'spelltag': [('CURSE', 'KO')], 'surf': [('SPLASH', '3')], 'parat': [('PARALYSIS', '/3')], 'vestburn': [('BURN', '0')], 'pokerus': [('POKERUS', '/3t')], 'elixir': [('PP', 'full')], 'expshare': [('ATK', 'copy')], 'terrain': [('SHIELD', '+2')], 'hpmult': [('HP', '×2')], 'swarm': [('SWARM', '3')], 'bulb': [('SHIELD', 'store')], 'starpiece': [('STAR', '+1')], 'econ_income': [('COIN', '/rd')], 'slot': [('ENTRY', '+1')], 'econ_ko': [('COIN', '/KO')], 'pads': [('SHIELD', '×2')],
 'shellbell': [('HP', '1')], 'redorb': [('TRUE', '¼')], 'immune_sleep': [('SLEEP', '0')], 'revive': [('RESURRECTION', '')], 'muscle': [('DEF', '/3hit')],
 'wonder': [('QMARK', 'T3+T2')], 'barb': [('TRUE', 'back'), ('WOUND', '')], 'glove': [('TRUE', '+1')], 'soul2': [],
}
def item_header(name):
    it = ITEMNAME.get(name)
    if not it: return ''
    st, fl = it['stats'], it['flags']
    chips = []
    def chip(icon, txt, pre=''):
        chips.append(f'<span class="hc">{pre}{ic(icon)}<i>{txt}</i></span>')
    mp = [('hp', 'HP'), ('atk', 'ATK'), ('df', 'DEF'), ('sdf', 'SPE_DEF'), ('spd', 'SPEED'), ('ap', 'AP'), ('crit', 'CRIT')]
    if 'type' in fl: chip(fl['type'], '')
    if 'gem' in fl: chip(fl['gem'], '+1')
    for k, icon in mp:
        if k in st: chip(icon, f"+{_tok(st[k])}" if k == 'crit' else f"+{st[k]}")
    ent = [(k, icon) for k, icon in (('sh', 'SHIELD'), ('ch', 'PP')) if k in st]
    for j, (k, icon) in enumerate(ent): chip(icon, f"+{st[k]}", ic('ENTRY', 'flag') if j == 0 else '')
    for f_, v in fl.items():
        if f_ == 'dodge': chip('LUCK', f'1/{v}'); continue
        if f_ == 'mach': chip('SPEED', f'/{v}t'); continue
        for icon, txt in FLAGCHIPS.get(f_, []): chip(icon, txt)
    if not chips: return ''
    cls = 'ihead tight' if len(chips) >= 6 else 'ihead'
    return f'<div class="{cls}">' + ''.join(chips[:7]) + '</div>'

ITEMS = json.load(open(f'{ROOT}/items_core.json'))['core']
ITEMFILE = {}
for f in os.listdir(f'{A}/item{{tps}}'):
    if f.endswith('.png'): ITEMFILE[re.sub(r'[^A-Z0-9]', '', f[:-4].upper())] = f
def item_img(name):
    k = re.sub(r'[^A-Z0-9]', '', name.upper())
    alias = {'POKEMONOMICON': 'POKEMONOMICON', 'XRAYVISION': 'XRAY_VISION'}
    if k in ITEMFILE: return f'{A}/item{{tps}}/{ITEMFILE[k]}'
    for kk, f in ITEMFILE.items():
        if kk.startswith(k[:8]): return f'{A}/item{{tps}}/{f}'
    return None

def chips(stats):
    out = []
    mp = {'hp': 'HP', 'atk': 'ATK', 'df': 'DEF', 'sdf': 'SPE_DEF', 'spd': 'SPEED', 'ap': 'AP', 'ch': 'PP', 'sh': 'SHIELD', 'crit': 'CRIT_CHANCE'}
    for m in re.finditer(r'(HP|ATK|DEF|SP\.DEF|speed|AP|charge|shield|crit)', stats or ''): pass
    return ''

def item_front(r):
    tier, price, copies, name, cat, eff, stats, lift, note = r[:9]
    if name == 'Wonder Box': eff = 'Battle start: borrow the top Tier III and Tier II items (max 3 held; Tier II only if room). Returned after the battle.'
    img = item_img(name)
    imgh = f'<img src="file://{img}">' if img else ''
    catlab = {'Component': 'COMPONENT', 'Crafted': 'ITEM', 'Stone': 'STONE'}.get(cat, cat.upper())
    return (f'<div class="card" style="--tc:{TIERCOL[tier]}">{item_header(name)}'
            f'<div class="ihd"><div class="iimg">{imgh}</div><div class="nm"><h1 style="font-size:{fit_name(name)-1}pt;white-space:normal;line-height:1.05">{html.escape(name)}</h1>'
            f'</div></div>'
            f'<div class="itx"><div class="tx">{rich(eff).replace("UNHOLDABLE. ", "<b class=unh>UNHOLDABLE</b> ")}</div></div>'
            f'<div class="tag">ITEM · TIER {tier}</div><div class="cost">{ic("COIN")}{price} ({TRADEV[tier]})</div></div>')

def write(name, body):
    open(f'{W}/out/{name}.html', 'w').write(page_html(body))

if __name__ == '__main__':
    which = sys.argv[1:] or ['core', 'items']
    if 'core' in which:
        write('PAC_core', pages([card_front(r) for r in CARDS]))
        write('PAC_core_BACKS', pages([back(r[0]) for r in CARDS], back=True))
    if 'items' in which:
        ALLI=[r for r in ITEMS for _ in range(r[2])]
        write('PAC_items', pages([item_front(r) for r in ALLI]))
        write('PAC_items_BACKS', pages([back(r[0]).replace('TIER ' + r[0], 'ITEM<br>TIER ' + r[0]) for r in ALLI], back=True))
    print('built', which, len(CARDS), len(ITEMS))
