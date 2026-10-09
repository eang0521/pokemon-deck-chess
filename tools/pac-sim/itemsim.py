import random, copy, math, sys, json, collections
from engine import load_cards
from duel import Duel
from lineups import draw_lineup, BUDGET
from items import ITEMS, ORDER

def equip(lineup, keys, idx=None, rng=None):
    L = [copy.copy(c) for c in lineup]
    for c in L: c.items = []
    h = L[idx if idx is not None else rng.randrange(len(L))]
    h.items = list(keys)
    return L

def smoke(n=20):
    cards = load_cards(); rng = random.Random(5); bad = {}
    for k in ORDER:
        for i in range(n):
            la = draw_lineup(cards, rng.choice([3,4,5,6]), rng); lb = draw_lineup(cards, len(la), rng)
            try: Duel(equip(la, [k], rng=rng), lb, random.Random(i)).run()
            except Exception as e: bad[k] = repr(e); break
    return bad
if __name__ == '__main__':
    print(smoke())
