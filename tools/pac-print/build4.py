import math, sys
sys.argv=[sys.argv[0]]
from build import ic, page_html, TIERCOL, W
CSS = '''@page{size:8.5in 11in;margin:0}*{box-sizing:border-box}body{margin:0;width:8.5in;height:22in;position:relative;font-family:Arial,Helvetica,sans-serif;overflow:hidden}
.i{width:100%;height:100%;object-fit:contain}'''
# ---------------- status tokens
STAT = ['BURN','POISONED','PARALYSIS','FLINCH','SLEEP','FREEZE','CONFUSION','CHARM','WOUND','ARMOR_BREAK','FATIGUE','SILENCE','PROTECT','CURSE','LOCKED']
toks = [(s,'#fff') for s in STAT for _ in range(5)] + [('SWARM','#e6f2c4')]*24
toks += [('CRIT','#ffe9a8')]*99
P, D = 0.88, 0.82
cells = []
for k,(n,bg) in enumerate(toks):
    pg, kk = divmod(k, 99); r, c = divmod(kk, 9)
    x = (8.5-9*P)/2 + c*P + (P-D)/2; y = (11-11*P)/2 + r*P + (P-D)/2
    lab = 'CRIT TOKEN' if n=='CRIT' else n.replace('_',' ')
    cells.append(f'<div style="position:absolute;left:{x}in;top:{y+pg*11}in;width:{D}in;height:{D}in;border-radius:50%;border:1.2px solid #444;background:{bg};text-align:center">'
                 f'<div style="position:absolute;left:.19in;top:.09in;width:.44in;height:.44in">{ic(n)}</div>'
                 f'<div style="position:absolute;left:0;right:0;top:.54in;font-size:5.6pt;font-weight:800;color:#333">{lab}</div></div>')
open(f'{W}/out/PAC_tokens.html','w').write(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(cells)}</body></html>')
# ---------------- XP spiral
LV = {2:('L3','TIER II'),6:('L4','TIER III'),14:('L5','TIER IV'),30:('L6','TIER V'),56:('L7',''),94:('L8','')}
LVC = {2:'II',6:'III',14:'IV',30:'V',56:'I',94:'I'}
CELL, STEP = 0.46, 0.5
CX, CY, RX0, RY0 = 4.25, 5.5, 0.55, 0.75
GAP = 0.8  # radial gain per turn in x
def pt(th):
    r = th/(2*math.pi)*GAP
    return CX + (RX0+r)*math.cos(th), CY + (RY0+r*1.3)*math.sin(th)
pts=[]; th=0.0; last=pt(0); pts.append(last)
while len(pts)<=100:
    th+=0.002; p=pt(th)
    if math.hypot(p[0]-last[0],p[1]-last[1])>=STEP: pts.append(p); last=p
print('max x extent',max(abs(p[0]-CX) for p in pts),'max y',max(abs(p[1]-CY) for p in pts))
# check clearance
mind=min(math.hypot(a[0]-b[0],a[1]-b[1]) for i,a in enumerate(pts) for j,b in enumerate(pts) if j>i+8)
print('min nonadjacent dist',round(mind,3))
h=[]
for xp,(x,y) in enumerate(pts):
    lv = LV.get(xp)
    if lv:
        col = TIERCOL[LVC[xp]] if xp<=30 else '#444'
        h.append(f'<div style="position:absolute;left:{x-CELL/2}in;top:{y-CELL/2}in;width:{CELL}in;height:{CELL}in;border-radius:50%;background:{col};border:1.5px solid #222;color:#fff;text-align:center;font-weight:800;line-height:1">'
                 f'<div style="font-size:9pt;margin-top:.07in">{lv[0]}</div><div style="font-size:5.6pt;font-weight:600">{xp}</div></div>')
    else:
        h.append(f'<div style="position:absolute;left:{x-CELL/2}in;top:{y-CELL/2}in;width:{CELL}in;height:{CELL}in;border-radius:50%;background:#fff;border:1px solid #888;color:#555;text-align:center;font-size:7.5pt;font-weight:700;line-height:{CELL}in">{xp}</div>')
legend = ('<div style="position:absolute;left:.5in;top:.5in;font-size:9pt;line-height:1.4;color:#222"><div style="font-size:15pt;font-weight:800">XP TRACK</div>'
 'Each player puts a cube on their XP.<br>+2 XP at the end of every round.<br>Buy XP: 4 gold = 4 XP.<br>Start at 0 (the center).</div>'
 '<div style="position:absolute;right:.5in;bottom:.5in;font-size:9pt;line-height:1.5;color:#222;text-align:left"><b>LEVELS</b><br>'
 'L3 at 2 XP · unlocks Tier II<br>L4 at 6 XP · unlocks Tier III<br>L5 at 14 XP · unlocks Tier IV<br>L6 at 30 XP · unlocks Tier V<br>L7 at 56 XP<br>L8 at 94 XP<br>L9 at 148 XP (off the track)<br>Level = lineup size.</div>')
open(f'{W}/out/PAC_xp_tracker.html','w').write(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS.replace('22in','11in')}</style></head><body>{"".join(h)}{legend}</body></html>')
