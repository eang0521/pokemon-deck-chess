import sys
sys.argv = [sys.argv[0]]
from build import ic, TIERCOL, A, W
CW, CH = 4.0, 2.625
LV = [('L2', 0, '#848b89', ''), ('L3', 2, TIERCOL['II'], 'TIER II'), ('L4', 6, TIERCOL['III'], 'TIER III'), ('L5', 14, TIERCOL['IV'], 'TIER IV'),
      ('L6', 30, TIERCOL['V'], 'TIER V'), ('L7', 56, '#848b89', ''), ('L8', 94, '#444', '')]
GOLD, GOLDD, GOLDL = '#d9a61e', '#a67c00', '#fff4cf'
XPC = '#5b6fb8'
CSS = f'''@font-face{{font-family:Jost;src:url(file://{A}/ui/Jost-VF.ttf);font-weight:100 900}}
@page{{size:8.5in 11in;margin:0}}*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:8.5in;height:11in}}body{{font-family:Jost,'DejaVu Sans',sans-serif;color:#1d2a29;background:#fff;position:relative}}
.tk{{position:absolute;width:{CW}in;height:{CH}in;border:.6pt dashed #999;padding:.09in .12in;overflow:hidden}}
.hd{{display:flex;align-items:center;justify-content:space-between;height:.26in;font-size:7pt;font-weight:600;color:#444}}
.nm{{flex:1;border-bottom:.8pt solid #444;margin:0 .08in 0 .05in;height:.19in;font-size:7pt;color:#777;font-weight:700;letter-spacing:.04em;line-height:.2in}}
.lab{{display:flex;align-items:center;gap:.05in;font-size:8pt;font-weight:800;letter-spacing:.06em}}
.lab img{{width:.17in;height:.17in}}
.row{{display:flex;align-items:center;margin-top:.03in}}
.rl{{width:.42in;font-size:5.5pt;font-weight:700;color:#666;letter-spacing:.05em}}
.b{{width:.3in;height:.3in;border-radius:.05in;border:.8pt solid;text-align:center;font-size:8.5pt;font-weight:800;line-height:.29in;margin-right:.015in}}
.g{{border-color:{GOLDD};background:{GOLDL};color:{GOLDD}}}.x{{border-color:{XPC};background:#eaedf8;color:{XPC}}}
.lv{{display:flex;gap:.03in;margin-top:.05in}}
.lv div{{flex:1;border-radius:.04in;color:#fff;text-align:center;padding:.015in 0;line-height:1}}
.lv b{{display:block;font-size:8pt}}.lv span{{display:block;font-size:5pt;font-weight:600;opacity:.95;margin-top:1px}}
.note{{font-size:5.6pt;color:#555;margin-top:.04in;line-height:1.25}}
'''
def page(body):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'
def tracker_pos(inner_fn):
    out = []
    for i in range(8):
        c, r = i % 2, i // 2
        out.append(f'<div class="tk" style="left:{.25 + c * CW}in;top:{.25 + r * CH}in">{inner_fn()}</div>')
    return ''.join(out)
def hdr(extra=''):
    return f'<div class="hd">PLAYER<div class="nm"></div>{extra}</div>'
def levelstrip():
    return '<div class="lv">' + ''.join(f'<div style="background:{c}"><b>{n}</b><span>{x} XP{(" · " + t) if t else ""}</span></div>' for n, x, c, t in LV) + '</div>'
def boxes(vals, cls, w=None):
    return ''.join(f'<div class="b {cls}"' + (f' style="width:{w}in;height:{w}in;line-height:{w - .01}in;font-size:{7.5 if w < .3 else 8.5}pt"' if w else '') + f'>{v}</div>' for v in vals)
# ---------- A: tens & ones
def A_inner():
    w = .33
    gold = (f'<div class="lab" style="color:{GOLDD}">{ic("COIN")}GOLD</div>'
            f'<div class="row"><div class="rl">TENS</div>{boxes(range(0, 60, 10), "g", w)}</div>'
            f'<div class="row"><div class="rl">ONES</div>{boxes(range(10), "g", w)}</div>')
    xp = (f'<div class="lab" style="color:{XPC};margin-top:.09in">XP</div>'
          f'<div class="row"><div class="rl">TENS</div>{boxes(range(0, 100, 10), "x", w)}</div>'
          f'<div class="row"><div class="rl">ONES</div>{boxes(range(10), "x", w)}</div>')
    return '<div style="height:.04in"></div>' + gold + xp + '<div style="height:.08in"></div>' + levelstrip() + '<div class="note">Cubes: one on TENS, one on ONES, add them. Income +5, interest 1 per 5 gold (max 3), streak. +2 XP each round, 4 gold buys 4 XP. Level = lineup size.</div>'
