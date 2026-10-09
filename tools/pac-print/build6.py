import sys
sys.argv = [sys.argv[0]]
from build import ic, TIERCOL, A, W
CW, CH = 4.0, 5.25
GOLD, GOLDD, GOLDL = '#d9a61e', '#a67c00', '#fff4cf'
XPC, PTC, RED, GRN = '#5b6fb8', '#2f8f83', '#c2392b', '#3f9a55'
LV = [('L2', 0, '#848b89', ''), ('L3', 2, TIERCOL['II'], 'TIER II'), ('L4', 6, TIERCOL['III'], 'TIER III'), ('L5', 14, TIERCOL['IV'], 'TIER IV'),
      ('L6', 30, TIERCOL['V'], 'TIER V'), ('L7', 56, '#848b89', ''), ('L8', 94, '#444', '')]
CSS = f'''@font-face{{font-family:Jost;src:url(file://{A}/ui/Jost-VF.ttf);font-weight:100 900}}
@page{{size:8.5in 11in;margin:0}}*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:8.5in;height:11in}}body{{font-family:Jost,'DejaVu Sans',sans-serif;color:#1d2a29;background:#fff;position:relative}}
.tk{{position:absolute;width:{CW}in;height:{CH}in;border:.6pt dashed #999;padding:.1in .12in;overflow:hidden}}
.lab{{display:flex;align-items:center;gap:.05in;font-size:8pt;font-weight:800;letter-spacing:.06em;height:.17in;margin-top:.06in}}
.lab img{{width:.16in;height:.16in}}.lab small{{font-weight:600;font-size:5.5pt;color:#777;letter-spacing:0;margin-left:.04in}}
.row{{display:flex;align-items:center;margin-top:.02in}}
.rl{{width:.42in;font-size:5.5pt;font-weight:700;color:#666;letter-spacing:.05em;flex:none}}
.b{{border-radius:.045in;border:.8pt solid;text-align:center;font-weight:800;margin-right:.015in;flex:none}}
.lv{{display:flex;gap:.03in;margin-top:.07in}}
.lv div{{flex:1;border-radius:.04in;color:#fff;text-align:center;padding:.015in 0;line-height:1}}
.lv b{{display:block;font-size:8pt}}.lv span{{display:block;font-size:5pt;font-weight:600;opacity:.95;margin-top:1px}}
.note{{font-size:5.6pt;color:#555;margin-top:.05in;line-height:1.25}}
table{{border-collapse:collapse;width:100%}}td,th{{border:.7pt solid #888;text-align:center;font-size:6pt;height:.262in}}th{{background:#eee;font-size:6.5pt;height:.26in;font-weight:800}}
'''
def page(body): return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'
def four(fn):
    return ''.join(f'<div class="tk" style="left:{.25 + (i % 2) * CW}in;top:{.25 + (i // 2) * CH}in">{fn()}</div>' for i in range(4))
def box(v, col, bg, w, h, fs=8.5, extra=''):
    return f'<div class="b" style="width:{w}in;height:{h}in;line-height:{h - .015}in;font-size:{fs}pt;border-color:{col};background:{bg};color:{col};{extra}">{v}</div>'
def lab(name, col, icon=None, small=''):
    return f'<div class="lab" style="color:{col}">{ic(icon) if icon else ""}{name}{f"<small>{small}</small>" if small else ""}</div>'
def to_rows(label, vals, col, bg, w, h, fs=8.5, mark=None):
    cells = ''.join(box(v, (RED if isinstance(v, int) and v < 0 else col), ('#fbe6e3' if isinstance(v, int) and v < 0 else bg), w, h, fs, 'box-shadow:0 0 0 1.4pt #1d2a29;' if v == mark else '') for v in vals)
    return f'<div class="row"><div class="rl">{label}</div>{cells}</div>'
