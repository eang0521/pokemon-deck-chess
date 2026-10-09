import random, math, collections, copy
from engine import *
from itemfx import ItemFX
from items import ITEMS

STN = dict(para='PARALYZED', armor='ARMOR BROKEN', fatigue='FATIGUED', flinch='FLINCHED', confuse='CONFUSED', charm='CHARMED', wound='WOUNDED', burn='BURNED', sleep='ASLEEP', freeze='FROZEN', locked='LOCKED')
SYN_LEVELS = (0, 0, 1, 2, 3)  # count -> level (count>=4 => 3)
# PAC thresholds x0.75 (round half up); every PAC threshold is a level (up to four)
PAC_TH = dict(NORMAL=[3,5,7,9], GRASS=[3,5,7,9], FIRE=[2,4,6,8], WATER=[3,6,9], ELECTRIC=[3,5,7], FIGHTING=[2,4,6,8], PSYCHIC=[3,5,7], DARK=[3,5,7],
    STEEL=[2,4,6,8], GROUND=[2,4,6,8], POISON=[3,5,7], DRAGON=[3,5,7], FIELD=[3,6,9], MONSTER=[2,4,6,8], HUMAN=[2,4,6], AQUATIC=[2,4,6,8], BUG=[2,4,6,8],
    FLYING=[2,4,6,8], FLORA=[3,4,5,6], ROCK=[2,4,6], GHOST=[2,4,6,8], FAIRY=[2,4,6,8], ICE=[2,4,6,8], FOSSIL=[2,4,6], SOUND=[2,4,6], ARTIFICIAL=[2,4,6],
    BABY=[3,5,7], LIGHT=[2,3,4,5], WILD=[2,4,6,9], AMORPHOUS=[3,5,7], GOURMET=[3,4,5])
import os
EXH = int(os.environ.get('EXH', '0')); EXS = int(os.environ.get('EXS', '8'))
def scaled(x): return int(0.75 * x + 0.5)
SYN_TH = {t: [scaled(x) for x in v[:4]] for t, v in PAC_TH.items()}
SYN_TH['LIGHT'] = [2, 3, 4]   # user override: Light keeps three levels at 2 / 3 / 4
SYN_TH['BABY'] = [2, 3, 4]   # fewer Baby cards exist: 2 / 3 / 4
if os.environ.get('BABYTH'): SYN_TH['BABY'] = [int(x) for x in os.environ['BABYTH'].split(',')]
def level_of(t, n): return sum(1 for x in SYN_TH.get(t, [2, 3, 4]) if n >= x)

# AP scaling per power: default 'first' = +1 per AP to the first damage number (or, with no damage, the first shield/heal number)
# 'half' = +1 per 2 AP (rounded down); 'each_half' = +1 per 2 AP on every damage number; 'none' = AP does nothing
import os
CHIP = int(os.environ.get('CHIP','1')); CAP = float(os.environ.get('CAP','0'))
STAR_MODE = os.environ.get('STAR_MODE', 'double')
OT_START = float(os.environ.get('OT_START','25')); OT_STEP = float(os.environ.get('OT_STEP','5'))
HALF = ['CRABHAMMER', 'SILVER_WIND', 'LEAF_BLADE', 'HORN_DRILL', 'FLAMETHROWER', 'SHOCKWAVE', 'GUILLOTINE', 'KOWTOW_CLEAVE', 'SLASH', 'BLAST_BURN', 'HYDRO_PUMP', 'DRAGON_BREATH', 'TWISTER', 'ICICLE_CRASH']
EACH_HALF = ['DARKEST_LARIAT', 'GEAR_GRIND', 'MANTIS_BLADES', 'METEOR_MASH', 'PETAL_DANCE', 'PSYCHO_CUT', 'ROCK_ARTILLERY', 'TORCH_SONG', 'WHEEL_OF_FIRE', 'WHIRLPOOL', 'ICICLE_MISSILE']
NOAP = ['ACID_ARMOR', 'AGILITY', 'FAIRY_WIND', 'GROWL', 'SING', 'TICKLE', 'TELEPORT', 'THRASH', 'FURY_SWIPES', 'NIGHTMARE', 'TRANSE', 'REFLECT', 'SPIKY_SHIELD', 'COLUMN_CRUSH', 'WAVE_SPLASH', 'TERRAIN_PULSE', 'STORED_POWER', 'HEAVY_SLAM']
APM = {**{a: 'half' for a in HALF}, **{a: 'each_half' for a in EACH_HALF}, **{a: 'none' for a in NOAP}}

