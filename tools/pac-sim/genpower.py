import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
"""Generate charge powers (text + simulator ops) for non-Core abilities from PAC ability descriptions.
make(ab, stars, c) -> (role, text, opsfn, apmode)   c = Raw-like object with hp, atk, defn, sdef, spd, hpc, atkc."""
import re, json, math
LOC = f'{ROOT}/keldaancommunity/pokemonautochess/app/public/dist/client/locales/en/translation.json'
TR = json.load(open(LOC))['ability_description']

def D(x): return max(1, int(x / 10 + 0.5))
def PA(p, base): return max(1, int(p / 100 * base / 6 + 0.5))
def S(x): return min(3, max(1, int(x / 3 + 0.5)))
def AT(x): return max(1, int(x / 5 + 0.5))
def SP(x): return max(1, int(x / 7 + 0.5))
def ceil(x): return int(math.ceil(x))

STATUS = {'PARALYSIS': ('para', 'PARALYZE'), 'BURN': ('burn', 'BURN'), 'POISONED': ('poison', 'POISON'), 'SLEEP': ('sleep', 'SLEEP'), 'FREEZE': ('freeze', 'FREEZE'),
          'CONFUSION': ('confuse', 'CONFUSE'), 'CHARM': ('charm', 'CHARM'), 'WOUND': ('wound', 'WOUND'), 'SILENCE': ('flinch', 'FLINCH'), 'FLINCH': ('flinch', 'FLINCH'),
          'ARMOR_BREAK': ('armor', 'ARMOR BREAK'), 'FATIGUE': ('fatigue', 'FATIGUE'), 'LOCKED': ('locked', 'LOCK'), 'BLINDED': ('confuse', 'CONFUSE'),
          'CURSE': ('fatigue', 'FATIGUE'), 'POSSESSED': ('confuse', 'CONFUSE')}
STATNAME = {'ATK': 'atk', 'DEF': 'def', 'SPE_DEF': 'sdef', 'SPEED': 'spd', 'AP': 'ap', 'PP': 'pp'}
STATTXT = {'atk': 'ATK', 'def': 'DEF', 'sdef': 'SP.DEF', 'spd': 'SPEED', 'ap': 'AP'}

def arrays(desc, stars):
    """list of (start, end, value, tags) for each [..] in order"""
    out = []
    for m in re.finditer(r'\[([^\]]*)\]', desc):
        nums = []; tags = set()
        for t in m.group(1).split(','):
            t = t.strip()
            try: nums.append(float(t))
            except ValueError: tags.add(t.split('=')[0])
        if nums: out.append((m.start(), m.end(), nums[min(stars - 1, len(nums) - 1)], tags))
        elif tags: out.append((m.start(), m.end(), None, tags))
    return out

def num_at(arrs, desc, pos_re, default=None, after=True):
    """value of the first array found just before/after a regex match"""
    m = re.search(pos_re, desc)
    if not m: return default
    best = None
    for a in arrs:
        if a[2] is None: continue
        if after and a[1] <= m.start() + 1 and m.start() - a[1] < 14: best = a[2]
    return best if best is not None else default

