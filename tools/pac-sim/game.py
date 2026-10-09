import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
"""Full-game playtest simulator: 8 bots, 12 rounds, shop, economy, picks, evolution, items, scoring."""
import random, copy, json, collections, statistics as st, sys, os, math
sys.path.insert(0, f'{ROOT}/pac-sim')
from engine import load_cards
from duel import Duel, SYN_TH, level_of
from items import ITEMS
import extra
import duel as _duel
HATCH = os.environ.get('HATCH','0') == '1'
HV = [x.split(',') for x in os.environ.get('HV','II;III;IV').split(';')]
HTRADE = {'II': 0, 'III': 0, 'IV': 0}
if os.environ.get('HTR') == 'half': HTRADE = {'II': 1, 'III': 2, 'IV': 3}
EVOLVE_H = os.environ.get('EVOH','0') == '1'
BABYBOT = int(os.environ.get('BABYBOT','0'))
if HATCH: _duel.BABY_HP = False
_ADJ = json.load(open(f'{ROOT}/pac-data/tweaks_extra.json')) if os.path.exists(f'{ROOT}/pac-data/tweaks_extra.json') else {}

GATE = {'I': 1, 'II': 3, 'III': 4, 'IV': 5, 'V': 6}
TIERS = ['I', 'II', 'III', 'IV', 'V']
TRADE = {'I': 0, 'II': 2, 'III': 4, 'IV': 7, 'V': 14}
import os
XPS = float(os.environ.get('XPSCALE', '0.75'))
XP_CUM = {k: int(round(v * XPS)) for k, v in {2: 0, 3: 2, 4: 8, 5: 18, 6: 40, 7: 74, 8: 126, 9: 198}.items()}
EVOMODE = os.environ.get('EVOMODE', 'shop')
EVO = os.environ.get('EVO', 'full')
PMIN = {'I': 1, 'II': 3, 'III': 5, 'IV': 8, 'V': 15}
BANKK = float(os.environ.get('BANKK', '6'))
def _lost(p, cost):
    return min(3, p.gold // 5) - min(3, max(0, p.gold - cost) // 5)
BONUS = lambda r: 0 if r <= 3 else 1 if r <= 6 else 2 if r <= 9 else 3
NAME2KEY = {v['name']: k for k, v in ITEMS.items()}
_rows = json.load(open(f'{ROOT}/items_core.json'))
_first = list(_rows.values())[0]
CORE_ITEMS = [dict(key=NAME2KEY[r[3]], tier=r[0], price=r[1], copies=r[2]) for r in _first if r[3] in NAME2KEY]


class Player:
    def __init__(s, idx, strat):
        s.idx = idx; s.strat = strat; s.gold = 5; s.xp = 0; s.level = 2; s.cards = []; s.inv = []
        s.points = 20; s.streak = 0; s.last = None; s.stats = collections.Counter(); s.wins = 0

    def trade(s, c): return c.trade if hasattr(c, 'trade') else TRADE[c.tier]


class Game:
    def __init__(s, strats, seed, cards=None):
        s.rng = random.Random(seed)
        allc = cards or load_cards()
        allc = [copy.copy(c) for c in allc]
        for c in allc: c.items = []
        s.cards = allc
        # proxy picks pool: 20% of Core stands in for the Additional / Unique / Legendary pools (not in shop)
        s.rng.shuffle(allc)
        s.picks = collections.defaultdict(list)
        s.deck = collections.defaultdict(list)
        for c in allc:
            if not hasattr(c, 'pool'): s.deck[c.tier].append(c)
        # picks: the real Additional / Unique / Legendary pools
        extras = [copy.copy(c) for c in extra.load_pool(_ADJ)]
        for c in extras:
            c.items = []; c.from_pick = True
            if c.pool == 'add': c.pkey = c.tier; c.price = max(math.ceil(c.value), PMIN.get(c.tier, 1)); c.trade = TRADE[c.tier]
            elif c.pool == 'unique': c.pkey = 'unique'; c.trade = 15; c.price = 15
            else: c.pkey = 'legendary'; c.trade = 30; c.price = 30
            s.picks[c.pkey].append(c)
        for k in s.picks: s.rng.shuffle(s.picks[k])
        s.hatch = {'II': [], 'III': [], 'IV': []}
        if HATCH:
            for c in extra.load_pool(_ADJ, hatch=True):
                if c.pool != 'hatch': continue
                c.types = set(c.types) - {'BABY'}; c.items = []; c.from_pick = True; c.pkey = 'hatch'; c.trade = TRADE[c.tier]; c.price = 0; s.hatch[c.tier].append(c)
            for k in s.hatch: s.rng.shuffle(s.hatch[k])
        allc = allc + extras
        s.fam = collections.defaultdict(list)
        for c in allc: s.fam[c.family].append(c)
        s.core_n = len(allc) - len(extras)
        s.players = [Player(i, st_) for i, st_ in enumerate(strats)]
        s.row = {t: [] for t in TIERS}
        for t in TIERS: s.refill(t)
        s.irow = []
        s.ideck = []
        for it in CORE_ITEMS: s.ideck += [it] * it['copies']
        s.rng.shuffle(s.ideck)
        s.irefill()
        s.log = collections.defaultdict(list); s.turns = []; s.battles = []

    # ---------- shop ----------
    def refill(s, t):
        while len(s.row[t]) < 3:
            if s.deck[t]: s.row[t].append(s.deck[t].pop())
            elif s.picks.get(t): s.row[t].append(s.picks[t].pop())   # empty shop deck: refill from Additional cards of that tier
            else: break

    def irefill(s):
        while len(s.irow) < 4 and s.ideck: s.irow.append(s.ideck.pop())

    # ---------- bot logic ----------
    def types_count(s, cards):
        cnt = collections.Counter(); seen = set()
        for c in cards:
            for t in c.types:
                if (t, c.family) not in seen: seen.add((t, c.family)); cnt[t] += 1
        return cnt

    def score(s, p, c, roster):
        base = c.value
        if p.strat == 'random': return base + s.rng.random() * 3
        cnt = s.types_count(roster)
        syn = 0
        for t in c.types:
            n = cnt[t]
            th = SYN_TH.get(t, [2, 3, 4])
            nxt = [x for x in th if x > n]
            syn += (1.0 if n else 0) + (2.0 if nxt and n + 1 >= nxt[0] else 0)
        if getattr(p, 'idx', 9) < BABYBOT and os.environ.get('BIAS','BABY') in c.types: syn += 4
        return base + 1.2 * syn

    def lineup(s, p):
        best = sorted(p.cards, key=lambda c: -s.score(p, c, p.cards))[:p.level]
        return best

    def maybe_buy(s, p):
        # returns True if the player acted (buy / evolve / churn), False to pass
        cap = p.level + 4
        # evolution first
        for c in sorted(p.cards, key=lambda c: -c.value):
            for h in s.fam[c.family]:
                if h.value > c.value and h.price > 0 and GATE.get(h.tier, 1) <= p.level and (h in s.available() if EVOMODE == 'pool' else (h.tier in s.row and h in s.row[h.tier])):
                    cost = max(0, h.price - (2 * p.trade(c) if EVO == 'dbl' else c.price))
                    if cost <= p.gold and h.value - c.value >= 1.0 and (p.strat != 'synbank' or _lost(p, cost) == 0 or h.value - c.value >= 1.0 + 2 * _lost(p, cost)):
                        s.take(h); p.gold -= cost; p.cards.remove(c); p.cards.append(h); h.items = c.items; c.items = []
                        s.return_card(c); p.stats['evolve'] += 1; p.stats['evo_saved'] += h.price - cost; p.stats['evo_price'] += h.price; return True
        # card purchase
        cands = []
        for t in TIERS:
            if GATE[t] > p.level: continue
            for c in s.row[t]: cands.append(c)
        need = len(p.cards) < p.level
        weakest = min(p.cards, key=lambda c: s.score(p, c, p.cards)) if p.cards else None
        best = None; bs = -1e9
        for c in cands:
            sc = s.score(p, c, p.cards + [c]) - (0 if need or len(p.cards) < cap else 0)
            if need or len(p.cards) < cap:
                cost = c.price
                if cost > p.gold: continue
                gain = sc - (s.score(p, weakest, p.cards) if (weakest and not need) else 0)
                if need or gain > 1.0 + (BANKK * _lost(p, cost) if p.strat == 'synbank' else 0):
                    if gain > bs or best is None and need: bs = gain; best = (c, None, cost)
            if weakest and not need and len(p.cards) >= cap:
                cost = max(0, c.price - p.trade(weakest))
                if cost > p.gold: continue
                gain = sc - s.score(p, weakest, p.cards)
                if gain > 1.5 + (BANKK * _lost(p, cost) if p.strat == 'synbank' else 0) and gain > bs: bs = gain; best = (c, weakest, cost)
        if best is None and need:
            aff = [c for c in cands if c.price <= p.gold]
            if aff: c = max(aff, key=lambda c: s.score(p, c, p.cards)); best = (c, None, c.price)
        if best:
            c, out, cost = best
            s.row[c.tier].remove(c); s.refill(c.tier); p.gold -= cost; p.cards.append(c)
            if out is not None:
                p.cards.remove(out); s.return_card(out); p.stats['tradein'] += 1
            p.stats['bought'] += 1; return True
        # items
        if p.gold >= 3 and any(len(c.items) < 3 for c in p.cards):
            opts = [it for it in s.irow if GATE[it['tier']] <= p.level and it['price'] <= p.gold - (0 if len(p.cards) >= p.level else 99) and (p.strat != 'synbank' or _lost(p, it['price']) == 0)]
            if opts:
                it = max(opts, key=lambda i: i['price'] + s.rng.random()) if p.strat != 'random' else s.rng.choice(opts)
                _ok = [c for c in p.cards if len(c.items) < 3 and (not ITEMS[it['key']]['flags'].get('evo_only') or any(h.value > c.value for h in s.fam[c.family]))]
                if _ok:
                    tgt = s.rng.choice(_ok)
                    s.irow.remove(it); s.irefill(); p.gold -= it['price']; tgt.items.append(it['key']); p.stats['item'] += 1
                    return True
        return False

    def available(s):
        out = set()
        for t in TIERS: out.update(s.deck[t]); out.update(s.row[t])
        for k in s.picks: out.update(s.picks[k])
        return out

    def take(s, c):
        if getattr(c, 'from_pick', False): s.picks[c.pkey].remove(c)
        elif c in s.row[c.tier]: s.row[c.tier].remove(c); s.refill(c.tier)
        else: s.deck[c.tier].remove(c)

    def return_card(s, c):
        c.items = []
        if getattr(c, 'from_pick', False): s.picks[c.pkey].append(c)
        else: s.deck[c.tier].insert(0, c)

    def buy_xp(s, p):
        spend = 0
        if p.strat == 'random': return
        if p.strat == 'lvl':
            while p.level < 6 and p.gold >= 4 and len(p.cards) >= min(p.level, 3) and p.stats['xpbuy'] < 12:
                p.gold -= 4; s.add_xp(p, 4); p.stats['xpbuy'] += 1
            return
        # keep 10 gold for interest, convert the rest into XP while below level 7
        keep = 15 if p.strat == 'synbank' else 10
        while p.level < 7 and p.gold >= (keep + 4 if p.level >= 4 else 4 + (0 if len(p.cards) >= p.level else 99)):
            if p.level <= 3 and len(p.cards) < p.level: break
            p.gold -= 4; s.add_xp(p, 4); p.stats['xpbuy'] += 1

    def add_xp(s, p, x):
        p.xp += x
        while p.level < 9 and p.xp >= XP_CUM[p.level + 1]: p.level += 1

    def pick(s, p, tier, label):
        pool = s.picks[label if label in ('unique', 'legendary') else {'II': 'II', 'III': 'III', 'IV': 'IV'}[tier]]
        if len(pool) < 3: return
        deal = [pool.pop() for _ in range(3)]
        chosen = max(deal, key=lambda c: s.score(p, c, p.cards))
        for c in deal:
            if c is not chosen: pool.insert(0, c)
        p.cards.append(chosen); p.stats['pick'] += 1

    # ---------- a round ----------
    def play(s):
        n = len(s.players); seats = list(range(n))
        for r in range(1, 13):
            for p in s.players:
                interest = min(3, p.gold // 5)
                streak = 0 if abs(p.streak) < 2 else 1 if abs(p.streak) == 2 else 2 if abs(p.streak) == 3 else 3
                inc = 0 if r == 1 else 5 + interest + streak
                if r > 1: p.stats['interest'] += interest; p.stats['streakg'] += streak
                if r > 1: p.gold += inc
                p.stats['income'] += inc
                s.add_xp(p, 2 if r > 1 else 0)
            if r == 2:
                for p in s.players: s.pick(p, 'II', 'add')
            if r == 5:
                for p in s.players: s.pick(p, 'III', 'add')
            if r == 6:
                for p in s.players: s.pick(p, 'V', 'unique')
            if r == 8:
                for p in s.players: s.pick(p, 'IV', 'add')
            if r == 9:
                for p in s.players: s.pick(p, 'V', 'legendary')
            for p in s.players: s.buy_xp(p)
            # shop: worst-first, one action each, until all pass
            passes = 0; safety = 0
            while passes < n and safety < 400:
                safety += 1; passes = 0
                order = sorted(s.players, key=lambda p: (p.points, p.level, s.rng.random()))
                for p in order:
                    if s.maybe_buy(p): s.turns.append(r)
                    else: passes += 1
            for p in s.players: s.buy_xp(p)
            for p in s.players: p.stats['gold_left_r%d' % r] = p.gold
            # pairings: rotating round robin
            rot = [seats[0]] + seats[1:][-(r - 1) % (n - 1):] + seats[1:][:-(r - 1) % (n - 1)] if (r - 1) % (n - 1) else seats[:]
            for i in range(n // 2):
                a, b = s.players[rot[i]], s.players[rot[n - 1 - i]]
                if s.rng.random() < .5: a, b = b, a
                la = s.lineup(a); lb = s.lineup(b)
                la = s.rng.sample(la, len(la)); lb = s.rng.sample(lb, len(lb))
                if a.points != b.points or a.gold != b.gold:
                    pass
                _duel.STREAKS = [max(0, -a.streak), max(0, -b.streak)]
                res = Duel(la, lb, s.rng).run()
                s.battles.append((r, res['rounds'], len(la), len(lb), res['winner'], res['left']))
                for pl, side in ((a, 0), (b, 1)):
                    cnt = s.types_count(la if side == 0 else lb)
                    act = [t for t, k in cnt.items() if level_of(t, k) > 0]
                    pl.stats['active_syn'] += len(act); pl.stats['syn_n'] += 1
                    pl.stats['max_syn_lv'] = max(pl.stats['max_syn_lv'], max([level_of(t, k) for t, k in cnt.items()] + [0]))
                if res['winner'] is None:
                    a.streak = b.streak = 0; a.last = b.last = None; continue
                w, l = (a, b) if res['winner'] == 0 else (b, a)
                pts = res['left'] + BONUS(r)
                w.points += pts; l.points -= pts; w.wins += 1
                w.streak = w.streak + 1 if w.streak > 0 else 1
                l.streak = l.streak - 1 if l.streak < 0 else -1
                if HATCH and (os.environ.get("HEVEN","0")!="1" or l.streak % 2 == 0):
                    cl = s.types_count(la if l is a else lb); bl = level_of('BABY', cl['BABY'])
                    if bl:
                        mine = [c_ for c_ in l.cards if getattr(c_, 'pkey', '') == 'hatch' and c_.tier != 'IV']
                        if bl >= 2 and mine and EVOLVE_H:
                            old_ = min(mine, key=lambda c_: ['II', 'III'].index(c_.tier))
                            nt = {'II': 'III', 'III': 'IV'}[old_.tier]
                            nxt = [c_ for c_ in s.hatch[nt] if c_.family == old_.family]
                            if nxt:
                                s.hatch[nt].remove(nxt[0]); l.cards[l.cards.index(old_)] = nxt[0]; s.hatch[old_.tier].append(old_); l.stats['hatch_evo'] += 1; continue
                        tk = ['II', 'II', 'III'][bl - 1] if EVOLVE_H else ['II', 'III', 'IV'][bl - 1]
                        dk = s.hatch[tk]
                        if dk: c_ = dk.pop(); l.cards.append(c_); l.stats['hatch'] += 1
        return s

    def result(s):
        return [(p.idx, p.strat, p.points, p.wins, p.level, dict(p.stats)) for p in s.players]


if __name__ == '__main__':
    g = Game(['syn'] * 8, 1).play()
    for r in g.result(): print(r[:5])