# GOURMET signature dishes (one per evolution family, as in PAC). Each entry: (level I, level II, level III) effect lists.
A_ = lambda *x: list(x)
from items import qh as _qh
DISH = {
 'FARFETCH_D': ([('crit', 20)], [('crit', 30)], [('crit', 40)]),
 'GALARIAN_FARFETCH_D': ([('crit', 30)], [('crit', 45)], [('crit', 60)]),
 'LICKITUNG': ([('atk', 1)], [('atk', 2)], [('atk', 2)]),
 'HAPPINY': ([('atk', 1), ('def', 1)], [('atk', 1), ('def', 1), ('sdef', 1)], [('atk', 2), ('def', 1), ('sdef', 1)]),
 'MUNCHLAX': ([('hp', 1)], [('hp', 2)], [('hp', 3)]),
 'SHUCKLE': ([('shield', 3)], [('shield', 4)], [('shield', 5)]),
 'MILTANK': ([('hp', 3)], [('hp', 4)], [('hp', 5)]),
 'GULPIN': ([('sludge', 1)], [('sludge', 2)], [('sludge', 3)]),
 'SPINDA': ([('rand', 1)], [('rand', 2)], [('rand', 3)]),
 'TROPIUS': ([('nanab', 2)], [('nanab', 3)], [('nanab', 4)]),
 'COMBEE': ([('regen', 1)], [('regen', 1), ('hp', 1)], [('regen', 2)]),
 'CHERUBI': ([('def', 1), ('sdef', 1)], [('def', 2), ('sdef', 1)], [('def', 2), ('sdef', 2)]),
 'VANILLITE': ([('first', 'freeze', 1)], [('first', 'freeze', 1), ('sdef', 1)], [('first', 'freeze', 1), ('freezen', 5)]),
 'DEERLING_SUMMER': ([('charge', 2)], [('charge', 2)], [('charge', 3)]),
 'SINISTEA': ([('charge', 2)], [('charge', 2)], [('charge', 3)]),
 'SWIRLIX': ([('first', 'charm', 2)], [('first', 'charm', 2), ('atk', 1)], [('first', 'charm', 2), ('charmn', 3)]),
 'BOUNSWEET': ([('spd', 1)], [('spd', 2)], [('spd', 2)]),
 'GUZZLORD': ([('atk', 2), ('hp', -2)], [('atk', 3), ('hp', -2)], [('atk', 3), ('hp', -2)]),
 'SKWOVET': ([('shield', 2)], [('shield', 3)], [('shield', 4)]),
 'APPLIN': ([('tart', 2)], [('tart', 3)], [('tart', 4)]),
 'MILCERY': ([('rand', 1)], [('rand', 2)], [('rand', 3)]),
 'LECHONK': ([('hp', 1)], [('hp', 2)], [('hp', 2)]),
 'FIDOUGH': ([('shield', 4)], [('shield', 5)], [('shield', 6)]),
 'SMOLIV': ([('dodge', 5)], [('dodge', 4)], [('dodge', 3)]),
 'NACLI': ([('shield', 3)], [('shield', 3), ('protect', 1)], [('shield', 4), ('protect', 1)]),
 'CAPSAKID': ([('rage', 2)], [('rage', 3)], [('rage', 4)]),
 'VELUZA': ([('atk', 2), ('ap', 1), ('hp', -2)], [('atk', 3), ('ap', 2), ('hp', -2)], [('atk', 3), ('ap', 3), ('hp', -2)]),
 'DONDOZO': ([('hp', 4)], [('hp', 5)], [('hp', 6)]),
 'TATSUGIRI_CURLY': ([('atk', 1)], [('atk', 2)], [('atk', 2)]),
 'TATSUGIRI_DROOPY': ([('def', 1)], [('def', 2)], [('def', 2)]),
 'TATSUGIRI_STRETCHY': ([('spd', 1)], [('spd', 2)], [('spd', 2)]),
 'PECHARUNT': ([('first', 'confuse', 1)], [('first', 'confuse', 1), ('atk', 1)], [('first', 'confuse', 1), ('atk', 1), ('first', 'fatigue', 2)]),
}
for _k, _lv in DISH.items():
    for _eff in _lv:
        for _n, _e in enumerate(_eff):
            if _e[0] == 'crit': _eff[_n] = ('crit', _qh(_e[1]))
DEFAULT_DISH = ([('atk', 1)], [('atk', 1), ('hp', 1)], [('atk', 2), ('hp', 1)])

class Side:
    def __init__(s, lineup, idx):
        s.idx = idx; s.lineup = list(lineup); s.fielded = []; s.active = None
        s.fallen = 0; s.field_ko = 0; s.light = 0; s.amorph = 0; s.nsyn = 0; s.carry = collections.defaultdict(int); s.pending = 0; s.delays = []

