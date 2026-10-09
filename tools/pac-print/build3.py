import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json
sys.path.insert(0, f'{ROOT}/pac-print')
from build import *
rows = json.load(open(f'{ROOT}/pac-print/pool_cards.json'))
def sel(pool): return [r for r in rows if r[17] == pool]
for pool, name in (('add', 'PAC_additional'), ('hatch', 'PAC_hatch'), ('unique', 'PAC_unique'), ('legendary', 'PAC_legendary')):
    rs = sel(pool)
    write(name, pages([card_front(r) for r in rs]))
    write(name + '_BACKS', pages([back(r[0], pool) for r in rs], back=True))
    print(name, len(rs))
