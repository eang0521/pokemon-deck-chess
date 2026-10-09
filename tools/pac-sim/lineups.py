import random, math
from engine import load_cards
GATE = {'I': 1, 'II': 3, 'III': 4, 'IV': 5, 'V': 6}
BUDGET = {2: 5, 3: 12, 4: 20, 5: 35, 6: 55}
def draw_lineup(cards, level, rng, budget=None, must=None):
    budget = BUDGET[level] if budget is None else budget
    elig = [c for c in cards if GATE[c.tier] <= level]
    chosen = []; left = budget
    if must is not None:
        chosen.append(must); left -= must.price
    pool = elig[:]; rng.shuffle(pool)
    for c in pool:
        if len(chosen) == level: break
        if c is must or c in chosen: continue
        slots_after = level - len(chosen) - 1
        if c.price + slots_after * 1 <= left:
            chosen.append(c); left -= c.price
    # fill with cheapest if short
    cheap = sorted([c for c in elig if c not in chosen], key=lambda c: c.price)
    while len(chosen) < level and cheap: chosen.append(cheap.pop(0))
    return chosen

POLICIES = {
    'random': lambda L, rng: rng.sample(L, len(L)),
    'strong_first': lambda L, rng: sorted(L, key=lambda c: -c.price),
    'strong_last': lambda L, rng: sorted(L, key=lambda c: c.price),
    'fast_first': lambda L, rng: sorted(L, key=lambda c: -c.spd0),
    'slow_first': lambda L, rng: sorted(L, key=lambda c: c.spd0),
    'tanks_first': lambda L, rng: sorted(L, key=lambda c: -(c.hp0 + 2 * c.def0 + 2 * c.sdef0)),
    'hitters_first': lambda L, rng: sorted(L, key=lambda c: -c.atk0),
}