def levelstrip(): return '<div class="lv">' + ''.join(f'<div style="background:{c}"><b>{n}</b><span>{x} XP{(" · " + t) if t else ""}</span></div>' for n, x, c, t in LV) + '</div>'
def streak(w=.4, h=.3):
    L = [('L4+', '+3'), ('L3', '+2'), ('L2', '+1'), ('L1', '0'), ('0', ''), ('W1', '0'), ('W2', '+1'), ('W3', '+2'), ('W4+', '+3')]
    cells = ''
    for n, g in L:
        c = RED if n.startswith('L') else GRN if n.startswith('W') else '#555'
        bg = '#fbe6e3' if n.startswith('L') else '#e4f3e7' if n.startswith('W') else '#f0f0f0'
        cells += f'<div style="width:{w}in;margin-right:.015in;text-align:center;flex:none">{box(n, c, bg, w, h, 7.5)}<div style="font-size:5.5pt;font-weight:700;color:{c};margin-top:.01in">{g + " gold" if g not in ("", "0") else g}</div></div>'
    return lab('STREAK', '#444', 'TURN', 'win or lose in a row · gold bonus under the box') + f'<div class="row" style="margin-top:.02in;align-items:flex-start">{cells}</div>'
def note(t): return f'<div class="note">{t}</div>'
GN = 'Income +5, interest 1 per 5 gold (max 3), streak gold. +2 XP each round, 4 gold buys 4 XP. Level = lineup size.'
PN = 'Points start at 20. Win: gain your surviving Pokemon + round bonus (R1-3 +0, R4-6 +1, R7-9 +2, R10-12 +3); the loser loses the same.'
T10 = list(range(-20, 80, 10))
# ---- 1: tens and ones for everything
def o1():
    w, h = .355, .33
    def rr(vals, col, bg, mark=None):
        return to_rows('', vals, col, bg, w, h, mark=mark).replace('class="rl"', 'class="rl" style="width:0"')
    return (lab('GOLD', GOLDD, 'COIN') + rr(range(0, 60, 10), GOLDD, GOLDL) + rr(range(10), GOLDD, GOLDL)
            + lab('XP', XPC) + rr(range(0, 100, 10), XPC, '#eaedf8') + rr(range(10), XPC, '#eaedf8')
            + lab('POINTS', PTC, None, 'start at 20 (outlined)') + rr(T10, PTC, '#e3f3f0', 20) + rr(range(10), PTC, '#e3f3f0')
            + streak(.4, .3) + levelstrip() + note(GN + ' ' + PN))
