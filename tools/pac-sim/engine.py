import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
"""PAC board game duel engine (draft rules, deterministic given lineups + choices)."""
import csv, json, re, math, random, collections

DATA = f'{ROOT}/pac-data/'
LOC = f'{ROOT}/keldaancommunity/pokemonautochess/app/public/dist/client/locales/en/translation.json'
tr = json.load(open(LOC))

# ---------------- scale (provisional, tunable) ----------------
SCALE = dict(hp=10, atk=5, df=7, spd=7, spd_mode='div', pp=35, flat=10, pa=6)
def setscale(**k): SCALE.update(k)
def D(x): return max(1, int(x / SCALE['flat'] + 0.5))
def PA(p, base): return max(1, int(p / 100 * base / SCALE['pa'] + 0.5))
def S(x): return min(3, max(1, int(x / 3 + 0.5)))
def AT(x): return max(1, int(x / 5 + 0.5))
def SP(x): return max(1, int(x / SCALE['spd'] + 0.5))
def ceil(x): return int(math.ceil(x))

def parse_arrays(desc):
    out = []
    for m in re.findall(r'\[([^\]]*)\]', desc):
        nums = []
        for t in m.split(','):
            try: nums.append(float(t.strip()))
            except ValueError: pass
        if nums: out.append(nums)
    return out
def resolve(ab, stars):
    return [a[min(stars - 1, len(a) - 1)] for a in parse_arrays(tr['ability_description'].get(ab, ''))]

NEG = ('burn', 'poison', 'para', 'flinch', 'sleep', 'freeze', 'confuse', 'charm', 'wound', 'armor', 'fatigue', 'locked')

# ---------------- powers: ops built at cast time ----------------
# ops: ('S'|'P'|'T'|'Sp', x[, splash]) ; ('shield',x) ('heal',x) ('drain',x,frac) ('st',who,name,r)
# ('buff',stat,x) ('tmp',who,stat,x,r) ('protect',) ('carry',key,x) ('foecharge',x) ('execute',frac)
# ('kocharge',x) ('koheal',frac) ('delay',r,x) ('atk',n) ('reflect',r,pct) ('spiky',r,x) ('cure',) ('ap_foe',x) ('nextatk',x)
def _tri(me):
    """Tri Attack: status chosen by the user's highest of FIRE / ELECTRIC / ICE synergy (ties: Fire > Electric > Ice; none -> burn)."""
    cn = me.side.cnt if hasattr(me.side, 'cnt') else {}
    f, e, i = cn.get('FIRE', 0), cn.get('ELECTRIC', 0), cn.get('ICE', 0)
    if i > f and i > e: return ('st', 'foe', 'freeze', 1)
    if e > f and e >= i: return ('st', 'foe', 'para', 1)
    return ('st', 'foe', 'burn', 2)

