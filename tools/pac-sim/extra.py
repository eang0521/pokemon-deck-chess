import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
"""Cards for the pick pools (Additional, Unique, Legendary): stats, tiers, generated + budget-scaled powers."""
import csv, math, collections, json, sys
sys.path.insert(0, f'{ROOT}/pac-sim')
import genpower as G
import engine
from engine import Card, Raw, SCALE, tr, PW
from duel import APM

DATA = f'{ROOT}/pac-data/'
COST = {'COMMON': 1, 'UNCOMMON': 2, 'RARE': 3, 'EPIC': 4, 'ULTRA': 5}
MULT = {1: 1.0, 2: 2.5, 3: 6.25}
BUDGET = {'I': 2.5, 'II': 5.0, 'III': 6.5, 'IV': 8.0, 'V': 14.0, 'U': 17.0, 'L': 21.0}
TWEAK = DATA + 'tweaks_extra.json'
HADJ = json.load(open(DATA + 'tweaks_extra_hp.json')) if __import__('os').path.exists(DATA + 'tweaks_extra_hp.json') else {}
POOLTWEAK = {'hatch': dict(hp=1.0, atk=1.0, bud=1.0), 'add': dict(hp=1.0, atk=1.0, bud=1.0), 'unique': dict(hp=1.0, atk=1.0, bud=1.0), 'legendary': dict(hp=1.0, atk=1.0, bud=1.0)}
if __import__('os').path.exists(DATA + 'pooltweaks.json'): POOLTWEAK.update(json.load(open(DATA + 'pooltweaks.json')))

def tier_of(v):
    return 'I' if v < 2.25 else 'II' if v < 5 else 'III' if v < 7 else 'IV' if v < 13 else 'V'

class _Stub:
    def __init__(s, maxhp, hp=None):
        s.maxhp = maxhp; s.hp = hp if hp is not None else maxhp; s.shield = 0; s.st = collections.defaultdict(int); s.boosts = 0; s.cycle = 0
        s.side = type('S', (), {'fallen': 0})()
    def neg(s): return False
    def eff(s, k): return 1
    def lv(s, t): return 0

CAP = {'spd': 2, 'atk': 3, 'def': 3, 'sdef': 3, 'ap': 3}
def scale_parts(parts, f):
    out = []
    r = lambda x: max(1, int(x * f + 0.5))
    for p in parts:
        k = p[0]
        if k in ('S', 'T', 'P'): out.append((k, min(24, r(p[1]))) + p[2:])
        elif k == 'dyn': out.append(tuple(p) if p[1] == 'top3' else ('dyn', p[1], round(p[2] * f, 1), p[3]))   # top3 (Judgment) is a fixed rule, never budget-scaled
        elif k == 'drain': out.append(('drain', min(24, r(p[1])), p[2]))
        elif k == 'delay': out.append(('delay', p[1], r(p[2])))
        elif k in ('shield', 'heal', 'mhp'): out.append((k, r(p[1])) + tuple(p[2:]))
        elif k == 'buff': out.append(('buff', p[1], min(CAP.get(p[1], 3), r(p[2]))))
        elif k == 'carry': out.append(('carry', p[1], p[2] if p[1] == 'revive' else min(2, r(p[2]))))
        elif k == 'selfhurt' and p[1] in ('amt',): out.append(('selfhurt', 'amt', r(p[2])))
        else: out.append(p)
    return out

def make_power(ab, stars, c, budget):
    role, parts, apmode, flagged = G.make(ab, stars, c)
    stub_me, stub_foe = _Stub(max(3, c.hpc)), _Stub(20)
    best = None
    for f in [x / 20 for x in range(5, 80)]:
        sp = scale_parts(parts, f)
        v = G.value_of(G.opsfn(sp, c)(None, c, stub_me, stub_foe))
        if best is None or abs(v - budget) < abs(best[1] - budget) - 1e-9: best = (f, v, sp)
    f, v, sp = best
    if v < 0.7 * budget and not any(p[0] in ('S', 'T', 'P', 'drain', 'dyn', 'delay') for p in sp):
        sp = [('S', max(1, int((budget - v) / 1.0 + 0.5)), False)] + sp
    text = G.render(sp, apmode, c)
    return role, text, G.opsfn(sp, c), apmode, flagged, v, f