# ---- 2: ladders
def o2():
    bands = ['#fff4cf', '#ffe69a', '#ffd25c', '#f2b52e']
    g = lab('GOLD', GOLDD, 'COIN', 'shading = interest: 5+ → +1, 10+ → +2, 15+ → +3')
    for r in range(4):
        g += '<div class="row" style="margin-top:.01in">' + ''.join(box(v, GOLDD, bands[min(3, v // 5)], .3, .205, 7) for v in range(r * 10, r * 10 + 10)) + '</div>'
    p = lab('POINTS', PTC, None, 'start at 20 (outlined)')
    for r in range(8):
        base = -20 + r * 10
        p += '<div class="row" style="margin-top:.01in">' + ''.join(box(v, (RED if v < 0 else PTC), ('#fbe6e3' if v < 0 else '#e3f3f0' if r % 2 == 0 else '#cfebe6'), .3, .185, 7, 'box-shadow:0 0 0 1.4pt #1d2a29;' if v == 20 else '') for v in range(base, base + 10)) + '</div>'
    x = lab('XP', XPC) + to_rows('TENS', range(0, 100, 10), XPC, '#eaedf8', .3, .22, 7.5) + to_rows('ONES', range(10), XPC, '#eaedf8', .3, .22, 7.5)
    return g + p + x + streak(.4, .26) + levelstrip() + note(GN)
# ---- 3: pencil tick-off
def o3():
    def line(vals, col, bg, w, label_every=5, startmark=None):
        return '<div class="row" style="margin-top:.015in">' + ''.join(f'<div style="position:relative;width:{w}in;height:{w}in;border:.7pt solid {(RED if isinstance(v, int) and v < 0 else col)};background:{bg if v % label_every else "#d8efe9" if col == PTC else "#ffe69a"};margin-right:.01in;flex:none;text-align:center;color:{col};font-size:5pt;font-weight:700;{"box-shadow:0 0 0 1.2pt #1d2a29;" if v == startmark else ""}">{v if v % label_every == 0 else ""}</div>' for v in vals) + '</div>'
    g = lab('GOLD', GOLDD, 'COIN', 'cross off / erase: one box = 1 gold') + line(range(1, 21), GOLDD, GOLDL, .17) + line(range(21, 41), GOLDD, GOLDL, .17)
    p = lab('POINTS', PTC, None, 'one box = 1 point; start at 20 (outlined); -20 to 79')
    for r in range(5):
        p += line(range(-20 + r * 20 + 1, -20 + r * 20 + 21), PTC, '#e3f3f0', .17, startmark=20)
    xp = lab('XP', XPC, None, 'fill a row to reach that level')
    for n, k, c, t in [('L3', 2, TIERCOL['II'], 'T-II'), ('L4', 4, TIERCOL['III'], 'T-III'), ('L5', 8, TIERCOL['IV'], 'T-IV'), ('L6', 16, TIERCOL['V'], 'T-V'), ('L7', 26, '#848b89', ''), ('L8', 38, '#444', '')]:
        for li, kk in enumerate([k] if k <= 26 else [19, 19]):
            xp += f'<div class="row" style="margin-top:.014in"><div style="width:.5in;font-size:6pt;font-weight:800;color:{c};flex:none">{n + " " + t if li == 0 else ""}</div>' + ''.join(f'<div style="width:.11in;height:.11in;border:.8pt solid {c};margin-right:.012in;flex:none"></div>' for _ in range(kk)) + '</div>'
    return g + p + xp + streak(.4, .26).replace('win or lose in a row · gold bonus under the box', 'circle it') + note(GN)
# ---- 4: hybrid (cubes for gold & points, tick XP staircase)
def o4():
    bands = ['#fff4cf', '#ffe69a', '#ffd25c', '#f2b52e']
    g = lab('GOLD', GOLDD, 'COIN', 'cube · shading = interest 5/10/15+')
    for r in range(4): g += '<div class="row" style="margin-top:.01in">' + ''.join(box(v, GOLDD, bands[min(3, v // 5)], .3, .215, 7.5) for v in range(r * 10, r * 10 + 10)) + '</div>'
    p = lab('POINTS', PTC, None, 'cubes: tens + ones') + to_rows('TENS', T10, PTC, '#e3f3f0', .3, .27, 8, mark=20) + to_rows('ONES', range(10), PTC, '#e3f3f0', .3, .27, 8)
    xp = lab('XP', XPC, None, 'tick boxes: fill a row to reach that level')
    for n, k, c, t in [('L3', 2, TIERCOL['II'], 'T-II'), ('L4', 4, TIERCOL['III'], 'T-III'), ('L5', 8, TIERCOL['IV'], 'T-IV'), ('L6', 16, TIERCOL['V'], 'T-V'), ('L7', 26, '#848b89', ''), ('L8', 38, '#444', '')]:
        for li, kk in enumerate([k] if k <= 26 else [19, 19]):
            xp += f'<div class="row" style="margin-top:.014in"><div style="width:.5in;font-size:6pt;font-weight:800;color:{c};flex:none">{n + " " + t if li == 0 else ""}</div>' + ''.join(f'<div style="width:.11in;height:.11in;border:.8pt solid {c};margin-right:.012in;flex:none"></div>' for _ in range(kk)) + '</div>'
    return g + p + xp + streak(.4, .26) + note(GN)
# ---- 5: ledger
def o5():
    bonus = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}
    head = '<tr><th>ROUND</th><th>W / L</th><th>STREAK</th><th style="color:#a67c00">GOLD</th><th style="color:#5b6fb8">XP</th><th style="color:#2f8f83">POINTS</th></tr>'
    rows = ''.join(f'<tr><td><b style="font-size:8pt">{r}</b><br><span style="font-size:5pt;color:#777">bonus +{bonus[r]}</span></td><td style="letter-spacing:.2em;font-weight:700;color:#888">W&nbsp;L</td><td></td><td></td><td></td><td></td></tr>' for r in range(1, 13))
    start = '<tr><td style="background:#f6f6f6;font-weight:700">START</td><td style="background:#f6f6f6">-</td><td style="background:#f6f6f6">0</td><td style="background:#f6f6f6">5</td><td style="background:#f6f6f6">0</td><td style="background:#f6f6f6;font-weight:800">20</td></tr>'
    streak_ref = ('<div style="display:flex;gap:.04in;margin-top:.06in;font-size:6pt;font-weight:700"><div style="flex:1;border:.7pt solid #888;border-radius:.04in;padding:.03in;text-align:center">STREAK GOLD<br><span style="font-weight:600;font-size:5.5pt">2 in a row +1 · 3 +2 · 4+ +3<br>(wins and losses both pay)</span></div>'
                  '<div style="flex:1;border:.7pt solid #888;border-radius:.04in;padding:.03in;text-align:center">INTEREST<br><span style="font-weight:600;font-size:5.5pt">1 per 5 gold banked<br>(max +3 at 15 gold)</span></div></div>')
    return f'<table style="table-layout:fixed"><colgroup><col style="width:.55in"><col style="width:.55in"><col style="width:.65in"><col style="width:.65in"><col style="width:.65in"><col style="width:.65in"></colgroup>{head}{start}{rows}</table>' + streak_ref + levelstrip() + note('Write the number at the end of each round. Income +5 + interest + streak gold; +2 XP each round; 4 gold buys 4 XP. Points: win = surviving Pokemon + round bonus (shown under each round); loser loses the same.')
OPTS = [('1', o1), ('2', o2), ('3', o3), ('4', o4), ('5', o5)]
for n, fn in OPTS:
    open(f'{W}/out/PAC_tracker4_{n}.html', 'w').write(page(four(fn)))
print('ok')

# ---- v3: option 1 with the XP snake track 0-69
LVT = {0: ('L2', '#848b89', ''), 2: ('L3', TIERCOL['II'], 'TIER II'), 6: ('L4', TIERCOL['III'], 'TIER III'), 14: ('L5', TIERCOL['IV'], 'TIER IV'), 30: ('L6', TIERCOL['V'], 'TIER V'), 56: ('L7', '#5f6663', '')}
def xptrack():
    w, h = .366, .33
    out = lab('XP', XPC, None, '0-56 (level 7), read left to right')
    for r in range(6):
        vals = [x for x in range(r * 10, r * 10 + 10) if x <= 56]
        cells = ''
        for xp in vals:
            k = max(k for k in LVT if k <= xp); name, col, tier = LVT[k]
            if xp in LVT and xp > 0:
                cells += f'<div class="b" style="width:{w}in;height:{h}in;border-color:#1d2a29;background:{col};color:#fff;border-width:1.4pt;line-height:1;padding-top:.02in"><div style="font-size:5pt;font-weight:700">{xp}</div><div style="font-size:8pt;font-weight:800;line-height:.95">{name}</div></div>'
            else:
                bg = ('#e8ebea' if xp == 0 else col + '33')
                tc = '#555' if col == '#848b89' else col
                cells += f'<div class="b" style="width:{w}in;height:{h}in;border-color:{col};background:{bg};color:{tc};line-height:{h - .015}in;font-size:8pt">{xp}</div>'
        arrow = '<div style="font-size:6pt;color:#999;width:.0in"></div>'
        out += f'<div class="row" style="margin-top:.012in">{cells}</div>'
    return out
def v3():
    w, h = .366, .27
    def rr(vals, col, bg, mark=None):
        return to_rows('', vals, col, bg, w, h, mark=mark).replace('class="rl"', 'class="rl" style="width:0"')
    leg = '<div class="note" style="margin-top:.04in">Level-up spaces: L3 (2 XP) Tier II · L4 (6) Tier III · L5 (14) Tier IV · L6 (30) Tier V · L7 (56). L8 is at 94 XP, past the end of this track. Level = lineup size.</div>'
    return (lab('GOLD', GOLDD, 'COIN') + rr(range(0, 60, 10), GOLDD, GOLDL) + rr(range(10), GOLDD, GOLDL)
            + lab('POINTS', PTC, None, 'start at 20 (outlined)') + rr(T10, PTC, '#e3f3f0', 20) + rr(range(10), PTC, '#e3f3f0')
            + xptrack() + streak(.4, .24) + leg + note('Income +5 + interest (1 per 5 gold, max 3) + streak gold. +2 XP each round; 4 gold = 4 XP. Duel win: gain surviving Pokemon + round bonus (R1-3 +0, R4-6 +1, R7-9 +2, R10-12 +3); loser loses the same. Start 20.'))
open(f'{W}/out/PAC_tracker_v3.html', 'w').write(page(four(v3)))
print('v3 ok')
