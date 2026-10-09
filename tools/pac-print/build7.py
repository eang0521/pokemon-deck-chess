import sys
sys.argv = [sys.argv[0]]
from build import TIERCOL, A, W
LV = {0: ('L2', '#848b89', ''), 2: ('L3', TIERCOL['II'], 'TIER II'), 6: ('L4', TIERCOL['III'], 'TIER III'), 14: ('L5', TIERCOL['IV'], 'TIER IV'), 30: ('L6', TIERCOL['V'], 'TIER V'), 56: ('L7', '#5f6663', '')}
def band(x):
    k = max(k for k in LV if k <= x); return k
C, R = 10, 8
CELL = 0.72
X0 = (8.5 - C * CELL) / 2
Y0 = 1.55
GAPR = 0.2
cells, arrows = [], []
pos = {}
for xp in range(71):
    r, c = divmod(xp, C)
    if r % 2 == 1: c = C - 1 - c
    x = X0 + c * CELL; y = Y0 + r * (CELL + GAPR)
    pos[xp] = (x, y)
for xp in range(71):
    x, y = pos[xp]; k = band(xp); name, col, tier = LV[k]
    up = xp in LV and xp > 0
    if up:
        cells.append(f'<div style="position:absolute;left:{x}in;top:{y}in;width:{CELL}in;height:{CELL}in;background:{col};border:2.2pt solid #1d2a29;border-radius:.09in;color:#fff;text-align:center;box-shadow:0 0 0 2pt #fff,0 0 0 3.2pt {col}">'
                     f'<div style="font-size:7pt;font-weight:700;margin-top:.04in;opacity:.95">{xp} XP</div><div style="font-size:15pt;font-weight:800;line-height:1">{name}</div>'
                     f'<div style="font-size:5.5pt;font-weight:700;letter-spacing:.04em;margin-top:.02in">{tier or "LEVEL UP"}</div></div>')
    else:
        bg = col + '33' if xp else '#e8ebea'
        cells.append(f'<div style="position:absolute;left:{x}in;top:{y}in;width:{CELL}in;height:{CELL}in;background:{bg};border:1.2pt solid {col};border-radius:.09in;color:{col if col != "#848b89" else "#555"};text-align:center">'
                     f'<div style="font-size:15pt;font-weight:800;line-height:{CELL}in">{xp}</div>' + ('<div style="position:absolute;left:0;right:0;bottom:.04in;font-size:5.5pt;font-weight:700;color:#555">START · L2</div>' if xp == 0 else '') + '</div>')
# connectors between rows: short arrows at the turn
for r in range(R - 1):
    xp_end = (r + 1) * C - 1
    if xp_end >= 70: break
    x, y = pos[xp_end]
    arrows.append(f'<div style="position:absolute;left:{x + CELL / 2 - .1}in;top:{y + CELL}in;width:.2in;height:{GAPR}in;text-align:center;font-size:10pt;line-height:{GAPR}in;color:#777">▼</div>')
# direction arrows within rows (small chevrons in gaps are skipped; row direction shown by the numbers and ▶/◀ labels)
dirs = ''
for r in range(R):
    y = Y0 + r * (CELL + GAPR) + CELL / 2 - .09
    ch = '▶' if r % 2 == 0 else '◀'
    xx = X0 - .22 if r % 2 == 0 else X0 + C * CELL + .04
    dirs += f'<div style="position:absolute;left:{xx}in;top:{y}in;font-size:9pt;color:#999;width:.18in">{ch}</div>'
legend_rows = ''.join(f'<div style="display:flex;align-items:center;gap:.08in"><div style="width:.28in;height:.2in;border-radius:.04in;background:{LV[k][1]}"></div><b style="width:.3in">{LV[k][0]}</b><span>{("at " + str(k) + " XP") if k else "start (0 XP)"}{(" · unlocks " + LV[k][2].replace("TIER", "Tier")) if LV[k][2] else ""}</span></div>' for k in LV)
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Jost;src:url(file://{A}/ui/Jost-VF.ttf);font-weight:100 900}}
@page{{size:8.5in 11in;margin:0}}*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:8.5in;height:11in}}body{{font-family:Jost,'DejaVu Sans',sans-serif;color:#1d2a29;background:#fff;position:relative}}
</style></head><body>
<div style="position:absolute;left:.6in;top:.5in;font-size:26pt;font-weight:800;letter-spacing:.04em">XP TRACK</div>
<div style="position:absolute;left:.6in;top:1.0in;font-size:9pt;line-height:1.35;color:#444;width:7.3in">Each player puts a cube on their XP, starting on 0. Move it forward <b>2 XP at the end of every round</b>, and <b>4 gold buys 4 XP</b> in the shop. When your cube reaches or passes a level space, you are that level: <b>level = lineup size</b>, and new levels unlock higher tiers in the shop. Follow the numbers: left to right, then right to left on the next row. L8 is at 94 XP, past the end of this track.</div>
{''.join(cells)}{''.join(arrows)}{dirs}
<div style="position:absolute;left:{X0}in;top:{Y0 + R * (CELL + GAPR) - 0.0}in;width:{C * CELL}in;font-size:9pt;line-height:1.5;display:grid;grid-template-columns:1fr 1fr;gap:.02in .3in;margin-top:.1in">{legend_rows}</div>
</body></html>'''
open(f'{W}/out/PAC_xp_track_70.html', 'w').write(html)
print('ok')
