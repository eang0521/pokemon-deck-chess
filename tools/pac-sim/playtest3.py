import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, sys, collections, statistics as st, time
sys.path.insert(0,f'{ROOT}/pac-sim')
import game as GM
from game import *
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
agg = collections.defaultdict(list); src = collections.Counter(); tot = 0; blen = collections.defaultdict(list); tv = collections.Counter()
seat = collections.defaultdict(list); spread = []; lvl = collections.Counter(); pw = collections.defaultdict(list); gl = collections.defaultdict(list)
t0 = time.time()
for g in range(N):
    G = Game([os.environ.get('STRAT','syn')] * 8, 300 + g).play()
    pts = [p.points for p in G.players]; spread.append(st.pstdev(pts))
    for p in G.players:
        seat[p.idx].append(p.points); lvl[p.level] += 1
        for k in ('evolve', 'tradein', 'item', 'pick', 'bought', 'xpbuy', 'evo_saved', 'evo_price'): agg[k].append(p.stats[k])
        agg['active_syn'].append(p.stats['active_syn'] / max(1, p.stats['syn_n']))
        for c in G.lineup(p):
            tot += 1; src[getattr(c, 'pkey', 'core') if getattr(c, 'from_pick', False) else 'core'] += 1; tv[c.tier] += 1
        for r in range(1, 13): gl[r].append(p.stats['gold_left_r%d' % r])
        n_pick = sum(1 for c in G.lineup(p) if getattr(c, 'from_pick', False)); pw[n_pick].append(p.points)
    for (r, rounds, la, lb, w, lf) in G.battles: blen[r].append(rounds * 2)
print('games', N, 'time', round(time.time() - t0))
print({k: round(st.mean(v), 2) for k, v in agg.items()})
print('final lineup source share', {k: round(v / tot, 3) for k, v in src.items()}, 'tier mix', {k: round(v / tot, 2) for k, v in tv.items()})
print('points by # pick cards in final lineup', {k: (len(v), round(st.mean(v), 1)) for k, v in sorted(pw.items())})
print('level dist', dict(lvl)); print('seat pts', {k: round(st.mean(v), 1) for k, v in seat.items()}, 'sd', round(st.mean(spread), 1))
print('battle turns', {r: round(st.mean(v), 1) for r, v in blen.items()})
print('gold left', {r: round(st.mean(v), 1) for r, v in gl.items()})
