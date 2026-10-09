import random, copy, json, sys, time, collections, statistics as st
from multiprocessing import Pool
from engine import load_cards
from duel import Duel
from lineups import draw_lineup, BUDGET
from items import ITEMS, ORDER
from itemsim import equip
cards = load_cards(); BY = {c.name: c for c in cards}
LEVELS = (4, 5, 6)
FAM = collections.defaultdict(list)
for _c in cards: FAM[_c.family].append(_c)
def res(la, lb, seed):
    r = Duel(la, lb, random.Random(seed)).run()
    return 1.0 if r['winner'] == 0 else 0.0 if r['winner'] == 1 else .5
def item_type(k):
    f = ITEMS[k]['flags']; return f.get('type') or f.get('gem')
def draw_pair(rng, lv, typ, evo=False):
    for _ in range(80):
        la = draw_lineup(cards, lv, rng); lb = draw_lineup(cards, lv, rng)
        if evo:
            ok = [i for i, c in enumerate(la) if any(h.value > c.value for h in FAM[c.family])]
            if ok: return la, lb, rng.choice(ok)
            continue
        la = draw_lineup(cards, lv, rng); lb = draw_lineup(cards, lv, rng)
        if typ is None: return la, lb, rng.randrange(lv)
        have = [i for i, c in enumerate(la) if typ in c.types]
        if 1 <= len(have) <= 3:
            no = [i for i in range(lv) if typ not in la[i].types]
            if no: return la, lb, rng.choice(no)
    return la, lb, rng.randrange(lv)
def work(args):
    key, n = args
    typ = item_type(key); rng = random.Random(hash(key) % 100000 + 1)
    diffs = []
    for i in range(n):
        lv = LEVELS[i % 3]
        la, lb, h = draw_pair(rng, lv, typ, bool(ITEMS[key]['flags'].get('evo_only')))
        w0 = res(la, lb, i); w1 = res(equip(la, [key], idx=h), lb, i)
        diffs.append(w1 - w0)
    m = st.mean(diffs); se = st.pstdev(diffs) / len(diffs) ** .5
    return key, m, se
def slope_work(args):
    lv, delta, n, seed = args
    rng = random.Random(seed); w = 0
    for i in range(n):
        la = draw_lineup(cards, lv, rng, budget=BUDGET[lv] + delta); lb = draw_lineup(cards, lv, rng)
        w += res(la, lb, i)
    return lv, delta, w / n
if __name__ == '__main__':
    N = int(sys.argv[1]); t = time.time()
    keys = [k for k in ORDER if not any(x in ITEMS[k]['flags'] for x in ('slot', 'econ_income', 'econ_churn', 'perm_fire'))]
    with Pool(2) as p:
        sl = p.map(slope_work, [(lv, d, 4000, 300 + lv + d) for lv in LEVELS for d in (0, 6, 12)])
        out = p.map(work, [(k, N) for k in keys], chunksize=1)
    json.dump(dict(slope=sl, lift=out, n=N), open('itemlift3.json', 'w')); print('done', time.time() - t)
