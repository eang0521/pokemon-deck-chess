import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, random, copy
sys.path.insert(0,f'{ROOT}/pac-sim')
import engine, extra, duel
from items import ITEMS
adj = json.load(open(f'{ROOT}/pac-data/tweaks_extra.json'))
core = engine.load_cards(); pool = extra.load_pool(adj, hatch=True)
allc = core + pool
hold = [k for k,v in ITEMS.items() if not v['flags'].get('unholdable') and k!='GOLD_BOW']
rng = random.Random(int(sys.argv[3]) if len(sys.argv)>3 else 7)
N = int(sys.argv[1]) if len(sys.argv)>1 else 80; R = int(sys.argv[2]) if len(sys.argv)>2 else 200
FOCUS = set(filter(None, _os.environ.get('PAC_FOCUS', '').split(',')))
out = []
for m in range(N):
    lv = rng.choice([3,4,5,6,7])
    def lineup():
        idx = rng.sample(range(len(allc)), lv)
        if FOCUS:      # PAC_FOCUS=ABILITY,ABILITY...: make most slots cards with those abilities (targeted parity)
            fi = [i for i, c in enumerate(allc) if c.ability.split('#')[0] in FOCUS]
            idx = rng.sample(fi, min(len(fi), lv - 1)) + rng.sample(range(len(allc)), lv - min(len(fi), lv - 1))
        items = [[rng.choice(hold) for _ in range(rng.choice([0,0,1,2,3]))] for _ in idx]
        return idx, items
    la, ia = lineup(); lb, ib = lineup()
    wins = [0,0,0]; left = 0; rounds = 0
    for r in range(R):
        a = []; b = []
        for i, its in zip(la, ia): c = copy.copy(allc[i]); c.items = list(its); a.append(c)
        for i, its in zip(lb, ib): c = copy.copy(allc[i]); c.items = list(its); b.append(c)
        res = duel.Duel(a, b, random.Random(1000*m + r)).run()
        w = res['winner']; wins[2 if w is None else w] += 1; left += res['left']; rounds += res['rounds']
    out.append(dict(la=la, ia=ia, lb=lb, ib=ib, py=dict(wins=wins, left=left/R, rounds=rounds/R)))
json.dump(out, open(__import__('os').path.join(__import__('tempfile').gettempdir(),'parity.json'),'w'))
print('ok', len(out))