def load_pool(adj=None, hadj=None, hatch=False):
    global HADJ
    if hadj is not None: HADJ = hadj
    allp = list(csv.DictReader(open(DATA + 'pokemons-data.csv')))
    coreset = {(x['Index'], x['Name']) for x in csv.DictReader(open(DATA + 'core-value-tiers.csv'))}
    cards = []
    adj = adj or {}
    _rm = set(json.load(open(DATA + 'removed.json')))
    for p in allp:
        if (p['Index'], p['Name']) in coreset or p['Name'] in _rm: continue
        cat = p['Category']
        if cat == 'UNIQUE': pool = 'unique'
        elif cat == 'LEGENDARY': pool = 'legendary'
        elif cat in COST: pool = 'add'
        elif cat == 'HATCH' and hatch:
            if p['Family'] == 'SCATTERBUG' and p['Tier'] == '3' and p['Name'] != 'VIVILLON': continue
            pool = 'hatch'
        else: continue
        stars = max(1, min(3, int(p['Tier'])))
        c = Raw()
        c.hp, c.atk, c.defn, c.sdef, c.spd, c.pp = [int(p[k]) for k in ('HP', 'Attack', 'Defense', 'Special Defense', 'Speed', 'Max PP')]
        pt = POOLTWEAK[pool]
        c.hpc = max(3, round(c.hp / SCALE['hp'] * pt['hp'])); c.atkc = max(1, round(c.atk / SCALE['atk'] * pt['atk']))
        types = [p[f'Type {i}'] for i in range(1, 5) if p[f'Type {i}']]
        if pool == 'hatch': types = [t for t in types if t != 'BABY']
        if pool == 'add':
            val = COST[cat] * MULT[stars]; nat = tier_of(val)
            tier = nat
            bud_key = tier
        elif pool == 'hatch':
            tier = {1: 'II', 2: 'III', 3: 'IV'}[stars]; val = {'II': 3.0, 'III': 5.0, 'IV': 8.0}[tier]; bud_key = tier
        else:
            val = 18.75 if pool == 'unique' else 31.25; tier = 'UNIQUE' if pool == 'unique' else 'LEGENDARY'; bud_key = 'U' if pool == 'unique' else 'L'
        ab = p['Ability']
        k = adj.get(p['Name'], 1.0)
        budget = BUDGET[bud_key] * pt['bud'] * k
        h = HADJ.get(p['Name'], 0)
        c.hpc = max(3, c.hpc + h); c.atkc = max(1, c.atkc + round(h / 6))
        role, text, ofn, apm, flagged, v, f = make_power(ab, stars, c, budget)
        if p['Name'] == 'MINIOR':
            role2, text2, ofn2, apm2, fl2, v2, f2 = make_power('SHIELDS_UP', stars, c, budget)
            _a, _b = ofn, ofn2
            ofn = (lambda a, b: (lambda vv, raw, me, foe: (a if me.casts % 2 == 1 else b)(vv, raw, me, foe)))(_a, _b)
            text = 'SHIELDS DOWN: ' + text + ' SHIELDS UP: ' + text2 + ' Alternates each cast, starting with Shields Down.'
        if p['Name'] == 'MIMIKYU': text += ' The first time a hit leaves it at half HP or less, it is busted: +2 ATK and PROTECT for 1 turn.'
        PTXT = {'HERACROSS': 'GUTS: +2 ATK while it has a negative status.', 'ZANGOOSE': 'TOXIC BOOST: takes half poison damage and has +2 ATK while poisoned.',
                'DURANT': 'Its basic attacks deal +1 TRUE per other BUG in your lineup.', 'KOMALA': 'COMATOSE: immune to burn, poison, freeze and paralysis.',
                'SPINDA': 'Immune to confusion. After attacking a confused foe it deals +2 SPECIAL.', 'PINCURCHIN': 'When hit by SPECIAL damage, the attacker is PARALYZED (1 turn).',
                'SCRAGGY': 'MOXIE: +1 ATK after each KO.', 'SCRAFTY': 'MOXIE: +1 ATK after each KO.',
                'GLIGAR': 'The first time poison would hurt it each battle, it heals that much instead.', 'GLISCOR': 'The first time poison would hurt it each battle, it heals that much instead.',
                'REGIGIGAS': 'SLOW START: -2 speed until it first casts, then +2 speed and +2 ATK.', 'KARTANA': 'BEAST BOOST: +1 ATK after each KO.',
                'NIHILEGO': 'BEAST BOOST: +2 AP after each KO.', 'MAGEARNA': 'SOUL HEART: after each KO gain +2 AP and +1 charge.'}
        if p['Name'] in PTXT: text += ' ' + PTXT[p['Name']]
        key = f"{ab}#{p['Name']}"
        PW[key] = ofn; APM[key] = apm if apm != 'first' else 'first'
        if apm == 'none': APM[key] = 'none'
        card = Card(dict(name={'MAUSHOLD_FOUR': 'Maushold'}.get(p['Name'], p['Name'].title().replace('_', ' ')), tier=tier, pool=pool, stars=stars, value=val, price=0, types=set(types), torder=types,
                         family=p['Family'], raw=c, ability=key, v=[], role=role, text=text, flagged=flagged, abname={'MINIOR': 'Shields'}.get(p['Name'], tr['ability'].get(ab, ab)), dex=p['Index'],
                         hp0=c.hpc, atk0=c.atkc, def0=max(0, round(c.defn / SCALE['df'])), sdef0=max(0, round(c.sdef / SCALE['df'])),
                         spd0=max(1, round(c.spd / SCALE['spd'])), ppmax=max(2, round(c.pp / SCALE['pp'])), pv=v, pf=f))
        cards.append(card)
    return cards

if __name__ == '__main__':
    cs = load_pool()
    print(len(cs), collections.Counter((c.pool, c.tier) for c in cs), sum(c.flagged for c in cs))
    import random
    for c in random.sample(cs, 12): print(c.pool, c.tier, c.name, c.hp0, c.atk0, c.def0, c.sdef0, c.spd0, c.ppmax, '|', c.abname, '|', c.text)