def POWERS():
    s = lambda x, sp=False: ('S', x, sp)
    return {
'ACCELEROCK': lambda v,c,me,foe: [s(PA(v[0],c.atk)), ('buff','spd',1), ('buff','def',-1)],
'ACID_ARMOR': lambda v,c,me,foe: [('buff','def',AT(v[0])), ('thorns',2)],
'AGILITY': lambda v,c,me,foe: [('buff','spd',SP(v[0]))],
'AIR_SLASH': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','flinch',1)],
'AQUA_STEP': lambda v,c,me,foe: [('buff','spd',SP(v[1])), s(D(v[0]))],
'AQUA_TAIL': lambda v,c,me,foe: [s(D(v[0])), ('shield',D(v[1]))],
'BITE': lambda v,c,me,foe: [('drain',PA(v[0],c.atk),.5), ('st','foe','flinch',1)],
'BLAST_BURN': lambda v,c,me,foe: [s(D(v[0]),True)],
'BLAZE_KICK': lambda v,c,me,foe: [s(ceil(D(v[0])*1.5) if foe.st['burn'] else D(v[0])), ('st','foe','burn',3)],
'BLOOD_MOON': lambda v,c,me,foe: [s(PA(v[0],c.atk)), ('st','foe','wound',2)],
'BUG_BUZZ': lambda v,c,me,foe: [s(D(v[0])*(2 if foe.st['para'] else 1))],
'BULLDOZE': lambda v,c,me,foe: [s(D(v[0]*1.4),True), ('tmp','foe','spd',-1,2)],
'COLUMN_CRUSH': lambda v,c,me,foe: [('shield',D(v[0])), s(me.shield + D(v[0]))],
'CRABHAMMER': lambda v,c,me,foe: [s(D(v[0])), ('execute',4)],
'CRUNCH': lambda v,c,me,foe: [s(D(v[0])), ('koheal',.5)],
'DARKEST_LARIAT': lambda v,c,me,foe: [s(PA(v[0],c.atk)) for _ in range(max(2, round(c.spd/25)))] + [('st','foe','flinch',1)],
'DARK_HARVEST': lambda v,c,me,foe: [('drain',D(v[0]*3),.3), ('st','me','flinch',1)],
'DOUBLE_SHOCK': lambda v,c,me,foe: [s(D(v[0])), ('st','me','para',1)],
'DRAGON_BREATH': lambda v,c,me,foe: [s(D(v[0]),True)],
'DRAGON_TAIL': lambda v,c,me,foe: [s(D(v[0])), ('buff','def',AT(v[1])), ('buff','sdef',AT(v[1]))],
'DRUM_BEATING': lambda v,c,me,foe: [[('shield',D(v[0]*.8))], [s(D(v[1]*.8))], [('carry','spd',SP(v[2]))]][me.cycle % 3],
'ENTANGLING_THREAD': lambda v,c,me,foe: [s(D(v[0]),True), ('st','foe','para',2)],
'FAIRY_WIND': lambda v,c,me,foe: [('carry','charge',1 + (1 if v[0] >= 10 else 0))],
'FIRESTARTER': lambda v,c,me,foe: [('buff','spd',SP(v[0])), s(D(v[1]*.8))],
'FLAMETHROWER': lambda v,c,me,foe: [s(D(v[0]),True), ('st','foe','burn',3)],
'FLOWER_TRICK': lambda v,c,me,foe: [('delay',1,D(v[0]))],
'FURY_SWIPES': lambda v,c,me,foe: [('atk', 5 if getattr(me,'stars',1) >= 4 else 3)],
'FUTURE_SIGHT': lambda v,c,me,foe: [('delay',2,D(v[1]*3))],
'GEAR_GRIND': lambda v,c,me,foe: [s(PA(v[0],me.eff('spd')*SCALE['spd'])), s(PA(v[0],me.eff('spd')*SCALE['spd']))],
'GIGATON_HAMMER': lambda v,c,me,foe: [s(D(v[0])), ('st','me','fatigue',2)],
'GLAIVE_RUSH': lambda v,c,me,foe: [('st','foe','armor',2), ('st','me','armor',2), s(D(v[0]))],
'GROWL': lambda v,c,me,foe: [('st','foe','flinch',1), ('tmp','foe','atk',-AT(v[0]),2)],
'GUILLOTINE': lambda v,c,me,foe: [s(PA(v[0],c.atk)), ('kocharge',1)],
'HEADBUTT': lambda v,c,me,foe: [s(D(v[0])*(2 if foe.shield>0 else 1)), ('st','foe','flinch',1)],
'HEAVY_SLAM': lambda v,c,me,foe: [s(D(v[0]) + max(0,(me.maxhp-foe.maxhp)//3), True)],
'HEX': lambda v,c,me,foe: [s(D(v[0])*(2 if foe.neg() else 1))],
'HORN_ATTACK': lambda v,c,me,foe: [s(PA(v[0],c.atk)), ('st','foe','armor',1)],
'HORN_DRILL': lambda v,c,me,foe: [s(ceil(PA(v[0],c.atk)*1.5) if me.eff('atk') > foe.eff('atk') else PA(v[0],c.atk))],
'HYDRO_PUMP': lambda v,c,me,foe: [s(D(v[0]),True)],
'ICE_BALL': lambda v,c,me,foe: [('buff','sdef',2), s(D(v[0]) + PA(v[1],c.sdef))],
'ICICLE_CRASH': lambda v,c,me,foe: [s(D(v[0]),True)],
'ICICLE_MISSILE': lambda v,c,me,foe: [s(D(v[1]*1.5)) for _ in range(int(v[0]))] + [('st','foe','freeze',1)],
'ICY_WIND': lambda v,c,me,foe: [s(D(v[0]),True), ('tmp','foe','spd',-SP(v[1]),2)],
'KING_SHIELD': lambda v,c,me,foe: [('protect',), ('shield',D(v[0]*2))],
'KOWTOW_CLEAVE': lambda v,c,me,foe: [s(ceil(PA(150,c.atk)*2)), ('T', me.side.fallen*max(1, round(PA(150,c.atk)*v[0]/100)))],
'LEAF_BLADE': lambda v,c,me,foe: [('T', ceil(PA(v[0],c.atk)*2))],
'LEECH_LIFE': lambda v,c,me,foe: [('drain',D(v[0]),1.0)],
'LICK': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','para',1), ('st','foe','confuse',1)],
'MAGICAL_LEAF': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','armor',1)],
'MAGIC_POWDER': lambda v,c,me,foe: [('shield',D(v[0])), ('st','foe','flinch',S(v[1]))],
'MAGNET_BOMB': lambda v,c,me,foe: [s(D(v[0]*1.5),True), ('st','foe','locked',1)],
'MANTIS_BLADES': lambda v,c,me,foe: [('P',D(v[0])), s(D(v[0])), ('T',D(v[0]))],
'METEOR_MASH': lambda v,c,me,foe: [s(PA(v[0],c.atk)) for _ in range(4 if me.lv('PSYCHIC') else 3)] + [('buff','atk',1)],
'MYSTICAL_FIRE': lambda v,c,me,foe: [s(D(v[0])), ('ap_foe',-1)],
'NIGHTMARE': lambda v,c,me,foe: [('st','foe','fatigue',S(v[0]))] + ([s(D(v[1]))] if foe.neg() else []),
'NUZZLE': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','para',S(v[1]))],
'PECK': lambda v,c,me,foe: [s(D(v[0]))],
'PETAL_DANCE': lambda v,c,me,foe: [s(D(v[1])) for _ in range(max(2, round(v[0]/2)))],
'PLAY_ROUGH': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','charm',2)],
'PSYCHIC': lambda v,c,me,foe: [s(D(v[0]*1.5),True), ('foecharge',-1)],
'PSYCHO_CUT': lambda v,c,me,foe: [s(ceil(D(v[0])*1.5)) for _ in range(3)],
'RAPID_SPIN': lambda v,c,me,foe: [s(D(v[0])), ('buff','def',max(1, round(PA(v[1],c.atk)))), ('buff','sdef',max(1, round(PA(v[1],c.atk))))],
'REFLECT': lambda v,c,me,foe: [('reflect',S(v[0]),50)],
'RETALIATE': lambda v,c,me,foe: [s(PA(v[0],c.atk)) for _ in range(1 + me.side.fallen)],
'ROCK_ARTILLERY': lambda v,c,me,foe: [s(D(v[1]*1.5)) for _ in range(max(2, round(v[0]/5)))],
'ROCK_SLIDE': lambda v,c,me,foe: [s(D(v[0])*(2 if foe.lv('FLYING') or 'FLYING' in foe.types else 1))],
'SALT_CURE': lambda v,c,me,foe: [('shield',D(v[0])), ('cure',)] + ([('st','foe','burn',3)] if foe.types & {'WATER','STEEL','GHOST'} else []),
'SHADOW_BALL': lambda v,c,me,foe: [s(D(v[0])), ('tmp','foe','sdef',-1,99)],
'SHOCKWAVE': lambda v,c,me,foe: [s(D(v[0]),True)],
'SILVER_WIND': lambda v,c,me,foe: [s(D(v[0])), ('buff','atk',1), ('buff','spd',1), ('buff','def',1), ('buff','sdef',1)],
'SING': lambda v,c,me,foe: [('st','foe','sleep',S(v[1]))],
'SLASH': lambda v,c,me,foe: [s(ceil(D(v[0])*2))],
'SNIPE_SHOT': lambda v,c,me,foe: [s(D(v[0]),True)],
'SOAK': lambda v,c,me,foe: [s(D(v[0])), ('carry','charge',1)],
'SOFT_BOILED': lambda v,c,me,foe: [('cure',), ('shield',D(v[0])), ('carry','shield',ceil(D(v[0])/2))],
'SPIKY_SHIELD': lambda v,c,me,foe: [('spiky',S(v[0]),PA(v[1],c.defn))],
'STEAMROLLER': lambda v,c,me,foe: [s(PA(v[0]*.75,c.spd))] + ([('st','foe','flinch',1)] if me.eff('spd') > foe.eff('spd') else []),
'STORED_POWER': lambda v,c,me,foe: [s(D(v[0]) + me.boosts)],
'STRING_SHOT': lambda v,c,me,foe: [s(D(v[0])), ('st','foe','para',2)],
'TELEPORT': lambda v,c,me,foe: [('nextatk',D(v[0]))],
'TERRAIN_PULSE': lambda v,c,me,foe: [('heal',max(1, round(v[0]/100*c.hpc)))] + ([('buff','def',1)] if me.lv('GRASS') else []) + ([('buff','spd',2)] if me.lv('ELECTRIC') else []) + ([('buff','ap',1)] if me.lv('PSYCHIC') else []),
'THRASH': lambda v,c,me,foe: [('buff','atk',max(1, round(v[0]/100*c.atkc))), ('st','me','confuse',1)],
'THUNDER_SHOCK': lambda v,c,me,foe: [s(D(v[0]))],
'TICKLE': lambda v,c,me,foe: [('tmp','foe','atk',-1,2), ('tmp','foe','def',-1,2)],
'TORCH_SONG': lambda v,c,me,foe: [s(PA(50,c.atk)) for _ in range(4)] + [('st','foe','burn',3), ('buff','ap',int(v[2]))],
'TRANSE': lambda v,c,me,foe: [('heal',max(1, round(.5*me.maxhp)))],
'TRI_ATTACK': lambda v,c,me,foe: [s(D(v[0]*.8)), _tri(me)],
'TROP_KICK': lambda v,c,me,foe: [s(D(v[0])), ('tmp','foe','atk',-AT(v[1]),2)],
'TWISTER': lambda v,c,me,foe: [s(D(v[0]),True)],
'UPROAR': lambda v,c,me,foe: [s(D(v[0])), ('delay',2,D(v[0]),1), ('delay',3,D(v[0]),1)],
'VOLT_SWITCH': lambda v,c,me,foe: [s(D(v[0]),True)],
'WAVE_SPLASH': lambda v,c,me,foe: [('shield',max(1, round(v[0]/100*c.hpc))), s(max(1, round(v[0]/100*c.hpc)))],
'WHEEL_OF_FIRE': lambda v,c,me,foe: [s(D(v[0])), s(D(v[0]))],
'WHIRLPOOL': lambda v,c,me,foe: [s(PA(v[0],c.atk)) for _ in range(4)],
'WISH': lambda v,c,me,foe: [('shield',D(v[0])), ('protect',)],
}
PW = POWERS()

# ---------------- cards ----------------
class Raw: pass

PAS = {'Heracross': 'guts', 'Zangoose': 'toxic', 'Durant': 'durant', 'Komala': 'komala', 'Spinda': 'spinda', 'Pincurchin': 'pincurchin', 'Scraggy': 'moxie', 'Scrafty': 'moxie',
       'Gligar': 'gligar', 'Gliscor': 'gligar', 'Regigigas': 'slow', 'Kartana': 'beastatk', 'Nihilego': 'beastap', 'Magearna': 'soul'}
class Card:
    def __init__(s, spec):
        s.__dict__.update(spec)
    def reset(s):
        s.hp = s.maxhp = s.hp0; s.charge = 0; s.shield = 0; s.ap = 0
        s.st = collections.defaultdict(int); s.tmp = []; s.perm = collections.defaultdict(int)
        s.syn = {}; s.boosts = 0; s.cycle = 0; s.atk_n = 0; s.hits_in = 0; s.rounds_on = 0
        s.protect = False; s.thorns = 0; s.reflect = (0, 0); s.spiky = (0, 0)
        s.aqua_used = False; s.fossil_used = False; s.fly_used = 0; s.swarm = 0; s.disguise = 0
        s.pas = PAS.get(s.name, ''); s.gl_used = False; s.first_attack = True; s.nextatk = 0; s.ground_n = 0; s.fire_n = 0; s.ghost_flinched = False
        s.base = dict(atk=s.atk0, defn=s.def0, sdef=s.sdef0, spd=s.spd0, ap=0)
        s.casts = 0; s.dealt = 0; s.kos = 0; s.accel = 0; s.sf = 0
        s.fl = collections.Counter(); s.itst = collections.Counter(); s.itn = collections.Counter(); s.critacc = 0; s.critpct = 0
        s.imm = set(); s.immturn = 0; s.berry_used = False; s.revived = False; s.dodge_n = 0; s.absorbed = 0; s.owed = 0
        s.rhalf = False; s.cover_used = False; s.bulb_used = False; s.charm_used = False; s.smoke_used = False; s.shtot = 0; s.expl_used = False
        s.cursed = set(); s.dish = {}; s.dodge_n2 = 0; s.items_eff = []; s.cheap0 = 0; s.elixir_used = False; s.surf_used = False; s.healboost = 0
    def orb_burn(s): return bool(s.fl['flameorb']) and not (s.fl['immune_neg'] or s.pas == 'komala')   # Flame Orb: the holder is permanently BURNED
    def neg(s): return any(s.st[k] > 0 for k in NEG) or s.orb_burn()
    def lv(s, t): return s.syn.get(t, 0)
    def eff(s, stat):
        key = {'def': 'defn'}.get(stat, stat)
        v = s.base[key] + s.perm[key] + sum(x for st_, x, r in s.tmp if st_ == stat)
        if stat in ('def', 'sdef') and (s.st['armor'] > 0 or s.st['freeze'] > 0): return 0
        if stat == 'atk' and s.st['charm'] > 0: v -= 2
        p = s.pas
        if p:
            if stat == 'atk':
                if p == 'guts' and (s.neg() or s.st.get('poison_n', 0) > 0): v += 2
                if p == 'toxic' and (s.st['poison'] > 0 or s.st.get('poison_n', 0) > 0): v += 2
                if p == 'slow' and s.casts > 0: v += 2
            if stat == 'spd' and p == 'slow': v += 2 if s.casts > 0 else -2
        if stat == 'spd':
            if s.st['para'] > 0: v -= 1
            return max(1, v)
        return max(0, v)

import os
TWEAK_PATH = f'{ROOT}/pac-data/tweaks.json'
def load_tweaks():
    return json.load(open(TWEAK_PATH)) if os.path.exists(TWEAK_PATH) else {}

def load_cards():
    allp = list(csv.DictReader(open(DATA + 'pokemons-data.csv')))
    _rm = set(json.load(open(DATA + 'removed.json')))
    core = [x for x in csv.DictReader(open(DATA + 'core-value-tiers.csv')) if x['Name'] not in _rm]
    cards = []
    for c0 in core:
        p = [x for x in allp if x['Index'] == c0['Index'] and x['Name'] == c0['Name']][0]
        c = Raw()
        c.hp, c.atk, c.defn, c.sdef, c.spd, c.pp = [int(p[k]) for k in ('HP','Attack','Defense','Special Defense','Speed','Max PP')]
        c.hpc = max(3, round(c.hp / SCALE['hp'])); c.atkc = max(1, round(c.atk / SCALE['atk']))
        ab = p['Ability']; stars = int(c0['Stars'])
        torder = [p[f'Type {i}'] for i in range(1, 5) if p[f'Type {i}']]; types = set(torder)
        cards.append(Card(dict(name=c0['Name'].title(), tier=c0['TierGroup'], stars=stars, value=float(c0['Value']), price=math.ceil(float(c0['Value'])),
            types=types, torder=torder, family=p['Family'], raw=c, ability=ab, v=resolve(ab, stars), role=None,
            hp0=c.hpc, atk0=c.atkc, def0=max(0, round(c.defn / SCALE['df'])), sdef0=max(0, round(c.sdef / SCALE['df'])),
            spd0=(max(1, round(c.spd / SCALE['spd'])) if SCALE.get('spd_mode') == 'div' else min(5, max(1, 3 + round((c.spd - 50) / 10)))), ppmax=max(2, round(c.pp / SCALE['pp'])))))
    tw = load_tweaks()
    for c in cards:
        t = tw.get(c.name, {})
        c.hp0 = max(3, c.hp0 + t.get('hp', 0)); c.atk0 = max(1, c.atk0 + t.get('atk', 0))
        c.def0 = max(0, c.def0 + t.get('df', 0)); c.sdef0 = max(0, c.sdef0 + t.get('sdf', 0))
        c.spd0 = max(1, c.spd0 + t.get('spd', 0)); c.ppmax = max(1, c.ppmax + t.get('pp', 0))
    return cards
