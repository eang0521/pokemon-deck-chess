import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os
"""Item mechanics for Duel (mixin). All hooks are cheap no-ops for cards without items."""
import collections, math
from engine import PW, D, NEG, resolve
from items import ITEMS, ORDER

CRAFT = [k for k in ORDER if ITEMS[k]['cat'] == 'Crafted' and 'wonder' not in ITEMS[k]['flags']]
FOODS = [k for k in ORDER if ITEMS[k]['cat'] == 'Food']
_WT = {}
def _wonder_pool(tier):
    # items of the print run by tier that can simply ride along for a battle
    if not _WT:
        import json
        d = json.load(open(f'{ROOT}/pac-digital/build/data.json'))
        for it in d['itemdeck']:
            f = ITEMS[it['key']]['flags']
            if any(x in f for x in ('slot', 'econ_income', 'econ_ko', 'econ_churn', 'wonder', 'evo_only')): continue
            _WT.setdefault(it['tier'], []).append(it['key'])
    return _WT.get(tier, [])
def _i(me, arr): return arr[min(max(me.stars, 1), 3) - 1]
def _ceil(x): return int(math.ceil(x))

TMP = {
    'TM_RAGE': lambda v, c, me, foe: [('tmp', 'me', 'atk', max(4, 2 + (me.maxhp - me.hp) * 8 // max(1, me.maxhp)), 6)],
    'TM_RETURN': lambda v, c, me, foe: [('S', int(D(_i(me, [20, 40, 80])) * 2.5 + .5)), ('buff', 'ap', 3)],
    'TM_COUNTER': lambda v, c, me, foe: [('S', max(4, int((me.maxhp - me.hp) * 1.5 + .5)))],
    'TM_DISABLE': lambda v, c, me, foe: [('S', int(D(_i(me, [12, 25, 50])) * 2.5 + .5)), ('st', 'foe', 'flinch', 2)],
    'TM_BULK_UP': lambda v, c, me, foe: [('buff', 'atk', max(3, me.base['atk'])), ('buff', 'def', max(2, me.base['defn']))],
    'TM_CHARGE': lambda v, c, me, foe: [('buff', 'xdmg', 2), ('S', max(1, int(D(_i(me, [20, 40, 80])) * 1.5 + .5)))],
    'TM_REFLECT': lambda v, c, me, foe: [('reflect', 5, 150)],
    'TM_PAYDAY': lambda v, c, me, foe: [('S', int(D(_i(me, [15, 30, 60])) * 2.5 + .5)), ('S', int(D(_i(me, [15, 30, 60])) * 2.5 + .5))],
    'TM_FOCUS_PUNCH': lambda v, c, me, foe: [('delay', 1, 4 * me.eff('atk'))],
    'TM_HYPER_BEAM': lambda v, c, me, foe: [('S', max(1, int(D(_i(me, [65, 130, 250])) * 1.0 + .5))), ('st', 'me', 'fatigue', 1)],
    'TM_SUBSTITUTE': lambda v, c, me, foe: [('shield', max(4, _ceil(me.maxhp / 3))), ('protect',)],
    'TM_SKILL_SWAP': lambda v, c, me, foe: PW[foe.ability](foe.v, foe.raw, me, foe) + [('shield', 3)],
}
PW.update(TMP)

class ItemFX:
    # ---------- setup ----------
    def setup_items(s, sd):
        sd.gems = collections.Counter(); sd.rk = {}; sd.battery = 0
        for c in sd.lineup:
            out = []
            for k in list(getattr(c, 'items', [])):
                fl = ITEMS[k]['flags']
                if fl.get('wonder'):
                    out.append(k); _room = 3 - len(c.items)
                    for _t in ('III', 'II'):
                        if _room <= 0: break
                        _pool = [x for x in _wonder_pool(_t) if x not in c.items and x not in out]
                        if _pool: out.append(s.rng.choice(_pool)); _room -= 1
                elif fl.get('chef'):
                    out += [s.rng.choice(FOODS), k]
                else: out.append(k)
            c.items_eff = out
            c.fl = collections.Counter(); c.itst = collections.Counter()
            types = set(c.types)
            for k in out:
                it = ITEMS[k]
                for a, v in it['stats'].items(): c.itst[a] += v
                for a, v in it['flags'].items():
                    if a == 'type': types.add(v)
                    elif a == 'gem': sd.gems[v] += 1
                    elif a == 'rock' or a == 'food' or a == 'perm': pass
                    elif isinstance(v, (int, float)): c.fl[a] += v
                    else: c.fl[a] = v
                if it['flags'].get('rock'):
                    for a, v in it['flags'].items():
                        if a.startswith('r_'): sd.rk[a] = max(sd.rk.get(a, 0), v)
                if it['flags'].get('battery'): sd.battery += 1
            c.types = types
            if c.fl['tm']: c.ability = 'TM_' + c.fl['tm']
            berries = [k for k in out if ITEMS[k]['flags'].get('berry')]
            c.berries = berries

    # ---------- entering ----------
    def item_enter(s, sd, c):
        f, st = c.fl, c.itst; rk = sd.rk
        if f['cheap']: c.ppmax = max(2, c.ppmax - 1)
        if st['hp'] or f['hpmult']:
            add = st['hp'] + int(round(c.hp0 * f['hpmult']))
            c.maxhp = max(1, c.maxhp + add); c.hp = min(c.maxhp, max(1, c.hp + add))
        c.perm['atk'] += st['atk'] + rk.get('r_atk', 0); c.perm['defn'] += st['df']
        c.perm['sdef'] += st['sdf'] + rk.get('r_sdf', 0); c.perm['spd'] += st['spd'] + rk.get('r_spd', 0)
        c.ap += st['ap']; c.charge += st['ch']; c.shield += st['sh'] + rk.get('r_shield', 0)
        c.critpct = st['crit'] + rk.get('r_crit', 0)
        if f['flameorb'] or f['rusted']: c.perm['atk'] += max(1, int(c.base['atk'] * .5 + .5))
        if f['egg']:
            for k_ in ('atk', 'defn', 'sdef'):
                if c.base[k_] > 0: c.perm[k_] += _ceil(c.base[k_] * .5)
        if f['swarm']: c.swarm += int(f['swarm'])
        if f['abshield']: c.shield += 3; c.immturn = 3
        if f['starpiece']: pass  # Star Piece now doubles cast numbers (see Duel.cast)
        if f['revive']: pass
        if f['expshare']:
            others = [x for x in sd.fielded if x is not c] + sd.lineup
            if others:
                for k_, a_ in (('atk', 'atk0'), ('defn', 'def0'), ('sdef', 'sdef0')):
                    best = max(getattr(x, a_) for x in others); gap = best - c.base[k_] - c.perm[k_]
                    if gap > 0: c.perm[k_] += gap
        if f['battery'] and False: pass
        if sd.battery and 'ELECTRIC' in c.types: c.perm['spd'] += min(2, sd.battery)
        if f['cover'] is not None and c.owed: c.hp = max(1, c.hp - c.owed); c.owed = 0
        if f['poffin'] and c.berries:
            c.shield += sum(ITEMS[k]['flags']['berry'] for k in c.berries); c.berry_used = True
        if f['juice']: c.itn['juice'] = 1
        if f['curry']: c.tmp.append(('atk', 2, 3))
        c.shtot = c.shield
        c.perm['spd'] -= 0

    # ---------- statuses ----------
    def blocks_status(s, tgt, name, r):
        """Return (blocked, duration)."""
        if name not in NEG: return False, r
        f = tgt.fl
        if tgt.pas == 'komala' and name in ('burn', 'poison', 'freeze', 'para'): return True, r
        if tgt.pas == 'spinda' and name == 'confuse': return True, r
        if f['immune_neg'] or tgt.immturn > 0: return True, r
        if f['immune_sleep'] and name == 'sleep': return True, r
        if name in tgt.imm: return True, r
        if f['boots'] and name == 'flinch': return True, r
        if f['twist']:
            tgt.perm['atk'] += 1; return True, r
        if tgt.side.rk.get('r_odd'): r = max(1, r - 1)
        if f['vestburn'] and name == 'burn': return True, r
        return False, r

    # ---------- berries ----------
    def berry_check(s, c, trigger='hp'):
        if c.berry_used or not c.berries or c.hp <= 0: return
        if trigger == 'hp' and c.hp * 2 > c.maxhp: return
        fire = None
        for k in c.berries:
            fl = ITEMS[k]['flags']
            if trigger == 'cast' and not fl.get('b_charge'): continue
            if trigger == 'hp' or trigger == 'cast': fire = fire or k
        if trigger == 'cast':
            if c.casts != 1: return
        if fire is None: return
        c.berry_used = True
        for k in c.berries:
            fl = ITEMS[k]['flags']
            heal = fl['berry']
            if fl.get('b_aguav'):
                heal = max(heal, _ceil(c.maxhp / 2));
                if fl['b_aguav'] == 1: c.st['confuse'] = max(c.st['confuse'], 1)
            s.heal(c, int(heal * (1.3 if c.healboost else 1)))
            c.shield += fl.get('b_shield', 0); c.perm['sdef'] += fl.get('b_sdf', 0); c.perm['defn'] += fl.get('b_df', 0)
            c.perm['atk'] += fl.get('b_atk', 0); c.perm['spd'] += fl.get('b_spd', 0); c.ap += fl.get('b_ap', 0)
            c.critpct += fl.get('b_crit', 0); c.charge = min(c.ppmax, c.charge + fl.get('b_charge', 0))
            if fl.get('b_heal'): c.healboost = 1
            if fl.get('b_cure'):
                for n in NEG: c.st[n] = 0
                c.st['poison_n'] = 0; c.immturn = 3
            if fl.get('b_protect'): c.protect = True
            if fl.get('b_spiky'): c.spiky = (fl['b_spiky'], 1)
            if fl.get('b_reflect'): c.reflect = (fl['b_reflect'], 50)
            if fl.get('b_immune'): c.imm.add(fl['b_immune'])
        if c.itn['juice']: c.shield += 5
        s.say(f'{c.name} eats its berry')

    # ---------- attacking ----------
    def item_attack(s, me, foe, dealt, crit):
        f = me.fl
        if not f and not me.side.rk and not me.perm['xdmg']: return
        me.itn['att'] += 1; a = me.itn['att']
        ev = lambda n: n and a % int(n) == 0
        rk = me.side.rk
        if f['wide'] and a % 2 == 0:   # Wide Lens: every 2nd attack also has SPLASH 1
            s.sides[1 - me.side.idx].pending += 1
        if me.perm['xdmg'] and foe.hp > 0: s.hit(me, foe, me.perm['xdmg'], 'T')
        if f['glove'] and foe.hp > 0: s.hit(me, foe, 1, 'T')
        if f['wand'] and foe.hp > 0:
            x = 1
            if f['w_surround']: x = 2
            if f['w_twoedge']:
                x = 3
                if a % 2 == 0: s.hit(me, me, 1, 'T')
            if f['w_crit'] and crit: x += 2
            if f['w_spirit']: x += me.casts // 2
            s.hit(me, foe, x, 'S')
            if f['w_guide']: s.sides[1 - me.side.idx].pending += (x + 1) // 2
            if ev(f['w_tunnel']): s.sides[1 - me.side.idx].pending += 2
            if f['w_pounce']: pass
        if foe.hp <= 0: return
        if dealt <= 0: return
        if f['armorbreak']: s.apply_st(foe, 'armor', 1)
        if f['reaper'] and crit: s.hit(me, foe, 1, 'S')
        if f['scope'] and crit: foe.charge = max(0, foe.charge - 1)
        if f['blackbelt'] and crit: me.shield += (dealt + 1) // 2
        if f['shellbell']: s.heal(me, 1)
        if rk.get('r_blood') and foe.st['wound'] > 0: s.heal(me, 1)
        sh = f['shred']
        if sh == 'df': foe.perm['defn'] = max(foe.perm['defn'] - 1, -2)
        elif sh == 'sdf': foe.perm['sdef'] = max(foe.perm['sdef'] - 1, -2)
        if ev(f['parat']): s.apply_st(foe, 'para', 1)
        if f['upgrade'] and a % 2 == 0 and me.perm['upg'] < 4: me.perm['upg'] += 1; me.perm['spd'] += 1
        if f['blueorb'] and a % 3 == 0:
            s.hit(me, foe, 1, 'S'); foe.charge = max(0, foe.charge - 1)
        if f['loaded'] and a % 2 == 0: s.sides[1 - me.side.idx].pending += max(1, int(dealt * .5))
        if f['dst']:
            if a % 2 == 0: me.charge += 1
        if rk.get('r_freeze') and a % rk['r_freeze'] == 0: s.apply_st(foe, 'freeze', 1)
        # wand riders
        if ev(f['w_steal']): foe.maxhp = max(1, foe.maxhp - 1); foe.hp = min(foe.hp, foe.maxhp); me.maxhp += 1; me.hp += 1
        if ev(f['w_spirit']): me.charge += 1
        if ev(f['w_conf']): s.apply_st(foe, 'confuse', 1); foe.perm['sdef'] = max(foe.perm['sdef'] - 1, -foe.base['sdef'])
        if ev(f['w_petrify']): s.apply_st(foe, 'flinch', 1); foe.perm['defn'] = max(foe.perm['defn'] - 1, -foe.base['defn'])
        if ev(f['w_slow']): s.apply_st(foe, 'para', 2)
        if ev(f['w_sleep']): s.apply_st(foe, 'sleep', 1); foe.perm['atk'] = max(foe.perm['atk'] - 1, -foe.base['atk'])
        if ev(f['w_warp']): s.apply_st(foe, 'flinch', 1)
        if ev(f['w_switch']): foe.charge = max(0, foe.charge - 1)
        if ev(f['w_whirl']): s.apply_st(foe, 'flinch', 1); s.hit(me, foe, 1, 'T')

    def item_first_hit(s, me, foe):
        f = me.fl
        fs = f['first_status']
        if fs and foe.hp > 0:
            if fs == 'freeze': s.apply_st(foe, 'freeze', 1)
            elif fs == 'charm': s.apply_st(foe, 'charm', 2)
            elif fs == 'flinch2': s.apply_st(foe, 'flinch', 2)

    # ---------- when hit ----------
    def item_on_hit(s, src, dst, amount, kind, basic, dmg_taken, absorbed):
        f = dst.fl
        if not f and not dst.side.rk: return
        if f['barb'] and basic:
            s.hit(dst, src, 1, 'T'); s.apply_st(src, 'wound', 1)
        if f['w_pounce'] and basic:
            dst.itn['hit'] += 1
            if dst.itn['hit'] % int(f['w_pounce']) == 0: s.hit(dst, src, 2, 'S')
        if f['muscle']:
            dst.itn['mus'] += 1
            if dst.itn['mus'] % 3 == 0 and dst.perm['musn'] < 3:
                dst.perm['musn'] += 1; dst.perm['atk'] += 1; dst.perm['defn'] += 1; dst.perm['spd'] += 1
        if f['explosive'] and not dst.expl_used and dst.shield <= 0 and absorbed > 0:
            dst.expl_used = True; s.hit(dst, src, max(1, dst.shtot // 2), 'S')
        if dst.hp > 0:
            if f['bulb'] and not dst.bulb_used and dst.hp * 2 <= dst.maxhp:
                dst.bulb_used = True; s.hit(dst, src, max(1, dst.absorbed), 'S')
            if f['charm30'] and not dst.charm_used and dst.hp * 2 <= dst.maxhp:
                dst.charm_used = True; dst.protect = True; dst.charge = min(dst.ppmax, dst.charge + 1)
            if f['smoke'] and not dst.smoke_used and dst.hp * 2 <= dst.maxhp:
                dst.smoke_used = True; dst.shield += 4; s.apply_st(src, 'para', 2)
            if dst.berries: s.berry_check(dst, 'hp')

    # ---------- own turn tick ----------
    def item_turn(s, c, foe):
        f = c.fl; rk = c.side.rk; n = c.rounds_on
        if c.immturn > 0: c.immturn -= 1
        if not f and not rk: return
        if f['soul']:
            if c.ap < 4 + c.itst['ap']: c.ap += 1
            if n % 3 == 0: c.charge = min(c.ppmax, c.charge + 1)
        if f['greenorb'] and n % 2 == 0:
            over = c.hp + 1 > c.maxhp
            s.heal(c, 1)
            if over: c.charge = min(c.ppmax, c.charge + 1)
        if f['mach'] and n % int(f['mach'] if f['mach'] > 1 else 4) == 0 and c.perm['mach'] < 3: c.perm['mach'] += 1; c.perm['spd'] += 1
        if f['metronome'] and n % int(f['metronome']) == 0: c.charge = min(c.ppmax, c.charge + 1)
        if f['pokerus'] and n % 3 == 0 and c.perm['pok'] < 3: c.perm['pok'] += 1; c.perm['atk'] += 1; c.ap += 1
        if f['flameorb'] and n % 2 == 0: c.hp -= 1
        if rk.get('r_heal') and n % rk['r_heal'] == 0: s.heal(c, 1)
        if rk.get('r_charge') and n % rk['r_charge'] == 0: c.charge = min(c.ppmax, c.charge + 1)
        if rk.get('r_speed') and n % rk['r_speed'] == 0 and c.perm['rs'] < 3: c.perm['rs'] += 1; c.perm['spd'] += 1
