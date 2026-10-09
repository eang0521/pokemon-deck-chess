import random, copy, json, sys, time
from multiprocessing import Pool
from engine import load_cards
from duel import Duel
from lineups import draw_lineup, BUDGET
from items import ITEMS, ORDER
from itemsim import equip
cards = load_cards()
LEVELS = (4, 5, 6)

def make_pairs(n, seed):
    rng = random.Random(seed); out = []
    for i in range(n):
        lv = LEVELS[i % 3]
        la = draw_lineup(cards, lv, rng); lb = draw_lineup(cards, lv, rng)
        out.append((lv, [c.name for c in la], [c.name for c in lb], rng.randrange(lv), rng.random() < .5, i))
    return out
BY = {c.name: c for c in cards}
def res(la, lb, seed, a_first):
    r = Duel(la, lb, random.Random(seed)).run()
    return 1.0 if r['winner'] == 0 else 0.0 if r['winner'] == 1 else .5

def work(args):
    key, pairs = args
    tot = 0; base = 0
    for lv, na, nb, h, _, i in pairs:
        la = [BY[x] for x in na]; lb = [BY[x] for x in nb]
        w0 = res(la, lb, i, True)
        w1 = res(equip(la, [key], idx=h), lb, i, True)
        base += w0; tot += w1
    return key, tot / len(pairs), base / len(pairs)

def slope_work(args):
    lv, delta, n, seed = args
    rng = random.Random(seed); w = 0
    for i in range(n):
        la = draw_lineup(cards, lv, rng, budget=BUDGET[lv] + delta); lb = draw_lineup(cards, lv, rng)
        w += res(la, lb, i, True)
    return lv, delta, w / n

if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    pairs = make_pairs(N, 777); t = time.time()
    keys = [k for k in ORDER if not any(x in ITEMS[k]['flags'] for x in ('slot', 'econ_income', 'econ_churn', 'perm_fire'))]
    with Pool(2) as p:
        sl = p.map(slope_work, [(lv, d, 1500, 100 + lv + d) for lv in LEVELS for d in (4, 8)])
        out = p.map(work, [(k, pairs) for k in keys], chunksize=1)
    json.dump(dict(slope=sl, lift=out, n=N), open('itemlift1.json', 'w'))
    print('done', time.time() - t)