# ---------- B: interest ladder
def B_inner():
    bands = ['#fff4cf', '#ffe69a', '#ffd25c', '#f2b52e']
    def gb(v):
        b = bands[min(3, v // 5)] if v < 15 else bands[3]
        return f'<div class="b" style="width:.3in;height:.215in;line-height:.205in;border-color:{GOLDD};background:{b};color:{GOLDD};font-size:7.5pt">{v}</div>'
    rows = ''.join(f'<div class="row" style="margin-top:.012in">{"".join(gb(v) for v in range(r * 10, r * 10 + 10))}</div>' for r in range(4))
    gold = (f'<div class="lab" style="color:{GOLDD}">{ic("COIN")}GOLD<span style="font-weight:600;font-size:5.5pt;color:#777;letter-spacing:0;margin-left:.06in">shading = interest: 5+ → +1, 10+ → +2, 15+ → +3 (max)</span></div>{rows}')
    xp = (f'<div class="lab" style="color:{XPC};margin-top:.05in">XP<span style="font-weight:600;font-size:5.5pt;color:#777;letter-spacing:0;margin-left:.06in">tens + ones</span></div>'
          f'<div class="row" style="margin-top:.012in"><div class="rl" style="width:.3in">10s</div>{boxes(range(0, 100, 10), "x", .22)}</div>'
          f'<div class="row" style="margin-top:.012in"><div class="rl" style="width:.3in">1s</div>{boxes(range(10), "x", .22)}</div>')
    return hdr() + gold + xp + levelstrip().replace('margin-top', 'margin-top')
# ---------- C: tick-off
def C_inner():
    bw = .085
    gold = (f'<div class="lab" style="color:{GOLDD}">{ic("COIN")}GOLD<span style="font-weight:600;font-size:5.5pt;color:#777;letter-spacing:0;margin-left:.06in">cross off / erase: one box = 1 gold</span></div>')
    for r in range(2):
        cells = ''
        for v in range(r * 20 + 1, r * 20 + 21):
            lab = f'<span style="position:absolute;left:0;right:0;top:.005in;font-size:5pt;font-weight:700">{v}</span>' if v % 5 == 0 else ''
            cells += f'<div style="position:relative;width:.17in;height:.17in;border:.7pt solid {GOLDD};background:{GOLDL if v % 5 else "#ffe69a"};margin-right:.012in;color:{GOLDD};text-align:center">{lab}</div>'
        gold += f'<div class="row" style="margin-top:.02in">{cells}</div>'
    xp = f'<div class="lab" style="color:{XPC};margin-top:.07in">XP<span style="font-weight:600;font-size:5.5pt;color:#777;letter-spacing:0;margin-left:.06in">fill the row to reach the level</span></div>'
    steps = [('L3', 2, TIERCOL['II'], 'T-II'), ('L4', 4, TIERCOL['III'], 'T-III'), ('L5', 8, TIERCOL['IV'], 'T-IV'), ('L6', 16, TIERCOL['V'], 'T-V'), ('L7', 26, '#848b89', ''), ('L8', 38, '#444', '')]
    bw = .11
    for n, k, c, t in steps:
        lines = [k] if k <= 26 else [19, 19]
        for li, kk in enumerate(lines):
            cells = ''.join(f'<div style="width:{bw}in;height:{bw}in;border:.8pt solid {c};margin-right:.012in"></div>' for _ in range(kk))
            lab = f'{n} <span style="font-size:4.5pt;font-weight:700">{t}</span>' if li == 0 else ''
            xp += f'<div class="row" style="margin-top:.02in"><div style="width:.5in;font-size:6pt;font-weight:800;color:{c}">{lab}</div>{cells}</div>'
    return hdr('Pencil or dry-erase') + gold + xp + '<div class="note">Level = lineup size. Income +5 + interest + streak. +2 XP each round; 4 gold = 4 XP.</div>'
for name, fn in (('A', A_inner), ('B', B_inner), ('C', C_inner)):
    pass
for name, fn in (('A', A_inner), ('B', B_inner), ('C', C_inner)):
    open(f'{W}/out/PAC_tracker_{name}.html', 'w').write(page(tracker_pos(fn)))
print('ok')
