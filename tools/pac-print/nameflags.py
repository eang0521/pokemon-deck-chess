import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json
sys.path.insert(0,f'{ROOT}/pac-print')
import build as B
rows = [r for r in B.CARDS]
for r in rows: B.card_front(r)
import json as J
pr = J.load(open(f'{ROOT}/pac-print/pool_cards.json'))
for r in pr: B.card_front(r)
fl = [x for x in B.NAMEFLAG if x[3]==2 or x[2] < 10.5]
J.dump(B.NAMEFLAG, open('/tmp/nameflag.json','w'))
print(len(B.NAMEFLAG), len(fl))