def _ov(role, parts, apmode='first'): return lambda stars, c: (role, parts(stars, c) if callable(parts) else parts, apmode, False)
def _hp(pct, c): return max(1, round(pct / 100 * c.hpc))
def _star(arr, stars): return arr[min(stars - 1, len(arr) - 1)]
OVERRIDE = {
 'ENCORE': _ov('Support', [('gcharge', 1), ('buff', 'ap', 1)]),
 'MIMIC': _ov('Control', lambda st, c: [('S', 3 + st, False), ('gcharge', 1)]),
 'METRONOME': _ov('Striker', lambda st, c: [('S', 4 + 2 * st, False)]),
 'SKETCH': _ov('Support', [('gcharge', 1), ('buff', 'ap', 1)]),
 'KNOWLEDGE_THIEF': _ov('Control', lambda st, c: [('S', 2 + st, False), ('tmp', 'sdef', 1, 2)]),
 'ENTRAINMENT': _ov('Control', [('gcharge', 1), ('foecharge', -1)]),
 'SHIELDS_DOWN': _ov('Tank', lambda st, c: [('shield', 2 + st)]),
 'SHIELDS_UP': _ov('Tank', lambda st, c: [('buff', 'def', 2), ('shield', 1 + st)]),
 'UNBOUND': _ov('Striker', [('buff', 'atk', 2), ('buff', 'spd', 1), ('buff', 'ap', 2)], 'none'),
 'VESPIQUEN_ORDERS': _ov('Tank', lambda st, c: [('shield', 2 + st), ('carry', 'shield', 2)]),
 'TRICK_OR_TREAT': _ov('Control', lambda st, c: [('S', 2 + st, False), ('st', 'foe', 'fatigue', 2, 'FATIGUE')]),
 'STUFF_CHEEKS': _ov('Tank', lambda st, c: [('shield', 2 + 2 * st), ('heal', 1 + st)]),
 'FLORAL_HEALING': _ov('Support', lambda st, c: [('heal', 2 + st)]),
 'BEAT_UP': _ov('MultiHit', lambda st, c: [('S', 2, False)] * _star([2, 3, 4, 5], st), 'each_half'),
 'SHADOW_CLONE': _ov('Tank', lambda st, c: [('shield', _hp(_star([50, 50, 90, 100], st), c) // 2 + 1)]),
 'RECOVER': _ov('Support', lambda st, c: [('heal', _hp(_star([25, 25, 50, 100], st), c))]),
 'SHORE_UP': _ov('Support', lambda st, c: [('heal', _hp(_star([20, 25, 40, 80], st), c))]),
 'SPITE': _ov('Control', [('foecharge', -1), ('carry', 'charge', 1)]),
 'WONDER_ROOM': _ov('Control', [('st', 'foe', 'armor', 2, 'ARMOR BREAK')]),
 'SPICY_EXTRACT': _ov('Support', [('buff', 'atk', 1), ('carry', 'atk', 1)]),
 'DECORATE': _ov('Support', [('carry', 'atk', 1), ('carry', 'charge', 1)]),
 'GROWTH': _ov('Tank', lambda st, c: [('mhp', D(_star([10, 20, 40, 80], st)) + 1), ('buff', 'atk', max(1, AT(_star([3, 5, 7, 14], st))))]),
 'COSMIC_POWER_MOON': _ov('Support', [('carry', 'charge', 1), ('gcharge', 1)]),
 'COSMIC_POWER_SUN': _ov('Support', [('carry', 'atk', 1), ('buff', 'atk', 1)]),
 'ELECTRIC_SURGE': _ov('Support', [('carry', 'spd', 1), ('buff', 'spd', 1)]),
 'GRASSY_SURGE': _ov('Support', [('carry', 'atk', 1), ('buff', 'atk', 1)]),
 'TAILWIND': _ov('Support', [('carry', 'spd', 2), ('buff', 'spd', 1)]),
 'JUDGEMENT': _ov('Striker', [('dyn', 'top3', 2, 'S')]),
 'EXPLOSION': _ov('Striker', lambda st, c: [('S', D(_star([50, 100, 200, 400], st)) , True), ('selfhurt', 'amt', max(1, D(_star([50, 100, 200, 400], st)) // 2))]),
}

def _make(ab, stars, c):
    desc = re.sub(r'\s+', ' ', TR.get(ab, '')).replace('BOARD_EFFECT:', '').strip()
    if ab in OVERRIDE: return OVERRIDE[ab](stars, c)
    arrs = arrays(desc, stars)
    vals = [a for a in arrs if a[2] is not None and 'LK' not in a[3]]
    low = desc
    area = bool(re.search(r'all (?:enemy|enemies)|ADJACENT enem|in a line|in the path|radius|bounc|random enem|3 enemy|enemies in|cone|every enemy|straight line|row|ahead|all ADJACENT', desc, re.I))
    parts = []   # structured
    # ---- damage
    kind = 'S'
    if re.search(r'\bTRUE\b', desc) and not re.search(r'SPECIAL', desc): kind = 'T'
    elif re.search(r'PHYSICAL', desc) and not re.search(r'SPECIAL', desc): kind = 'P'
    has_dmg = bool(re.search(r'\bdeal|dealing|damage|SPECIAL|TRUE\b|PHYSICAL', desc, re.I))
    dmg = None; role = 'Striker'; mode = 'first'; mult_hits = 1
    m_atk = re.search(r'\[([^\]]*)\]\s*%\s*(?:of )?(?:his |its |the user\'s )?ATK', desc)
    m_hpmax_user = re.search(r"\[([^\]]*)\]\s*%\s*of the user's max HP", desc)
    m_hpmax_tgt = re.search(r"\[([^\]]*)\]\s*%\s*of (?:their|the target's|its) max HP", desc)
    m_cur = re.search(r"\[([^\]]*)\]\s*%\s*of the user's current HP", desc)
    m_miss = re.search(r"\[([^\]]*)\]\s*%\s*of its missing HP", desc)
    m_def = re.search(r"\[([^\]]*)\]\s*%\s*of the user's DEF", desc)
    pct = lambda m: arrays(m.group(0), stars)[0][2]
    dyn = None
    if m_atk and has_dmg:
        dmg = PA(pct(m_atk), c.atk)
        pre = [a for a in arrs if a[2] is not None and a[1] < m_atk.start() and 'LK' not in a[3]]
        if pre and re.search(r'\]\s*\+\s*$', desc[:m_atk.start()]): dmg += D(pre[-1][2])
    elif m_hpmax_user: dmg = max(1, round(pct(m_hpmax_user) / 100 * c.hpc * .5))
    elif m_hpmax_tgt: dyn = ('tgtmax', pct(m_hpmax_tgt))
    elif m_cur: dmg = max(1, round(pct(m_cur) / 100 * c.hpc * .4))
    elif m_miss: dyn = ('missing', pct(m_miss))
    elif m_def: dmg = PA(pct(m_def), c.defn)
    elif has_dmg and vals:
        v0 = vals[0][2]
        dmg = D(v0)
        # "N SPECIAL [x] times" style
    if dmg is None and dyn is None and has_dmg and not vals:
        m = re.search(r'(\d+) SPECIAL', desc)
        if m: dmg = D(int(m.group(1)))
    # multi hits
    m = re.search(r'(\d+) SPECIAL \[([^\]]*)\] times', desc) or re.search(r'Deal (\d+) SPECIAL \[', desc)
    if re.search(r'(\d+) SPECIAL \[[^\]]*\] times', desc):
        mm = re.search(r'Deal (\d+) SPECIAL \[([^\]]*)\] times', desc)
        n = arrays(mm.group(0), stars)[0][2] if mm else 4
        dmg = D(int(mm.group(1)) * 1.0); mult_hits = max(2, min(5, round(n / 4))); mode = 'each_half'
    m = re.search(r'(\d+|\[[^\]]*\]) times', desc)
    if m and mult_hits == 1 and not re.search(r'(?:more|every|if|per) .{0,10}times', desc):
        txt = m.group(1)
        n = float(txt) if txt.isdigit() else (arrays(txt, stars)[0][2] if arrays(txt, stars) else 2)
        if re.search(r'Strikes? \[LK\] 2 to 5 times', desc): n = 3
        mult_hits = max(2, min(5, int(round(n)))) if n >= 2 else 1
        if mult_hits > 1: mode = 'each_half'
    m = re.search(r'\[([^\]]*)\]\s*(?:small ghosts|bolts|moons|projectiles|petals|stones|rocks|missiles|shards|arrows|needles|bubbles|stars|spears|rings|fireballs|cards|flames|blades)', desc, re.I)
    if m and mult_hits == 1 and has_dmg:
        n = arrays(m.group(0), stars)[0][2]; mult_hits = max(2, min(5, int(round(n / 2)))); mode = 'each_half'
        mm = re.search(r'each dealing (\d+)', desc)
        if mm: dmg = D(int(mm.group(1)))
        elif vals and len(vals) > 1: dmg = D(vals[1][2])
    # per-hit damage must not be huge when the hit count is big
    if mult_hits > 1 and dmg: dmg = max(1, round(dmg * (0.9 if mult_hits == 2 else 0.6 if mult_hits == 3 else .5)))
    cond = None
    mcond = re.search(r'(?:doubled|Double damage|\+\d+% damage|double damage)[^.]*?(?:if|when) ([^.]*)', desc, re.I)
    if mcond:
        c_ = mcond.group(1).lower()
        if 'shield' in c_: cond = ('shield', 2)
        elif re.search(r'suffer|status|freeze|sleep|poison|burn|paraly|confus', c_): cond = ('neg', 2)
        elif 'spe_def is 0' in c_: cond = ('sdef0', 2)
        elif 'less than 50% hp' in c_ or 'below 50%' in c_: cond = ('low', 2)
    splash = area and mult_hits == 1 and kind == 'S' and (dmg or 0) >= 1 and not re.search(r'to the target', desc) is None
    splash = area and mult_hits == 1
    # ---- statuses
    sts = []
    for m in re.finditer(r'(PARALYSIS|BURN|POISONED|SLEEP|FREEZE|CONFUSION|CHARM|WOUND|SILENCE|FLINCH|ARMOR_BREAK|FATIGUE|LOCKED|BLINDED|CURSE)\b(?: for ((?:\[[^\]]*\]|[\d.]+)) seconds)?', desc):
        w = m.group(1)
        # skip statuses that only describe a condition ("if the target suffers from X", "cures")
        pre = desc[max(0, m.start() - 40):m.start()].lower()
        if re.search(r'suffer|already|cure|immune|if the target|removes|with burn|enemies with', pre): continue
        if w == 'CURSE' and 'Inflict the highest' not in desc: continue
        sec = None
        if m.group(2):
            sec = float(m.group(2)) if re.match(r'[\d.]+$', m.group(2)) else (arrays(m.group(2), stars)[0][2] if arrays(m.group(2), stars) else 2)
        r = S(sec) if sec else 1
        if w == 'LOCKED': r = 1
        if w in ('ARMOR_BREAK',): r = max(1, min(2, r))
        who = 'me' if re.search(r'(?:Self inflict|user inflicts|BURN itself|Self-inflict|the user is|user also|itself)', desc[max(0, m.start() - 40):m.start() + 10], re.I) else 'foe'
        if re.search(r'Self inflict|BURN itself', desc[max(0, m.start() - 30):m.start() + 12]): who = 'me'
        if re.search(r'either|random status', desc) and sts: continue
        if (who, STATUS[w][0]) not in [(x[0], x[1]) for x in sts]: sts.append((who, STATUS[w][0], r, STATUS[w][1]))
    # ---- debuffs
    debuffs = []
    for m in re.finditer(r"(?:reduc\w+|lower\w*|steal\w*|burn\w*|[Dd]rains?) (?:the target's |their |its |the enemy's |the )?(?:from target )?(?:BASE )?(ATK|DEF|SPE_DEF|SPEED|PP)\b(?: by (\d+))?", desc, re.I):
        st = m.group(1).upper()
        debuffs.append((st, m.group(2)))
    # ---- self effects
    buffs = []   # (stat, k, target) target 'me'|'allies'
    for m in re.finditer(r"(?:[Ii]ncrease|[Bb]uff|[Gg]ain|[Rr]aise|[Gg]rant|[Gg]ives?|[Bb]oosts?|[Rr]eceive|[Rr]estore)[^.]*", desc):
        seg = m.group(0)
        for sm in re.finditer(r'(?:\[([^\]]*)\]|(\d+))\s*(?:%\s*)?(?:BASE )?(ATK|DEF|SPE_DEF|SPEED|AP|PP|HP|SHIELD)\b', seg):
            nums = sm.group(1) or sm.group(2)
            val = arrays('[' + nums + ']', stars)[0][2] if sm.group(1) else float(nums)
            stat = sm.group(3)
            tgt = 'allies' if re.search(r'allied|allies|ally', seg[:sm.start()]) and not re.search(r"user's and", seg[:sm.start()]) else 'me'
            isp = '%' in seg[sm.start():sm.end()]
            buffs.append((stat, val, tgt, isp))
    for m in re.finditer(r"((?:BASE )?(?:ATK|DEF|SPE_DEF|SPEED|AP)(?:(?:, | and | and its )(?:BASE )?(?:ATK|DEF|SPE_DEF|SPEED|AP))*) by (\[[^\]]*\]|\d+)(%?)", desc):
        pre = desc[:m.start()]
        if re.search(r'reduc|lower|steal|drain', pre[-25:], re.I): continue
        val = arrays(m.group(2), stars)[0][2] if m.group(2).startswith('[') else float(m.group(2))
        tgt = 'allies' if re.search(r'allies|allied|ally', pre[-45:]) and not re.search(r"user's and", pre[-45:]) else 'me'
        for st_ in re.findall(r'ATK|DEF|SPE_DEF|SPEED|AP', m.group(1).replace('BASE ', '')):
            if not any(b[0] == st_ and b[2] == tgt for b in buffs): buffs.append((st_, val, tgt, bool(m.group(3))))
    shield = None; heal = None; healtgt = 'me'
    for b in buffs:
        if b[0] == 'SHIELD' and shield is None: shield = D(b[1])
        if b[0] == 'HP' and heal is None:
            seg = desc
            heal = D(b[1])
    mh = re.search(r'[Hh]eal\w*[^.]*?\[([^\]]*)\]\s*HP|heals? (?:for )?\[([^\]]*)\]\s*HP|\[([^\]]*)\]\s*(?:\+ \[[^\]]*\] )?HP', desc)
    if heal is None and mh:
        g = [x for x in mh.groups() if x]; heal = D(arrays('[' + g[0] + ']', stars)[0][2])
    # drain
    drain = None
    if re.search(r'heal(?:ing)? (?:for )?(?:the )?(?:damage dealt|same)|heals? for 200% of the damage|healing for the damage', desc, re.I) or re.search(r'steal', desc) and 'HP' in desc: drain = 1.0
    if re.search(r'heal for 200% of the damage', desc): drain = 1.0
    if re.search(r'heals? 10% of its max HP', desc): drain = .5
    if re.search(r'heals? half', desc): drain = .5
    protect = bool(re.search(r'\bPROTECT\b(?! ADJACENT enemy)', desc)) and not re.search(r'SAFEGUARD', desc)
    resurrect = 'RESURRECTION' in desc
    selfhurt = None
    mself = re.search(r"(?:Damages user by the same amount|user (?:hurts itself|loses) (?:for )?\[?([^\]%]*)\]?\s*(?:PHYSICAL|% of its max HP))", desc)
    if re.search(r'Damages user by the same amount', desc): selfhurt = ('same',)
    elif re.search(r'user loses (\d+)% of its max HP', desc): selfhurt = ('pct', int(re.search(r'user loses (\d+)% of its max HP', desc).group(1)))
    elif re.search(r'hurts itself for \[', desc): selfhurt = ('amt', D(arrays(re.search(r'hurts itself for \[[^\]]*\]', desc).group(0), stars)[0][2]))
    delay = None
    md = re.search(r'After (\d) seconds', desc)
    if md and has_dmg: delay = 1 if int(md.group(1)) <= 1 else 2
    cure = bool(re.search(r'[Cc]ures? negative|cure', desc))
    ko_charge = bool(re.search(r'KO\'d.{0,40}max PP|back to max PP|KO.{0,30}PP', desc))
    return compose(ab, desc, stars, c, kind, has_dmg, dmg, dyn, mult_hits, mode, cond, splash, sts, debuffs, buffs, shield, heal, drain, protect, selfhurt, delay, cure, ko_charge, area)

def compose(ab, desc, stars, c, kind, has_dmg, dmg, dyn, hits, mode, cond, splash, sts, debuffs, buffs, shield, heal, drain, protect, selfhurt, delay, cure, ko_charge, area):
    P = []   # parts
    role = 'Striker'
    if dyn or (has_dmg and dmg):
        if delay: P.append(('delay', delay, dmg or 3))
        elif drain and not dyn: P.append(('drain', dmg, drain))
        elif dyn: P.append(('dyn', dyn[0], dyn[1], kind))
        else:
            for _ in range(hits): P.append((kind, dmg, splash and hits == 1 and not drain and not delay))
            if cond: P[-1] = P[-1] + (cond,) if False else P[-1]
        if hits > 1: role = 'MultiHit'
        if drain: role = 'Drain'
    for who, n, r, w in sts: P.append(('st', who, n, r, w))
    sh = None
    for stat, v, tgt, isp in buffs:
        pass
    # buffs / debuffs
    done = set()
    for stat, v, tgt, isp in buffs:
        if stat in ('SHIELD', 'HP'): continue
        if stat == 'PP':
            if tgt == 'allies': P.append(('carry', 'charge', 1))
            else: P.append(('gcharge', 1))
            continue
        key = STATNAME[stat]
        if isp: k = max(1, round(v / 100 * {'atk': c.atkc, 'def': max(1, round(c.defn / 7)), 'sdef': max(1, round(c.sdef / 7)), 'spd': max(1, round(c.spd / 7)), 'ap': 2}[key]))
        elif key == 'ap': k = max(1, round(v / 25)) if v >= 13 else max(1, round(v / 10))
        elif key == 'atk': k = AT(v)
        elif key == 'spd': k = SP(v)
        else: k = max(1, round(v / 7))
        k = min(k, 4)
        if (key, tgt) in done: continue
        done.add((key, tgt))
        if tgt == 'allies':
            if key in ('atk', 'def', 'spd'): P.append(('carry', key, max(1, (k + 1) // 2)))
            elif key == 'sdef': P.append(('carry', 'def', max(1, (k + 1) // 2)))
            else: P.append(('carry', 'charge', 1))
        else: P.append(('buff', key, k))
    # target debuffs
    for st, amt in debuffs:
        key = STATNAME.get(st)
        if key == 'pp': P.append(('foecharge', -1)); continue
        if key in ('def', 'sdef', 'atk', 'spd'): P.append(('tmp', key, 1 if not amt or int(amt) < 8 else 2, 2))
    if shield: P.append(('shield', shield))
    if heal and not drain:
        P.append(('heal', heal))
    if protect:
        P.append(('protect',))
        if not any(p[0] in ('S','T','P','shield','drain','dyn','delay') for p in P): P.append(('shield', 2))
    if cure: P.append(('cure',))
    if ko_charge: P.append(('kocharge', 1))
    if selfhurt: P.append(('selfhurt',) + selfhurt)
    if ('RESURRECTION' in desc): P.append(('carry', 'revive', 1))
    # nothing recognised -> modest generic power so the card is playable; flagged for review
    flagged = False
    if not P:
        flagged = True
        P.append(('S', max(1, D(30)), False))
    if role == 'Striker' and not any(p[0] in ('S', 'T', 'P', 'dyn', 'drain', 'delay') for p in P):
        role = 'Control' if any(p[0] in ('st', 'tmp', 'foecharge') for p in P) else ('Support' if any(p[0] in ('carry', 'heal', 'shield') for p in P) else 'Tank')
        if any(p[0] == 'shield' or p[0] == 'protect' or p[0] == 'buff' for p in P) and role == 'Support': role = 'Tank'
    elif role == 'Striker' and any(p[0] == 'st' for p in P): role = 'Control'
    apmode = mode if any(p[0] in ('S', 'T', 'P', 'drain') for p in P) else 'first'
    if mode == 'each_half' and hits >= 3: apmode = 'each_half'
    elif hits == 2: apmode = 'half' if False else 'first'
    P = [(p + (cond,) if (cond and p[0] in ('S', 'T', 'P') and i == 0) else p) for i, p in enumerate(P)]
    return role, P, apmode, flagged

# ---------------- render parts -> text and ops ----------------
TXT = {'para': 'PARALYZE', 'burn': 'BURN', 'poison': 'POISON', 'sleep': 'SLEEP', 'freeze': 'FREEZE', 'confuse': 'CONFUSE', 'charm': 'CHARM', 'wound': 'WOUND', 'flinch': 'FLINCH', 'armor': 'ARMOR BREAK', 'fatigue': 'FATIGUE'}
KINDT = {'S': 'SPECIAL', 'T': 'TRUE', 'P': 'PHYSICAL'}

def render(parts, apmode, c):
    tag = {'first': '✦', 'half': '✦/2 ', 'each_half': '✦/2 ', 'none': ''}[apmode]
    txt = []; ap_used = False
    dm = [p for p in parts if p[0] in ('S', 'T', 'P')]
    i = 0
    def t_(x):
        nonlocal ap_used
        if apmode != 'none' and not ap_used: ap_used = True; return tag + str(x)
        return str(x)
    first_dmg = True
    consumed = set()
    # damage sentence
    if dm:
        hits = len(dm); p0 = dm[0]; k = p0[0]
        base = ('Deal' if hits == 1 else f'Hit {hits} times for')
        cond = p0[3] if len(p0) > 3 else None
        s = f"{base} {t_(p0[1])} {KINDT[k]}" + (' each' if hits > 1 else '')
        if apmode == 'each_half' and hits > 1: pass
        if cond: s += {'shield': ', doubled if the target has SHIELD', 'neg': ', doubled if the target has a negative status', 'sdef0': ', doubled if the target has 0 SP.DEF', 'low': ', doubled if you are below half HP', 'poison': ', doubled if the target is POISONED'}[cond[0]]
        txt.append(s)
    for p in parts:
        k = p[0]
        if k == 'dyn':
            if p[1] == 'top3': txt.append(f"Deal AP ({tag}) + {'double' if p[2] == 2 else str(p[2]) + 'x'} the sum of your 3 highest synergy counts {KINDT[p[3]]}")
            elif p[1] == 'tgtmax' and p[2] >= 100: txt.append(f"Deal {KINDT[p[3]]} damage equal to the target's max HP")
            else: txt.append(f"Deal 1 {KINDT[p[3]]}")
        elif k == 'drain': txt.append(f"Deal {t_(p[1])} SPECIAL and heal " + ("that much" if p[2] >= 1 else "half the damage dealt"))
        elif k == 'delay': txt.append(f"After {'your next turn' if p[1] == 1 else 'your 2nd turn from now'}, the opposing Pokemon takes {t_(p[2])} SPECIAL")
        elif k == 'st':
            who, n, r, w = p[1:5]
            if n == 'locked': txt.append("LOCK the target (it cannot Fly Away, dodge or evade on its next hit)"); continue
            txt.append((f"inflict {w} ({r} turn{'s' if r > 1 else ''})" if who == 'foe' else f"you are {w}{'D' if not w.endswith('E') else 'D'} ({r} turn{'s' if r > 1 else ''})") if False else
                       (f"{w} the target ({r} turn{'s' if r > 1 else ''})" if who == 'foe' else f"{w} yourself ({r} turn{'s' if r > 1 else ''})"))
        elif k == 'buff': txt.append(f"gain {p[2]:+d} {STATTXT[p[1]]}" if p[2] > 0 else f"lose {-p[2]} {STATTXT[p[1]]}")
        elif k == 'tmp': txt.append(f"give the target -{p[2]} {STATTXT[p[1]]} ({p[3]} turns)")
        elif k == 'shield':
            cnd = p[2] if len(p) > 2 else None
            if cnd == 'burned': txt.append(f"gain SHIELD equal to the charge burned")
            else: txt.append(f"gain {t_(p[1])} SHIELD" + (' if the target is PARALYZED' if cnd == 'para' else ''))
        elif k == 'koif':
            txt.append("KO the target if it is " + ' or '.join({'sleep': 'ASLEEP', 'freeze': 'FROZEN'}[n] for n in p[1]) + (f" (not if it is {p[2].title()} type)" if p[2] else ''))
        elif k == 'heal': txt.append(f"heal {t_(p[1])}")
        elif k == 'protect': txt.append("PROTECT (ignore all damage until your next turn)")
        elif k == 'cure': txt.append("cure your negative statuses")
        elif k == 'carry' and p[1] == 'revive': txt.append("your next Pokemon is revived once at half HP when it is first KO'd")
        elif k == 'carry': txt.append(f"your next Pokemon enters with +{p[2]} {'charge' if p[1] == 'charge' else 'SHIELD' if p[1] == 'shield' else STATTXT.get(p[1], p[1])}")
        elif k == 'gcharge': txt.append(f"gain {p[1]} charge")
        elif k == 'mhp': txt.append(f"gain +{p[1]} max HP")
        elif k == 'foecharge': txt.append(f"burn {-p[1]} charge from the target")
        elif k == 'kocharge': txt.append("if it KOs the target, gain 1 charge")
        elif k == 'selfhurt':
            txt.append({'same': 'you take the same damage', 'pct': ('you lose half your max HP' if p[2] == 50 else f"you lose {p[2]}% of your max HP"), 'amt': f"you take {p[2]} TRUE"}[p[1]])
    out = []
    for i, s in enumerate(txt):
        s = s[0].upper() + s[1:] if i == 0 else s
        out.append(s)
    text = ', '.join(out[:1]) if len(out) == 1 else out[0] + (', ' if len(out) > 1 else '') + ', '.join(out[1:])
    # nicer joins: " and " before last
    if len(out) > 2: text = ', '.join(out[:-1]) + ' and ' + out[-1]
    elif len(out) == 2: text = out[0] + ' and ' + out[1]
    text += '.'
    if any(p[0] in ('S', 'T', 'P') and len(p) > 2 and p[2] for p in parts): text += ' SPLASH.'
    return text

def opsfn(parts, c):
    def f(v, raw, me, foe):
        ops = []
        for p in parts:
            k = p[0]
            if k in ('S', 'T', 'P'):
                x = p[1]
                cond = p[3] if len(p) > 3 else None
                if cond:
                    ok = {'shield': foe.shield > 0, 'neg': foe.neg(), 'sdef0': foe.eff('sdef') == 0, 'low': me.hp * 2 < me.maxhp, 'poison': foe.st['poison'] > 0}[cond[0]]
                    if ok: x *= 2
                ops.append((k, x, p[2]) if k == 'S' else (k, x))
            elif k == 'dyn':
                if p[1] == 'tgtmax': x = max(1, round(foe.maxhp * p[2] / 100)) if p[2] >= 100 else 1
                elif p[1] == 'top3': x = max(1, p[2] * (sum(sorted(me.side.cnt.values(), reverse=True)[:3]) if hasattr(me.side, 'cnt') else 10))   # stub (pricing) assumes a 4/3/3 lineup   # double your 3 highest synergy counts
                else: x = 1
                ops.append(({'S': 'S', 'T': 'T', 'P': 'P'}[p[3]], x, False) if p[3] == 'S' else (p[3], x))
            elif k == 'drain': ops.append(('drain', p[1], p[2]))
            elif k == 'delay': ops.append(('delay', p[1], p[2]))
            elif k == 'st': ops.append(('st', p[1], p[2], p[3]))
            elif k == 'buff': ops.append(('buff', p[1], p[2]))
            elif k == 'tmp': ops.append(('tmp', 'foe', p[1], -p[2], p[3]))
            elif k == 'shield':
                cnd = p[2] if len(p) > 2 else None
                if cnd == 'para':
                    if foe.st['para'] > 0: ops.append(('shield', p[1]))
                elif cnd == 'burned': pass          # handled with the foecharge part below
                else: ops.append(('shield', p[1]))
            elif k == 'koif': ops.append(('koif', p[1], p[2]))
            elif k == 'heal': ops.append(('heal', p[1]))
            elif k == 'protect': ops.append(('protect',))
            elif k == 'cure': ops.append(('cure',))
            elif k == 'carry': ops.append(('carry', p[1], p[2]))
            elif k == 'gcharge': ops.append(('gcharge', p[1]))
            elif k == 'mhp': ops.append(('mhp', p[1]))
            elif k == 'foecharge':
                if any(q[0] == 'shield' and len(q) > 2 and q[2] == 'burned' for q in parts):
                    _n = min(-p[1], max(0, getattr(foe, 'charge', 0)))
                    if _n > 0: ops.append(('shield', _n))
                ops.append(('foecharge', p[1]))
            elif k == 'kocharge': ops.append(('kocharge', p[1]))
            elif k == 'selfhurt':
                x = sum(o[1] for o in ops if o[0] in ('S', 'T', 'P')) if p[1] == 'same' else round(me.maxhp * p[2] / 100) if p[1] == 'pct' else p[2]
                ops.append(('selfhurt', max(1, x)))
        return ops
    return f

def _patch_hornleech(P, st, c): return [('drain', p[1], .5) if p[0] == 'S' else p for p in P]
def _patch_koif(names, imm):
    return lambda P, st, c: P + [('koif', names, imm)]
def _patch_psyshock(P, st, c):
    n = 2 if st >= 3 else 1
    return [p for p in P if p[0] != 'foecharge'] + [('foecharge', -n), ('shield', n, 'burned')]
def _patch_zingzap(P, st, c): return [(p + ('para',)) if p[0] == 'shield' else p for p in P]
def _patch_venoshock(P, st, c): return [(p[:3] + (('poison', 2),)) if p[0] == 'S' else p for p in P]
PATCH = {
 'HORN_LEECH': _patch_hornleech,
 'HEAD_SMASH': _patch_koif(('sleep', 'freeze'), None),
 'SHEER_COLD': _patch_koif(('freeze',), 'ICE'),
 'VENOSHOCK': _patch_venoshock,
 'PSYSHOCK': _patch_psyshock,
 'ZING_ZAP': _patch_zingzap,
}
def make(ab, stars, c):
    role, parts, apmode, flagged = _make(ab, stars, c)
    if ab in PATCH:
        parts = PATCH[ab](parts, stars, c)
        if ab == 'HORN_LEECH': role = 'Drain'
    return role, parts, apmode, flagged

def build(ab, stars, c):
    role, parts, apmode, flagged = make(ab, stars, c)

    text = render(parts, apmode, c)
    return role, text, opsfn(parts, c), apmode, flagged, parts


STW = {'locked': 1.0, 'para': 1.6, 'burn': 1.0, 'poison': 1.0, 'sleep': 3.0, 'freeze': 2.6, 'confuse': 1.5, 'charm': 1.5, 'wound': 1.0, 'flinch': 1.8, 'armor': 1.6, 'fatigue': 1.4}
BW = {'atk': 2.2, 'spd': 2.4, 'def': 1.6, 'sdef': 1.6, 'ap': 2.0}
def value_of(ops):
    v = 0.0
    for o in ops:
        k = o[0]
        if k == 'S': v += o[1] * (1.25 if len(o) > 2 and o[2] else 1.0)
        elif k == 'Sp': v += o[1] * 1.2
        elif k == 'T': v += o[1] * 1.15
        elif k == 'P': v += o[1] * 0.9
        elif k == 'drain': v += o[1] * (1 + 0.8 * o[2])
        elif k == 'delay': v += o[2] * 0.85
        elif k in ('shield', 'heal'): v += o[1] * 0.8
        elif k == 'st': v += STW.get(o[2], 1.2) * o[3] * (1 if o[1] == 'foe' else -1)
        elif k == 'buff': v += BW.get(o[1], 1.5) * o[2]
        elif k == 'tmp': v += 0.8 * -o[3] * min(o[4], 3)
        elif k == 'carry': v += 1.4 * o[2]
        elif k == 'protect': v += 3.0
        elif k == 'foecharge': v += 1.5
        elif k == 'gcharge': v += 1.5 * o[1]
        elif k == 'mhp': v += 0.8 * o[1]
        elif k == 'selfhurt': v -= 0.6 * o[1]
        elif k == 'cure': v += 1.0
        elif k == 'kocharge': v += 0.8
        elif k == 'koif': v += 1.2
        elif k in ('execute', 'koheal', 'atk', 'reflect', 'spiky', 'nextatk'): v += 1.5
    return v