BABY_HP = False
STREAKS = [0, 0]
GH3 = os.environ.get('GH3','0') == '1'
GHFAT = os.environ.get('GHFAT','0') == '1'; GHBACK = os.environ.get('GHBACK','1') == '1'
BABYBOOST = os.environ.get('BABYBOOST', '')
class Duel(ItemFX):
    def __init__(s, la, lb, rng=None, strat=('order', 'order'), max_rounds=60, log=False):
        s.rng = rng or random.Random()
        la = [copy.copy(c) for c in la]; lb = [copy.copy(c) for c in lb]
        for c in la + lb: c.reset()
        s.sides = [Side(la, 0), Side(lb, 1)]
        for sd in s.sides:
            for c in sd.lineup: c.side = sd
            s.setup_items(sd)
            s.assign_syn(sd)
            s.cook(sd)
        s.strat = strat; s.round = 0; s.max_rounds = max_rounds; s.log = [] if log else None
        s.nrounds = 0; s.acting = None
        s.rec = False; s.buf = []; s.snaps = []
        s.orig = [list(sd.lineup) for sd in s.sides]

    def assign_syn(s, side):
        # all Pokemon are revealed; synergy levels come from the whole lineup and are fixed for the battle
        cnt = collections.Counter(); seen = set()
        for c in side.lineup:
            for t in c.types:
                if (t, c.family) not in seen: seen.add((t, c.family)); cnt[t] += 1
        cnt.update(side.gems)
        # Dragon level I: each Dragon's second synergy counts twice (not the third)
        if level_of('DRAGON', cnt['DRAGON']) >= 1:
            for c in side.lineup:
                if 'DRAGON' in c.types:
                    sec = [t for t in c.torder[:2] if t != 'DRAGON']
                    if sec: cnt[sec[0]] += 1
        for c in side.lineup:
            c.syn = {t: level_of(t, cnt[t]) for t in c.types if level_of(t, cnt[t]) > 0}
        side.light = level_of('LIGHT', cnt['LIGHT']); side.amorph = level_of('AMORPHOUS', cnt['AMORPHOUS'])
        side.ndrag = sum(1 for c in side.lineup if 'DRAGON' in c.types)
        side.nsyn = len({t for c in side.lineup for t in c.syn})
        side.cnt = cnt

    def cook(s, sd):
        # GOURMET: each chef serves its signature dish to the next card in lineup order (the previous one if last)
        lin = sd.lineup
        for i, c in enumerate(lin):
            l = c.lv('GOURMET')
            if not l: continue
            j = i + 1 if i + 1 < len(lin) else i - 1
            if j < 0: continue
            t = lin[j]; d = t.dish
            for e in DISH.get(c.family, DEFAULT_DISH)[l - 1]:
                k = e[0]
                if k == 'atk': t.perm['atk'] += e[1]
                elif k == 'def': t.perm['defn'] += e[1]
                elif k == 'sdef': t.perm['sdef'] += e[1]
                elif k == 'spd': t.perm['spd'] += e[1]
                elif k == 'ap': t.ap += e[1]
                elif k == 'hp': t.maxhp = max(1, t.maxhp + e[1]); t.hp = max(1, t.hp + e[1])
                elif k == 'shield': t.perm['dshield'] += e[1]
                elif k == 'shieldpct': t.perm['dshield'] += max(2, int(t.maxhp * e[1] / 100 + .5))
                elif k == 'charge': t.perm['dcharge'] += e[1]
                elif k == 'protect': t.perm['dprotect'] = 1
                elif k == 'rage': t.tmp.append(('atk', e[1], 3))
                elif k == 'rand':
                    for _ in range(e[1]):
                        r = s.rng.choice(['atk', 'def', 'sdef', 'spd', 'hp'])
                        if r == 'hp': t.maxhp += 2; t.hp += 2
                        else: t.perm[{'def': 'defn'}.get(r, r)] += 1
                elif k == 'first': d.setdefault('first', []).append((e[1], e[2]))
                else: d[k] = d.get(k, 0) + e[1] if k in ('crit', 'regen') else max(d.get(k, 0), e[1]) if k not in ('dodge',) else (min(d[k], e[1]) if k in d else e[1])

    def spotlight(s, sd):
        # LIGHT: the opening Pokemon stands in the spotlight (any type)
        lg = sd.light
        if not lg: return
        c = sd.active; c.ap += 1; c.perm['atk'] += 1
        if lg >= 2: c.charge = min(c.ppmax, c.charge + 2)
        if lg >= 3: c.perm['defn'] += 1; c.perm['sdef'] += 1; c.protect = True
        s.say(f'{c.name} stands in the spotlight')

    def say(s, *a):
        if s.log is not None: s.log.append(' '.join(str(x) for x in a))
        if s.rec: s.buf.append(' '.join(str(x) for x in a))
    def _say_old(s, *a):
        if s.log is not None: s.log.append(' '.join(str(x) for x in a))

    # ---------- choosing ----------
    def pick(s, side, foe_card, opener=False):
        pool = side.lineup
        if not pool: return None
        if s.strat[side.idx] == 'order':
            return pool[0]   # set order: lineup is arranged before the battle
        if s.strat[side.idx] == 'random':
            return s.rng.choice(pool)
        if foe_card is None or opener:
            # secret starter: best average matchup against the opponent's revealed roster
            osd = s.sides[1 - side.idx]
            foes = osd.lineup + ([osd.active] if osd.active is not None and osd.active.hp > 0 else [])
            if not foes: return s.rng.choice(pool)
            def avg(c):
                t = 0
                for f in foes:
                    fd = max(1, f.eff('atk') - c.eff('def')); md = max(1, c.eff('atk') - f.eff('def'))
                    t += (c.hp0 / fd) / (f.hp0 / md)
                return t / len(foes)
            return max(pool, key=avg)
        def score(c):
            foe_dmg = max(1, foe_card.eff('atk') - c.eff('def'))
            my_dmg = max(1, c.eff('atk') - foe_card.eff('def'))
            surv = (c.hp0) / foe_dmg; kill = foe_card.hp / my_dmg
            sc = surv / kill
            if c.eff('spd') > foe_card.eff('spd'): sc *= 1.1
            return sc
        return max(pool, key=score)

    # ---------- entering ----------
    def enter(s, side, card):
        side.lineup.remove(card); side.fielded.append(card); side.active = card
        L = card.lv
        pick = lambda t, arr: arr[L(t) - 1] if L(t) else 0
        card.shield += pick('NORMAL', [5, 7, 10, 12])
        if L('NORMAL') == 4: card.perm['atk'] += 1; card.ap += 1
        card.perm['defn'] += pick('FIGHTING', [1, 1, 2, 2]) + pick('ROCK', [2, 3, 5])
        card.perm['sdef'] += pick('ICE', [1, 2, 2, 3])
        card.ap += pick('PSYCHIC', [2, 3, 5])
        if L('WILD'):
            w = L('WILD'); card.perm['spd'] += [1, 1, 2, 2][w - 1]; card.perm['atk'] += [0, 1, 2, 2][w - 1]
        if L('WATER'): card.charge += 2
        sd_ = side
        if L('DRAGON') >= 2: card.shield += sd_.ndrag
        if L('DRAGON') >= 3: k = max(1, sd_.ndrag // 2); card.perm['spd'] += 1; card.ap += k
        if L('FIELD') and sd_.field_ko:
            k = sd_.field_ko; card.maxhp += [2, 3, 4][L('FIELD') - 1] * k; card.hp = card.maxhp
            if L('FIELD') >= 2: card.perm['spd'] += min(3, k)
        if sd_.amorph:
            am = sd_.amorph; n = sd_.nsyn
            hpb = n * [1, 1, 2][am - 1]; card.maxhp += hpb; card.hp += hpb
            if am >= 2: card.perm['spd'] += n // [9, 3, 2][am - 1]
        card.swarm = pick('BUG', [1, 2, 2, 3])
        card.disguise = 1 if card.name == 'Mimikyu' else 0
        if L('BUG') == 3: card.perm['sdef'] += 1
        card.shield += card.perm['dshield']; card.charge += card.perm['dcharge']
        if card.perm['dprotect']: card.protect = True
        if L('BABY') and BABYBOOST:
            ls_ = STREAKS[side.idx]
            if BABYBOOST == 'atk': card.perm['atk'] += min([1, 2, 3][L('BABY') - 1], ls_)
            elif BABYBOOST == 'atkhp': card.perm['atk'] += min([1, 2, 3][L('BABY') - 1], ls_); card.maxhp += min(ls_, 3) * L('BABY'); card.hp += min(ls_, 3) * L('BABY')
        if L('BABY') and BABY_HP:
            b = pick('BABY', [3, 6, 9]) + min(3, getattr(side, 'streak', 0)); card.maxhp += b; card.hp += b
        # carry-overs from the previous Pokemon
        cr = side.carry
        card.charge += cr['charge']; card.shield += cr['shield']; card.perm['spd'] += cr['spd']
        card.perm['defn'] += cr['def']; card.perm['atk'] += cr['atk']
        card.rhalf = cr['revive'] > 0
        s.heal(card, cr['heal']); card.maxhp += cr['maxhp']; card.hp += cr['maxhp']
        side.carry = collections.defaultdict(int)
        s.item_enter(side, card)
        if side.pending:
            if not card.fl['boots']:
                s.say(f'  splash {side.pending} hits {card.name}')
                card.hp -= side.pending
            side.pending = 0
        card.charge = min(card.charge, card.ppmax)
        s.say(f'{card.name} enters the battle')

    def heal(s, card, x):
        if x <= 0 or card.st['wound'] > 0: return
        b = card.hp; card.hp = min(card.maxhp, card.hp + x)
        if card.hp > b: s.say(f"{card.name} heals {card.hp - b}")

    # ---------- damage ----------
    def apply_st(s, tgt, name, r, pw=None):
        blocked, r = s.blocks_status(tgt, name, r)
        if blocked: return
        if name == 'burn':
            tgt.st['burn_pow'] = max(pw or 1, tgt.st['burn_pow'] if tgt.st['burn'] > 0 else 0)
        if name in NEG and tgt.lv('AQUATIC') and not tgt.aqua_used:
            tgt.aqua_used = True; return
        tgt.st[name] = max(tgt.st[name], r)
        s.say(f"{tgt.name} is {STN.get(name, name.upper())} ({r} turn{'s' if r != 1 else ''})")

    def hit(s, src, dst, amount, kind, basic=False, ignore_def=False):
        if amount <= 0 or dst.hp <= 0: return 0
        if dst.fl['doll'] and kind in ('P', 'S'): amount = max(1, amount - 1)
        lk = dst.st['locked'] > 0      # LOCKED: this hit ignores Fly Away, dodge and evade; the lock is then used up
        if lk: dst.st['locked'] = 0
        if basic and dst.fl['dodge'] and not lk:
            dst.dodge_n += 1
            if dst.dodge_n % int(dst.fl['dodge']) == 0:
                s.say(f"{dst.name} dodges"); return 0
        if basic and dst.dish.get('dodge') and not lk:
            dst.dodge_n2 += 1
            if dst.dodge_n2 % dst.dish['dodge'] == 0: s.say(f"{dst.name} dodges"); return 0
        if dst.protect:
            s.say(f"{dst.name} is protected"); return 0
        if basic and dst.swarm > 0:
            s.say(f"{dst.name}'s swarm token blocks the attack")
            dst.swarm -= 1
            if dst.lv('BUG') >= 9: src.hp -= 1
            return 0
        if basic and dst.lv('GHOST'):
            dst.hits_in += 1
            if dst.hits_in % 4 == 0 and dst.lv('GHOST') >= 1 and not lk:
                s.say(f"{dst.name} evades")
                if dst.lv('GHOST') >= 4 and GHBACK: s.hit(dst, src, 1, 'T')
                return 0
        if kind == 'P': blk = dst.eff('def')
        elif kind == 'S': blk = 0 if ignore_def else dst.eff('sdef')
        else: blk = 0
        dmg = max(1, amount - blk)
        if blk > 0:
            dst.absorbed += min(amount, blk)
            if kind == 'S' and dst.fl['lens'] and src is not dst: s.hit(dst, src, min(blk, amount), 'T')
        if kind == 'S' and src.fl['nomicon'] and src is not dst:
            s.apply_st(dst, 'burn', 3); dst.perm['sdef'] = max(dst.perm['sdef'] - 1, -2)
        absorbed = min(dst.shield, dmg - CHIP); absorbed = max(0, absorbed); dst.shield -= absorbed; dmg_hp = dmg - absorbed
        dst.hp -= dmg_hp; src.dealt += dmg
        if src is s.acting and src is not dst and src.lv('HUMAN') and dst.hp > -999:
            if basic: s.heal(src, [1, 2, 3][src.lv('HUMAN') - 1])
        s.say(f"{src.name} hits {dst.name} for {dmg} {({'P':'physical','S':'special','T':'true'}[kind])}" + (f" ({absorbed} absorbed by shield)" if absorbed else ""))
        # reactions
        if basic and kind == 'P':
            if dst.thorns > 0: dst.thorns -= 1; src.perm['defn'] = max(-src.base['defn'], src.perm['defn'] - 1)
            if dst.reflect[0] > 0: s.hit(dst, src, int(amount * dst.reflect[1] / 100), 'S')
            if dst.spiky[0] > 0: src.st['wound'] = max(src.st['wound'], 2); s.hit(dst, src, dst.spiky[1], 'S')
            if dst.lv('FIGHTING') >= 2:
                dst.sf += 1
                if dst.sf % {2: 4, 3: 3, 4: 2}[dst.lv('FIGHTING')] == 0:
                    if dst.lv('FIGHTING') >= 3: src.shield = 0
                    src.hp -= 1
        if dst.hp <= 0 and not dst.revived:
            for ally in dst.side.lineup:
                if ally.fl['cover'] and not ally.cover_used:
                    ally.cover_used = True; ally.owed += (1 - dst.hp); dst.hp = 1; break
        s.item_on_hit(src, dst, amount, kind, basic, dmg_hp, absorbed)
        if dst.pas == 'pincurchin' and kind == 'S' and src is not dst and dst.hp > 0 and src.hp > 0: s.apply_st(src, 'para', 1)
        if dst.hp > 0 and dst.dish.get('nanab') and not dst.perm['nanabu'] and dst.hp * 2 <= dst.maxhp:
            dst.perm['nanabu'] = 1; s.heal(dst, dst.dish['nanab'])
        if dst.hp > 0 and dst.disguise and dst.hp * 2 <= dst.maxhp:
            dst.disguise = 0; dst.perm['atk'] += 2; dst.protect = True; s.say(f"{dst.name} is busted")
        if dst.hp > 0:
            if dst.lv('FOSSIL') and not dst.fossil_used and dst.hp * 2 <= dst.maxhp:
                dst.fossil_used = True; l = dst.lv('FOSSIL')
                dst.shield += [2, 4, 6][l - 1]; dst.perm['atk'] += (1 if l < 3 else 2)
            if dst.lv('WILD') == 4 and not dst.fl['berserk'] and dst.hp * 2 <= dst.maxhp:
                dst.fl['berserk'] = 1; dst.perm['atk'] += 2; dst.perm['spd'] += 2; dst.shield += 3
            if dst.lv('FLYING') >= 2 and False: pass
            if dst.lv('FLYING') and not lk and dst.fly_used < [1, 1, 2, 3][dst.lv('FLYING') - 1] and dst.hp * 2 <= dst.maxhp:
                dst.fly_used += 1; dst.protect = True
                if dst.fly_used == 1: dst.perm['spd'] += 1
                if dst.lv('FLYING') >= 2: dst.perm['sdef'] += 1
        return dmg

    # ---------- attacking ----------
    def attack(s, me, foe, free=False):
        L = me.lv
        base = me.eff('atk')
        if me.st['confuse'] > 0: base = base // 2; me.st['confuse'] = 0
        me.atk_n += 1
        crit = False
        want = False
        gen = me.critpct + me.dish.get('crit', 0) + ([1, 2, 3][L('DARK') - 1] if L('DARK') else 0)   # crit tokens gained per attack
        if gen:
            me.critacc += gen
            if me.critacc >= 5: me.critacc -= 5; want = True   # 5 crit tokens = one crit (x2 damage)
        if want and not (foe.lv('ROCK') >= 2 or foe.fl['helmet'] or foe.side.rk.get('r_crit')):
            crit = True
            base = base * 2
        if me.fl['pads'] and foe.shield > 0: base *= 2
        tp = min(base, [1, 2, 4, 5][L('STEEL') - 1]) if L('STEEL') else 0
        if me.fl['redorb']: tp = min(base, tp + 1)
        spec = 0
        if me.nextatk: spec += me.nextatk; me.nextatk = 0
        dealt = 0
        if foe.hp > 0:
            dealt += s.hit(me, foe, base - tp, 'P', basic=True)
            if tp: dealt += s.hit(me, foe, tp, 'T')
            if spec: dealt += s.hit(me, foe, spec, 'S')
        if L('ELECTRIC'):
            s.hit(me, foe, [1, 2, 3][L('ELECTRIC') - 1], 'S')   # Level III: one extra hit of 3; foes need +1 PP (foes need +1 PP while an Electric Level III Pokemon is in play: see act())
        if foe.hp > 0 and dealt > 0:
            if L('FIRE') and me.atk_n % [3, 2, 2, 1][L('FIRE') - 1] == 0: s.apply_st(foe, 'burn', 4 if L('FIRE') == 4 else 3, 2 if L('FIRE') >= 3 else 1)
            if L('POISON'):
                foe.st['poison_n'] = min([1, 2, 3][L('POISON') - 1], foe.st['poison_n'] + 1)
            if L('WILD'): s.apply_st(foe, 'wound', 2 if L('WILD') >= 3 else 1)
            if L('MONSTER') and me.first_attack: s.apply_st(foe, 'flinch', 1)
            if L('GHOST') >= 2 and id(foe) not in me.cursed:
                me.cursed.add(id(foe)); foe.perm['defn'] -= 1
                if L('GHOST') >= 3: foe.perm['atk'] -= 1
                if L('GHOST') >= 4: foe.perm['sdef'] -= 1
                if L('GHOST') >= 4 and GHFAT: s.apply_st(foe, 'fatigue', 1)
            dd = me.dish
            if dd:
                if me.first_attack:
                    for st_, r_ in dd.get('first', []): s.apply_st(foe, st_, r_)
                if dd.get('tart') and me.perm['tartn'] < dd['tart']: me.perm['tartn'] += 1; foe.perm['defn'] -= 1
                if dd.get('sludge'): foe.st['poison_n'] = min(dd['sludge'], foe.st['poison_n'] + 1)
                if dd.get('freezen') and me.atk_n % dd['freezen'] == 0: s.apply_st(foe, 'freeze', 1)
                if dd.get('charmn') and me.atk_n % dd['charmn'] == 0: s.apply_st(foe, 'charm', 2)
            if L('FAIRY') and me.atk_n % [2, 2, 2, 1][L('FAIRY') - 1] == 0:
                s.apply_st(foe, 'confuse', 1)
                if L('FAIRY') >= 2: s.apply_st(foe, 'charm', 2)
                if L('FAIRY') >= 3: foe.tmp.append(('spd', -1, 2))
            if L('ICE') >= 2 and me.atk_n % {2: 6, 3: 5, 4: 4}[L('ICE')] == 0: s.apply_st(foe, 'freeze', 1)
        if me.first_attack and me.fl: s.item_first_hit(me, foe)
        s.item_attack(me, foe, dealt, crit)
        me.first_attack = False
        if L('FIRE') == 2 and False: pass
        if not free and me.st['para'] <= 0 and me.st['fatigue'] <= 0:
            if me.fl['nullify']: me.perm['atk'] += 1
            else: me.charge += 2 if L('WATER') == 3 else 1
        return dealt

    # ---------- casting ----------
    def cast(s, me, foe):
        me.casts += 1; me.charge = 0
        ops = PW[me.ability](me.v, me.raw, me, foe)
        if me.fl['starpiece'] and STAR_MODE:
            _m = (lambda x: x + (x + 1) // 2) if STAR_MODE == 'half' else (lambda x: x * 2)
            ops = [((o[0], _m(o[1])) + tuple(o[2:])) if o[0] in ('S', 'P', 'T', 'Sp', 'drain', 'shield', 'heal') else o for o in ops]
        first = True; last = 0; ko_ops = []
        mode = APM.get(me.ability, 'first')
        hasdmg = any(o[0] in ('S', 'P', 'T', 'Sp', 'drain', 'delay') for o in ops)
        ap_ = me.ap if mode in ('first', 'all') else me.ap // 2 if mode in ('half', 'each_half') else 0
        shield_done = False
        for op in ops:
            k = op[0]
            if k in ('S', 'P', 'T', 'Sp'):
                x = op[1] + (ap_ if (first or mode == 'each_half') else 0)
                first = False
                if foe.hp <= 0: continue
                kind = 'S' if k in ('S', 'Sp') else k
                last = s.hit(me, foe, x, kind, ignore_def=(k == 'Sp' or me.lv('PSYCHIC') == 3))
                if len(op) > 2 and op[2]: s.sides[1 - me.side.idx].pending += x // 2
                if foe.hp <= 0: s.kill_hooks(me, foe)
            elif k == 'drain':
                x = op[1] + (ap_ if (first or mode == 'each_half') else 0); first = False
                d = s.hit(me, foe, x, 'S'); s.heal(me, int(d * op[2]))
                if foe.hp <= 0: s.kill_hooks(me, foe)
            elif k == 'shield':
                if me.st['wound'] <= 0: me.shield += op[1] + (ap_ if (not hasdmg and not shield_done) else 0)
                shield_done = True
            elif k == 'heal': s.heal(me, op[1] + (ap_ if (not hasdmg and not shield_done) else 0)); shield_done = True
            elif k == 'st': s.apply_st(foe if op[1] == 'foe' else me, op[2], op[3])
            elif k == 'buff':
                st_ = {'def': 'defn'}.get(op[1], op[1])
                if st_ == 'ap': me.ap += op[2]
                else: me.perm[st_] += op[2]
                if op[2] > 0: me.boosts += 1
            elif k == 'tmp':
                tgt = foe if op[1] == 'foe' else me; tgt.tmp.append((op[2], op[3], op[4]))
            elif k == 'protect': me.protect = True
            elif k == 'carry': me.side.carry[op[1]] += op[2]
            elif k == 'foecharge': foe.charge = max(0, foe.charge + op[1])
            elif k == 'execute':
                if foe.hp > 0 and foe.hp <= op[1]: foe.hp = 0; s.kill_hooks(me, foe)
            elif k == 'koif':      # KO the target if it has one of these statuses (unless it has the immune type)
                if foe.hp > 0 and any(foe.st[n] > 0 for n in op[1]) and not (op[2] and op[2] in foe.types): foe.hp = 0; s.kill_hooks(me, foe)
            elif k == 'kocharge':
                if foe.hp <= 0: me.charge = min(me.ppmax, me.charge + op[1])
            elif k == 'koheal':
                if foe.hp <= 0: s.heal(me, int(foe.maxhp * op[1]))
            elif k == 'delay': s.sides[1 - me.side.idx].delays.append([op[1], op[2] + (0 if len(op) > 3 else ap_), me.side.idx])
            elif k == 'atk':
                for _ in range(op[1]):
                    if foe.hp > 0: s.attack(me, foe, free=True)
                if foe.hp <= 0 and False: pass
            elif k == 'reflect': me.reflect = (op[1], op[2])
            elif k == 'spiky': me.spiky = (op[1], op[2])
            elif k == 'cure':
                for n in NEG: me.st[n] = 0
                me.st['poison_n'] = 0
            elif k == 'ap_foe': foe.ap = max(0, foe.ap + op[1])
            elif k == 'gcharge': me.charge = min(me.ppmax, me.charge + op[1])
            elif k == 'mhp': me.maxhp += op[1]; me.hp += op[1]
            elif k == 'selfhurt':
                me.hp -= op[1]
                if me.hp <= 0: me.hp = 1
            elif k == 'nextatk': me.nextatk += op[1]
        if me.ability == 'DRUM_BEATING': me.cycle += 1
        f = me.fl
        if f:
            if f['aqua']: me.charge = min(me.ppmax, me.charge + 1)
            if f['stardust']: me.shield += int(f['stardust'])
            if f['elixir'] and not me.elixir_used: me.elixir_used = True; me.charge = me.ppmax
            if f['terrain']: me.side.carry['shield'] += 2
            if f['ball']: me.side.carry['shield'] += 3
            if f['surf'] and not me.surf_used: me.surf_used = True; s.sides[1 - me.side.idx].pending += 3
            if me.berries: s.berry_check(me, 'cast')
        # synergy on cast
        L = me.lv
        if L('FIRE') >= 2: me.perm['atk'] += 1
        if L('WATER') >= 2: me.charge = min(me.ppmax, me.charge + 1)
        if L('SOUND'):
            if me.perm['soundn'] < L('SOUND'):
                me.perm['soundn'] += 1; me.perm['atk'] += 1
                if L('SOUND') == 3 and me.perm['soundn'] == 1: me.perm['spd'] += 1
            if L('SOUND') == 3: me.side.carry['charge'] += 1
        if foe.hp <= 0: pass

    def kill_hooks(s, killer, dead):
        killer.kos += 1
        L = killer.lv
        kp = killer.pas
        if kp in ('moxie', 'beastatk'): killer.perm['atk'] += 1
        elif kp == 'beastap': killer.ap += 2
        elif kp == 'soul': killer.ap += 2; killer.charge = min(killer.ppmax, killer.charge + 1)
        if L('MONSTER') >= 2:
            killer.perm['atk'] += 1; s.heal(killer, 1)
            if L('MONSTER') >= 3: killer.maxhp += 1; killer.hp += 1
            if L('MONSTER') == 4: killer.perm['atk'] += 1

    # ---------- acting ----------
    def act(s, me, foe):
        if me.hp <= 0 or foe.hp <= 0: return
        if me.st['sleep'] > 0 or me.st['freeze'] > 0:
            s.say(f'{me.name} skips'); return
        s.say(f'{me.name} attacks {foe.name}')
        s.acting = me
        s.attack(me, foe)
        if me.pas == 'durant' and foe.hp > 0:
            nb = sum(1 for c in me.side.lineup if c is not me and 'BUG' in c.types)
            if nb: s.hit(me, foe, nb, 'T')
        if me.pas == 'spinda' and foe.hp > 0 and foe.st['confuse'] > 0: s.hit(me, foe, 2, 'S')
        if foe.hp <= 0: s.kill_hooks(me, foe); return
        if me.charge >= me.ppmax + (1 if foe.lv('ELECTRIC') == 3 else 0) and me.st['flinch'] <= 0 and not me.fl['nullify']:
            s.say(f'{me.name} casts {tr["ability"].get(me.ability, me.ability)}')
            s.cast(me, foe)

    # ---------- end of a Pokemon's own turn ----------
    def snap(s, turn, mover, bar):
        sides = []
        for sd in s.sides:
            cards = []
            for i, c in enumerate(s.orig[sd.idx]):
                cards.append(dict(hp=max(0, c.hp), mx=c.maxhp, ent=c in sd.fielded, dead=(c in sd.fielded and c.hp <= 0)))
            a = sd.active
            act = None
            if a is not None:
                act = dict(i=s.orig[sd.idx].index(a), hp=max(0, a.hp), mx=a.maxhp, sh=a.shield, ch=a.charge, pp=a.ppmax,
                           atk=a.eff('atk'), df=a.eff('def'), sd=a.eff('sdef'), sp=a.eff('spd'), ap=a.ap,
                           st={k: v for k, v in a.st.items() if v and k not in ('poison_n', 'burn_pow')}, pois=a.st.get('poison_n', 0), prot=a.protect, sw=a.swarm)
            sides.append(dict(cards=cards, act=act))
        s.snaps.append(dict(t=turn, mv=mover, bar=bar, sides=sides, ev=s.buf[:])); s.buf.clear()

    def end_turn(s, me, foe):
        c = me; L = c.lv; sd = me.side
        if c.hp > 0:
            c.rounds_on += 1
            if EXH and getattr(s, 'tn', 0) > EXH: c.hp -= (s.tn - EXH) // EXS + 1
            if c.st['burn'] > 0 and not (c.fl['vest'] or c.fl['vestburn']): c.hp -= ((c.st['burn_pow'] or 1) if not (c.side.rk.get('r_atk') and c.rounds_on % 2) else 0)
            if c.st.get('poison_n', 0) > 0:
                pn = c.st['poison_n']
                if c.fl['vest']: pn //= 2
                if c.pas == 'toxic': pn //= 2
                pn = max(0, pn - c.side.rk.get('r_clay', 0))
                if c.pas == 'komala': pn = 0
                if c.pas == 'gligar' and not c.gl_used and pn > 0: c.gl_used = True; s.heal(c, pn); pn = 0
                c.hp -= pn
            s.item_turn(c, foe)
            if c.fl['cookburn'] if False else False: pass
            if L('GRASS'):
                h = [1, 2, 2, 3][L('GRASS') - 1]
                over = max(0, c.hp + h - c.maxhp); s.heal(c, h)
                if L('GRASS') >= 3 and over and c.perm['gmax'] < (3 if L('GRASS') == 3 else 5): c.perm['gmax'] += 1; c.maxhp += 1; c.hp += 1
            if L('FIRE') >= 3 and c.fire_n < (4 if L('FIRE') == 3 else 6): c.fire_n += 1; c.perm['atk'] += 1
            if L('GROUND'):
                lv = L('GROUND')
                if lv >= 2 or c.rounds_on % 2 == 0:
                    cap = {1: 2, 2: 2, 3: 3, 4: 5}[lv]
                    if c.ground_n < cap:
                        c.ground_n += 1; c.perm['defn'] += 1
                        if lv >= 3: c.perm['atk'] += 1
            if c.dish.get('regen'): s.heal(c, c.dish['regen'])
            if L('AQUATIC') >= 2 and c.rounds_on == 3:
                for n in NEG: c.st[n] = 0
                if foe and foe.hp > 0: s.hit(c, foe, {2: 2, 3: 4, 4: 6}[L('AQUATIC')], 'T')
                if L('AQUATIC') >= 3: s.heal(c, 2 if L('AQUATIC') == 3 else 4)
        # delayed effects cast by me land on the opposing card after my Nth turn
        osd = s.sides[1 - sd.idx]; nd = []
        for dl in osd.delays:
            if dl[2] == sd.idx:
                dl[0] -= 1
                if dl[0] <= 0:
                    t = osd.active
                    if t and t.hp > 0: s.hit(c, t, dl[1], 'S')
                    continue
            nd.append(dl)
        osd.delays = nd
        # durations count the affected Pokemon's own turns
        for n in ('para', 'flinch', 'charm', 'wound', 'armor', 'fatigue', 'burn'):
            if c.st[n] > 0: c.st[n] -= 1
        c.tmp = [(a, b, r - 1) for a, b, r in c.tmp if r - 1 > 0]
        if c.reflect[0] > 0: c.reflect = (c.reflect[0] - 1, c.reflect[1])
        if c.spiky[0] > 0: c.spiky = (c.spiky[0] - 1, c.spiky[1])

    # ---------- main: initiative bar ----------
    def run(s):
        A, B = s.sides
        for sd in s.sides: s.enter(sd, s.pick(sd, None, opener=True))
        for sd in s.sides: s.spotlight(sd)
        bar = 0; last = None; turns = 0
        if s.rec:
            s.say('Both sides reveal their lineups; Pokemon enter in set order'); s.snap(0, None, 0)
        # at 0 (even) the faster Pokemon starts; equal speed -> coin flip
        while True:
            turns += 1; s.nrounds = turns / 2; s.tn = turns
            if turns > s.max_rounds * 2: return s.result(timeout=True)
            a, b = A.active, B.active
            if bar > 0: mover = A
            elif bar < 0: mover = B
            else:
                if last is None:
                    sa, sb = a.eff('spd'), b.eff('spd')
                    mover = A if sa > sb else B if sb > sa else (A if s.rng.random() < .5 else B)
                else: mover = B if last is A else A
            me = mover.active; foe = s.sides[1 - mover.idx].active
            cost = foe.eff('spd')
            me.protect = False
            if me.st['sleep'] > 0 or me.st['freeze'] > 0:
                s.say(f'{me.name} skips')
                me.st['sleep'] = max(0, me.st['sleep'] - 1); me.st['freeze'] = max(0, me.st['freeze'] - 1)
            else:
                s.act(me, foe)
                s.acting = None
            s.end_turn(me, foe)
            bar += -cost if mover is A else cost
            last = mover
            if CAP:
                for _sd in s.sides:
                    _a = _sd.active; _cap = max(1, int(_a.maxhp * CAP + .5))
                    if _a.shield > _cap: _a.shield = _cap
            if OT_START and s.nrounds > OT_START and me.hp > 0:
                od = 1 + int((s.nrounds - OT_START) // OT_STEP)
                me.hp -= od; s.say(f'Overtime: {me.name} takes {od} true damage')
            for sd0 in s.sides:
                a0 = sd0.active
                if a0.hp <= 0 and (a0.fl['revive'] or getattr(a0, 'rhalf', False)) and not a0.revived:
                    a0.revived = True; a0.hp = a0.maxhp if a0.fl['revive'] else max(1, a0.maxhp // 2)
                    if a0.fl['revive'] >= 2: sd0.carry['shield'] += 4
                    s.say(f'{a0.name} is revived')
                    continue
                if a0.hp <= 0 and not a0.cover_used:
                    pass
                if a0.hp <= 0: s.say(f'{a0.name} faints')
            dead = [sd for sd in s.sides if sd.active.hp <= 0]
            for sd in dead:
                sd.fallen += 1; d = sd.active
                if 'FIELD' in d.types: sd.field_ko += 1
                if d.fl['rusted']: sd.carry['atk'] += 1
                if d.fl['gracidea']: sd.carry['spd'] += 1
                if d.fl['spelltag']:
                    o = s.sides[1 - sd.idx].active
                    if o is not None and o.hp > 0: o.hp -= 2
                if d.lv('FLORA'):
                    l = d.lv('FLORA'); sd.carry['maxhp'] += [3, 4, 4, 5][l - 1]
                    if l >= 3: sd.carry['atk'] += 1
                    if l == 4: sd.carry['spd'] += 1
            if dead:
                lost = [sd for sd in dead if not sd.lineup]
                if len(lost) == 2: return s.result(draw=True)
                if lost: return s.result(loser=lost[0])
                alive = [sd for sd in s.sides if sd not in dead]
                for sd in dead:
                    foe_card = alive[0].active if alive else None
                    s.enter(sd, s.pick(sd, foe_card))
                    while sd.active.hp <= 0:
                        sd.fallen += 1
                        if not sd.lineup: return s.result(loser=sd)
                        s.enter(sd, s.pick(sd, foe_card))
            if s.rec: s.snap(turns, mover.idx, bar)

    def result(s, loser=None, draw=False, timeout=False):
        if s.rec:
            s.say('Battle over: ' + ('draw' if draw else 'time limit' if timeout else f'side {1 - loser.idx} wins')); s.snap(int(s.nrounds * 2), None, 0)
        A, B = s.sides
        if timeout:
            ta = sum(c.hp for c in A.lineup) + max(0, A.active.hp); tb = sum(c.hp for c in B.lineup) + max(0, B.active.hp)
            if ta == tb: return dict(winner=None, left=0, rounds=s.nrounds, timeout=True)
            w = A if ta > tb else B
        elif draw: return dict(winner=None, left=0, rounds=s.nrounds, timeout=False)
        else: w = B if loser is A else A
        left = len(w.lineup) + (1 if w.active.hp > 0 else 0)
        return dict(winner=w.idx, left=left, rounds=s.nrounds, timeout=timeout)
