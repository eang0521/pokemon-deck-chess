/* PAC duel engine — faithful JS port of the Python simulator (engine.py, duel.py, itemfx.py, genpower.opsfn). */
(function (root) {
'use strict';
// card/item data comes from js/data.js (window.PAC_DATA); Node and Workers load it onto the global first
const DATA = (typeof window !== 'undefined' ? window : globalThis).PAC_DATA;

// ---------- helpers ----------
function pyround(x) { const f = Math.floor(x), d = x - f; if (d < 0.5) return f; if (d > 0.5) return f + 1; return f % 2 === 0 ? f : f + 1; }
const trunc = Math.trunc;
const D = x => Math.max(1, trunc(x / 10 + 0.5));
const PA = (p, base) => Math.max(1, trunc(p / 100 * base / 6 + 0.5));
const S = x => Math.min(3, Math.max(1, trunc(x / 3 + 0.5)));
const AT = x => Math.max(1, trunc(x / 5 + 0.5));
const SP = x => Math.max(1, trunc(x / 7 + 0.5));
const ceil = Math.ceil;
function counter(init) {
  return new Proxy(Object.assign({}, init || {}), { get(t, k) { if (typeof k === 'symbol') return t[k]; return (k in t) ? t[k] : 0; } });
}
const empty = o => Object.keys(o).length === 0;
const NEG = ['burn', 'poison', 'para', 'flinch', 'sleep', 'freeze', 'confuse', 'charm', 'wound', 'armor', 'fatigue', 'locked'];
const STN = { para: 'PARALYZED', armor: 'ARMOR BROKEN', fatigue: 'FATIGUED', flinch: 'FLINCHED', confuse: 'CONFUSED', charm: 'CHARMED', wound: 'WOUNDED', burn: 'BURNED', sleep: 'ASLEEP', freeze: 'FROZEN', locked: 'LOCKED' };

// ---------- RNG ----------
function makeRng(seed) {
  let a = (seed >>> 0) || 1;
  const r = {
    random() { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; },
    int(n) { return Math.floor(r.random() * n); },
    choice(arr) { return arr[Math.floor(r.random() * arr.length)]; },
    shuffle(arr) { for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(r.random() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; },
    sample(arr, k) { const c = arr.slice(); r.shuffle(c); return c.slice(0, k); },
    getState() { return a; }, setState(v) { a = v | 0; },
  };
  return r;
}

// ---------- synergy thresholds ----------
const SYN_TH = DATA.syn_th;
const level_of = (t, n) => (SYN_TH[t] || [2, 3, 4]).filter(x => n >= x).length;
const ITEMS = DATA.items;
const APM = Object.assign({}, DATA.apm);
const HALF_ONLY = null;

// ---------- Core powers ----------
const s_ = (x, sp) => ['S', x, !!sp];
const rep = (n, f) => { const o = []; for (let i = 0; i < n; i++) o.push(f(i)); return o; };
// Tri Attack: status by the user's highest of FIRE / ELECTRIC / ICE synergy (ties: Fire > Electric > Ice; none -> burn)
function triStatus(me) {
  const cn = me.side.cnt || {}; const f = cn.FIRE || 0, e = cn.ELECTRIC || 0, i = cn.ICE || 0;
  if (i > f && i > e) return ['st', 'foe', 'freeze', 1];
  if (e > f && e >= i) return ['st', 'foe', 'para', 1];
  return ['st', 'foe', 'burn', 2];
}
const PW = {
  ACCELEROCK: (v, c, me, foe) => [s_(PA(v[0], c.atk)), ['buff', 'spd', 1], ['buff', 'def', -1]],
  ACID_ARMOR: (v, c, me, foe) => [['buff', 'def', AT(v[0])], ['thorns', 2]],
  AGILITY: (v, c, me, foe) => [['buff', 'spd', SP(v[0])]],
  AIR_SLASH: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'flinch', 1]],
  AQUA_STEP: (v, c, me, foe) => [['buff', 'spd', SP(v[1])], s_(D(v[0]))],
  AQUA_TAIL: (v, c, me, foe) => [s_(D(v[0])), ['shield', D(v[1])]],
  BITE: (v, c, me, foe) => [['drain', PA(v[0], c.atk), .5], ['st', 'foe', 'flinch', 1]],
  BLAST_BURN: (v, c, me, foe) => [s_(D(v[0]), true)],
  BLAZE_KICK: (v, c, me, foe) => [s_(foe.st.burn ? ceil(D(v[0]) * 1.5) : D(v[0])), ['st', 'foe', 'burn', 3]],
  BLOOD_MOON: (v, c, me, foe) => [s_(PA(v[0], c.atk)), ['st', 'foe', 'wound', 2]],
  BUG_BUZZ: (v, c, me, foe) => [s_(D(v[0]) * (foe.st.para ? 2 : 1))],
  BULLDOZE: (v, c, me, foe) => [s_(D(v[0] * 1.4), true), ['tmp', 'foe', 'spd', -1, 2]],
  COLUMN_CRUSH: (v, c, me, foe) => [['shield', D(v[0])], s_(me.shield + D(v[0]))],
  CRABHAMMER: (v, c, me, foe) => [s_(D(v[0])), ['execute', 4]],
  CRUNCH: (v, c, me, foe) => [s_(D(v[0])), ['koheal', .5]],
  DARKEST_LARIAT: (v, c, me, foe) => rep(Math.max(2, pyround(c.spd / 25)), () => s_(PA(v[0], c.atk))).concat([['st', 'foe', 'flinch', 1]]),
  DARK_HARVEST: (v, c, me, foe) => [['drain', D(v[0] * 3), .3], ['st', 'me', 'flinch', 1]],
  DOUBLE_SHOCK: (v, c, me, foe) => [s_(D(v[0])), ['st', 'me', 'para', 1]],
  DRAGON_BREATH: (v, c, me, foe) => [s_(D(v[0]), true)],
  DRAGON_TAIL: (v, c, me, foe) => [s_(D(v[0])), ['buff', 'def', AT(v[1])], ['buff', 'sdef', AT(v[1])]],
  DRUM_BEATING: (v, c, me, foe) => [[['shield', D(v[0] * .8)]], [s_(D(v[1] * .8))], [['carry', 'spd', SP(v[2])]]][me.cycle % 3],
  ENTANGLING_THREAD: (v, c, me, foe) => [s_(D(v[0]), true), ['st', 'foe', 'para', 2]],
  FAIRY_WIND: (v, c, me, foe) => [['carry', 'charge', 1 + (v[0] >= 10 ? 1 : 0)]],
  FIRESTARTER: (v, c, me, foe) => [['buff', 'spd', SP(v[0])], s_(D(v[1] * .8))],
  FLAMETHROWER: (v, c, me, foe) => [s_(D(v[0]), true), ['st', 'foe', 'burn', 3]],
  FLOWER_TRICK: (v, c, me, foe) => [['delay', 1, D(v[0])]],
  FURY_SWIPES: (v, c, me, foe) => [['atk', (me.stars || 1) >= 4 ? 5 : 3]],
  FUTURE_SIGHT: (v, c, me, foe) => [['delay', 2, D(v[1] * 3)]],
  GEAR_GRIND: (v, c, me, foe) => [s_(PA(v[0], me.eff('spd') * 7)), s_(PA(v[0], me.eff('spd') * 7))],
  GIGATON_HAMMER: (v, c, me, foe) => [s_(D(v[0])), ['st', 'me', 'fatigue', 2]],
  GLAIVE_RUSH: (v, c, me, foe) => [['st', 'foe', 'armor', 2], ['st', 'me', 'armor', 2], s_(D(v[0]))],
  GROWL: (v, c, me, foe) => [['st', 'foe', 'flinch', 1], ['tmp', 'foe', 'atk', -AT(v[0]), 2]],
  GUILLOTINE: (v, c, me, foe) => [s_(PA(v[0], c.atk)), ['kocharge', 1]],
  HEADBUTT: (v, c, me, foe) => [s_(D(v[0]) * (foe.shield > 0 ? 2 : 1)), ['st', 'foe', 'flinch', 1]],
  HEAVY_SLAM: (v, c, me, foe) => [s_(D(v[0]) + Math.max(0, Math.floor((me.maxhp - foe.maxhp) / 3)), true)],
  HEX: (v, c, me, foe) => [s_(D(v[0]) * (foe.neg() ? 2 : 1))],
  HORN_ATTACK: (v, c, me, foe) => [s_(PA(v[0], c.atk)), ['st', 'foe', 'armor', 1]],
  HORN_DRILL: (v, c, me, foe) => [s_(me.eff('atk') > foe.eff('atk') ? ceil(PA(v[0], c.atk) * 1.5) : PA(v[0], c.atk))],
  HYDRO_PUMP: (v, c, me, foe) => [s_(D(v[0]), true)],
  ICE_BALL: (v, c, me, foe) => [['buff', 'sdef', 2], s_(D(v[0]) + PA(v[1], c.sdef))],
  ICICLE_CRASH: (v, c, me, foe) => [s_(D(v[0]), true)],
  ICICLE_MISSILE: (v, c, me, foe) => rep(trunc(v[0]), () => s_(D(v[1] * 1.5))).concat([['st', 'foe', 'freeze', 1]]),
  ICY_WIND: (v, c, me, foe) => [s_(D(v[0]), true), ['tmp', 'foe', 'spd', -SP(v[1]), 2]],
  KING_SHIELD: (v, c, me, foe) => [['protect'], ['shield', D(v[0] * 2)]],
  KOWTOW_CLEAVE: (v, c, me, foe) => [s_(ceil(PA(150, c.atk) * 2)), ['T', me.side.fallen * Math.max(1, pyround(PA(150, c.atk) * v[0] / 100))]],
  LEAF_BLADE: (v, c, me, foe) => [['T', ceil(PA(v[0], c.atk) * 2)]],
  LEECH_LIFE: (v, c, me, foe) => [['drain', D(v[0]), 1.0]],
  LICK: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'para', 1], ['st', 'foe', 'confuse', 1]],
  MAGICAL_LEAF: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'armor', 1]],
  MAGIC_POWDER: (v, c, me, foe) => [['shield', D(v[0])], ['st', 'foe', 'flinch', S(v[1])]],
  MAGNET_BOMB: (v, c, me, foe) => [s_(D(v[0] * 1.5), true), ['st', 'foe', 'locked', 1]],
  MANTIS_BLADES: (v, c, me, foe) => [['P', D(v[0])], s_(D(v[0])), ['T', D(v[0])]],
  METEOR_MASH: (v, c, me, foe) => rep(me.lv('PSYCHIC') ? 4 : 3, () => s_(PA(v[0], c.atk))).concat([['buff', 'atk', 1]]),
  MYSTICAL_FIRE: (v, c, me, foe) => [s_(D(v[0])), ['ap_foe', -1]],
  NIGHTMARE: (v, c, me, foe) => [['st', 'foe', 'fatigue', S(v[0])]].concat(foe.neg() ? [s_(D(v[1]))] : []),
  NUZZLE: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'para', S(v[1])]],
  PECK: (v, c, me, foe) => [s_(D(v[0]))],
  PETAL_DANCE: (v, c, me, foe) => rep(Math.max(2, pyround(v[0] / 2)), () => s_(D(v[1]))),
  PLAY_ROUGH: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'charm', 2]],
  PSYCHIC: (v, c, me, foe) => [s_(D(v[0] * 1.5), true), ['foecharge', -1]],
  PSYCHO_CUT: (v, c, me, foe) => rep(3, () => s_(ceil(D(v[0]) * 1.5))),
  RAPID_SPIN: (v, c, me, foe) => [s_(D(v[0])), ['buff', 'def', Math.max(1, pyround(PA(v[1], c.atk)))], ['buff', 'sdef', Math.max(1, pyround(PA(v[1], c.atk)))]],
  REFLECT: (v, c, me, foe) => [['reflect', S(v[0]), 50]],
  RETALIATE: (v, c, me, foe) => rep(1 + me.side.fallen, () => s_(PA(v[0], c.atk))),
  ROCK_ARTILLERY: (v, c, me, foe) => rep(Math.max(2, pyround(v[0] / 5)), () => s_(D(v[1] * 1.5))),
  ROCK_SLIDE: (v, c, me, foe) => [s_(D(v[0]) * ((foe.lv('FLYING') || foe.types.has('FLYING')) ? 2 : 1))],
  SALT_CURE: (v, c, me, foe) => [['shield', D(v[0])], ['cure']].concat(['WATER', 'STEEL', 'GHOST'].some(t => foe.types.has(t)) ? [['st', 'foe', 'burn', 3]] : []),
  SHADOW_BALL: (v, c, me, foe) => [s_(D(v[0])), ['tmp', 'foe', 'sdef', -1, 99]],
  SHOCKWAVE: (v, c, me, foe) => [s_(D(v[0]), true)],
  SILVER_WIND: (v, c, me, foe) => [s_(D(v[0])), ['buff', 'atk', 1], ['buff', 'spd', 1], ['buff', 'def', 1], ['buff', 'sdef', 1]],
  SING: (v, c, me, foe) => [['st', 'foe', 'sleep', S(v[1])]],
  SLASH: (v, c, me, foe) => [s_(ceil(D(v[0]) * 2))],
  SNIPE_SHOT: (v, c, me, foe) => [s_(D(v[0]), true)],
  SOAK: (v, c, me, foe) => [s_(D(v[0])), ['carry', 'charge', 1]],
  SOFT_BOILED: (v, c, me, foe) => [['cure'], ['shield', D(v[0])], ['carry', 'shield', ceil(D(v[0]) / 2)]],
  SPIKY_SHIELD: (v, c, me, foe) => [['spiky', S(v[0]), PA(v[1], c.defn)]],
  STEAMROLLER: (v, c, me, foe) => [s_(PA(v[0] * .75, c.spd))].concat(me.eff('spd') > foe.eff('spd') ? [['st', 'foe', 'flinch', 1]] : []),
  STORED_POWER: (v, c, me, foe) => [s_(D(v[0]) + me.boosts)],
  STRING_SHOT: (v, c, me, foe) => [s_(D(v[0])), ['st', 'foe', 'para', 2]],
  TELEPORT: (v, c, me, foe) => [['nextatk', D(v[0])]],
  TERRAIN_PULSE: (v, c, me, foe) => [['heal', Math.max(1, pyround(v[0] / 100 * c.hpc))]].concat(me.lv('GRASS') ? [['buff', 'def', 1]] : [], me.lv('ELECTRIC') ? [['buff', 'spd', 2]] : [], me.lv('PSYCHIC') ? [['buff', 'ap', 1]] : []),
  THRASH: (v, c, me, foe) => [['buff', 'atk', Math.max(1, pyround(v[0] / 100 * c.atkc))], ['st', 'me', 'confuse', 1]],
  THUNDER_SHOCK: (v, c, me, foe) => [s_(D(v[0]))],
  TICKLE: (v, c, me, foe) => [['tmp', 'foe', 'atk', -1, 2], ['tmp', 'foe', 'def', -1, 2]],
  TORCH_SONG: (v, c, me, foe) => rep(4, () => s_(PA(50, c.atk))).concat([['st', 'foe', 'burn', 3], ['buff', 'ap', trunc(v[2])]]),
  TRANSE: (v, c, me, foe) => [['heal', Math.max(1, pyround(.5 * me.maxhp))]],
  TRI_ATTACK: (v, c, me, foe) => [s_(D(v[0] * .8)), triStatus(me)],
  TROP_KICK: (v, c, me, foe) => [s_(D(v[0])), ['tmp', 'foe', 'atk', -AT(v[1]), 2]],
  TWISTER: (v, c, me, foe) => [s_(D(v[0]), true)],
  UPROAR: (v, c, me, foe) => [s_(D(v[0])), ['delay', 2, D(v[0]), 1], ['delay', 3, D(v[0]), 1]],
  VOLT_SWITCH: (v, c, me, foe) => [s_(D(v[0]), true)],
  WAVE_SPLASH: (v, c, me, foe) => [['shield', Math.max(1, pyround(v[0] / 100 * c.hpc))], s_(Math.max(1, pyround(v[0] / 100 * c.hpc)))],
  WHEEL_OF_FIRE: (v, c, me, foe) => [s_(D(v[0])), s_(D(v[0]))],
  WHIRLPOOL: (v, c, me, foe) => rep(4, () => s_(PA(v[0], c.atk))),
  WISH: (v, c, me, foe) => [['shield', D(v[0])], ['protect']],
};

// generated powers (genpower.opsfn)
function opsfn(parts) {
  return function (v, raw, me, foe) {
    const ops = [];
    for (const p of parts) {
      const k = p[0];
      if (k === 'S' || k === 'T' || k === 'P') {
        let x = p[1]; const cond = p.length > 3 ? p[3] : null;
        if (cond) {
          const ok = { shield: foe.shield > 0, neg: foe.neg(), sdef0: foe.eff('sdef') === 0, low: me.hp * 2 < me.maxhp, poison: foe.st.poison > 0 }[cond[0]];
          if (ok) x *= 2;
        }
        ops.push(k === 'S' ? [k, x, p[2]] : [k, x]);
      } else if (k === 'dyn') {
        const x = p[1] === 'tgtmax' ? (p[2] >= 100 ? Math.max(1, pyround(foe.maxhp * p[2] / 100)) : 1)
          : p[1] === 'top3' ? Math.max(1, p[2] * Object.values(me.side.cnt).sort((a, b) => b - a).slice(0, 3).reduce((a, b) => a + b, 0)) : 1;
        ops.push(p[3] === 'S' ? ['S', x, false] : [p[3], x]);
      } else if (k === 'drain') ops.push(['drain', p[1], p[2]]);
      else if (k === 'delay') ops.push(['delay', p[1], p[2]]);
      else if (k === 'st') ops.push(['st', p[1], p[2], p[3]]);
      else if (k === 'buff') ops.push(['buff', p[1], p[2]]);
      else if (k === 'tmp') ops.push(['tmp', 'foe', p[1], -p[2], p[3]]);
      else if (k === 'shield') {
        const cnd = p.length > 2 ? p[2] : null;
        if (cnd === 'para') { if (foe.st.para > 0) ops.push(['shield', p[1]]); }
        else if (cnd === 'burned') { /* handled with the foecharge part */ }
        else ops.push(['shield', p[1]]);
      } else if (k === 'koif') ops.push(['koif', p[1], p[2]]);
      else if (k === 'heal') ops.push(['heal', p[1]]);
      else if (k === 'protect') ops.push(['protect']);
      else if (k === 'cure') ops.push(['cure']);
      else if (k === 'carry') ops.push(['carry', p[1], p[2]]);
      else if (k === 'gcharge') ops.push(['gcharge', p[1]]);
      else if (k === 'mhp') ops.push(['mhp', p[1]]);
      else if (k === 'foecharge') {
        if (parts.some(q => q[0] === 'shield' && q.length > 2 && q[2] === 'burned')) {
          const n = Math.min(-p[1], Math.max(0, foe.charge || 0));
          if (n > 0) ops.push(['shield', n]);
        }
        ops.push(['foecharge', p[1]]);
      }
      else if (k === 'kocharge') ops.push(['kocharge', p[1]]);
      else if (k === 'selfhurt') {
        const x = p[1] === 'same' ? ops.filter(o => o[0] === 'S' || o[0] === 'T' || o[0] === 'P').reduce((a, o) => a + o[1], 0) : p[1] === 'pct' ? pyround(me.maxhp * p[2] / 100) : p[2];
        ops.push(['selfhurt', Math.max(1, x)]);
      }
    }
    return ops;
  };
}

// ---------- items: crafted/food lists and TM powers ----------
const CRAFT = DATA.order.filter(k => ITEMS[k].cat === 'Crafted' && !ITEMS[k].flags.wonder);
const FOODS = DATA.order.filter(k => ITEMS[k].cat === 'Food');
const _i = (me, arr) => arr[Math.min(Math.max(me.stars, 1), 3) - 1];
const TMP = {
  TM_RAGE: (v, c, me, foe) => [['tmp', 'me', 'atk', Math.max(4, 2 + Math.floor((me.maxhp - me.hp) * 8 / Math.max(1, me.maxhp))), 6]],
  TM_RETURN: (v, c, me, foe) => [['S', trunc(D(_i(me, [20, 40, 80])) * 2.5 + .5)], ['buff', 'ap', 3]],
  TM_COUNTER: (v, c, me, foe) => [['S', Math.max(4, trunc((me.maxhp - me.hp) * 1.5 + .5))]],
  TM_DISABLE: (v, c, me, foe) => [['S', trunc(D(_i(me, [12, 25, 50])) * 2.5 + .5)], ['st', 'foe', 'flinch', 2]],
  TM_BULK_UP: (v, c, me, foe) => [['buff', 'atk', Math.max(3, me.base.atk)], ['buff', 'def', Math.max(2, me.base.defn)]],
  TM_CHARGE: (v, c, me, foe) => [['buff', 'xdmg', 2], ['S', Math.max(1, trunc(D(_i(me, [20, 40, 80])) * 1.5 + .5))]],
  TM_REFLECT: (v, c, me, foe) => [['reflect', 5, 150]],
  TM_PAYDAY: (v, c, me, foe) => [['S', trunc(D(_i(me, [15, 30, 60])) * 2.5 + .5)], ['S', trunc(D(_i(me, [15, 30, 60])) * 2.5 + .5)]],
  TM_FOCUS_PUNCH: (v, c, me, foe) => [['delay', 1, 4 * me.eff('atk')]],
  TM_HYPER_BEAM: (v, c, me, foe) => [['S', Math.max(1, trunc(D(_i(me, [65, 130, 250])) * 1.0 + .5))], ['st', 'me', 'fatigue', 1]],
  TM_SUBSTITUTE: (v, c, me, foe) => [['shield', Math.max(4, ceil(me.maxhp / 3))], ['protect']],
  TM_SKILL_SWAP: (v, c, me, foe) => powerOf(foe)(foe.v, foe.raw, me, foe).concat([['shield', 3]]),
};
Object.assign(PW, TMP);

// extra-card powers
const EXTRA_PW = {};
for (const c of DATA.cards) {
  if (c.pool === 'core') continue;
  if (c.parts2) { const a = opsfn(c.parts2[0]), b = opsfn(c.parts2[1]); EXTRA_PW[c.ab] = (v, raw, me, foe) => (me.casts % 2 === 1 ? a : b)(v, raw, me, foe); }
  else if (c.parts) EXTRA_PW[c.ab] = opsfn(c.parts);
  APM[c.ab] = c.apm || 'first';
}
function powerOf(c) { return PW[c.ability] || EXTRA_PW[c.ability] || (() => []); }

// ---------- passives ----------
const PAS = { Heracross: 'guts', Zangoose: 'toxic', Durant: 'durant', Komala: 'komala', Spinda: 'spinda', Pincurchin: 'pincurchin', Scraggy: 'moxie', Scrafty: 'moxie',
  Gligar: 'gligar', Gliscor: 'gligar', Regigigas: 'slow', Kartana: 'beastatk', Nihilego: 'beastap', Magearna: 'soul' };

// ---------- battle card ----------
class BCard {
  constructor(spec, items) {
    this.spec = spec; this.id = spec.id; this.name = spec.name; this.tier = spec.tier; this.stars = spec.stars; this.value = spec.value;
    this.types = new Set(spec.types); this.torder = spec.types.slice(); this.family = spec.family;
    this.hp0 = spec.hp; this.atk0 = spec.atk; this.def0 = spec.df; this.sdef0 = spec.sdf; this.spd0 = spec.spd; this.ppmax = spec.pp;
    this.ability = spec.ab; this.v = spec.v || []; this.raw = spec.raw || {}; this.abname = spec.abname; this.pool = spec.pool;
    this.items = (items || []).slice();
    this.reset();
  }
  reset() {
    this.hp = this.maxhp = this.hp0; this.charge = 0; this.shield = 0; this.ap = 0;
    this.st = counter(); this.tmp = []; this.perm = counter();
    this.syn = {}; this.boosts = 0; this.cycle = 0; this.atk_n = 0; this.hits_in = 0; this.rounds_on = 0;
    this.protect = false; this.thorns = 0; this.reflect = [0, 0]; this.spiky = [0, 0];
    this.aqua_used = false; this.fossil_used = false; this.fly_used = 0; this.swarm = 0; this.disguise = 0;
    this.pas = PAS[this.name] || ''; this.gl_used = false; this.first_attack = true; this.nextatk = 0; this.ground_n = 0; this.fire_n = 0;
    this.base = { atk: this.atk0, defn: this.def0, sdef: this.sdef0, spd: this.spd0, ap: 0 };
    this.casts = 0; this.dealt = 0; this.kos = 0; this.accel = 0; this.sf = 0;
    this.fl = counter(); this.itst = counter(); this.itn = counter(); this.critacc = 0; this.critpct = 0;
    this.imm = new Set(); this.immturn = 0; this.berry_used = false; this.revived = false; this.rhalf = false; this.dodge_n = 0; this.absorbed = 0; this.owed = 0;
    this.cover_used = false; this.bulb_used = false; this.charm_used = false; this.smoke_used = false; this.shtot = 0; this.expl_used = false;
    this.cursed = new Set(); this.dish = {}; this.dodge_n2 = 0; this.items_eff = []; this.elixir_used = false; this.surf_used = false; this.healboost = 0;
    this.berries = [];
  }
  orbBurn() { return !!this.fl.flameorb && !(this.fl.immune_neg || this.pas === 'komala'); }   // Flame Orb: the holder is permanently BURNED
  neg() { for (const k of NEG) if (this.st[k] > 0) return true; return this.orbBurn(); }
  lv(t) { return this.syn[t] || 0; }
  eff(stat) {
    const key = stat === 'def' ? 'defn' : stat;
    let v = this.base[key] + this.perm[key];
    for (const t of this.tmp) if (t[0] === stat) v += t[1];
    if ((stat === 'def' || stat === 'sdef') && (this.st.armor > 0 || this.st.freeze > 0)) return 0;
    if (stat === 'atk' && this.st.charm > 0) v -= 2;
    const p = this.pas;
    if (p) {
      if (stat === 'atk') {
        if (p === 'guts' && (this.neg() || this.st.poison_n > 0)) v += 2;
        if (p === 'toxic' && (this.st.poison > 0 || this.st.poison_n > 0)) v += 2;
        if (p === 'slow' && this.casts > 0) v += 2;
      }
      if (stat === 'spd' && p === 'slow') v += this.casts > 0 ? 2 : -2;
    }
    if (stat === 'spd') { if (this.st.para > 0) v -= 1; return Math.max(1, v); }
    return Math.max(0, v);
  }
}

// ---------- gourmet dishes ----------
const DISH = DATA.DISH, DEFAULT_DISH = DATA.default_dish;

class Side {
  constructor(lineup, idx) {
    this.idx = idx; this.lineup = lineup.slice(); this.fielded = []; this.active = null;
    this.fallen = 0; this.field_ko = 0; this.light = 0; this.amorph = 0; this.nsyn = 0; this.carry = counter(); this.pending = 0; this.delays = [];
    this.gems = counter(); this.rk = {}; this.battery = 0;
  }
}

class Duel {
  constructor(la, lb, rng, opts) {
    opts = opts || {};
    this.rng = rng || makeRng(1);
    const mk = l => l.map(c => c instanceof BCard ? c : new BCard(c.spec || c, c.items || []));
    la = mk(la); lb = mk(lb);
    this.sides = [new Side(la, 0), new Side(lb, 1)];
    for (const sd of this.sides) {
      for (const c of sd.lineup) c.side = sd;
      this.setup_items(sd);
      this.assign_syn(sd);
      this.cook(sd);
    }
    this.round = 0; this.max_rounds = opts.max_rounds || 60; this.nrounds = 0; this.acting = null;
    this.rec = !!opts.rec; this.buf = []; this.snaps = [];
    this.orig = this.sides.map(sd => sd.lineup.slice());
    this.streaks = opts.streaks || [0, 0];
  }

  // ----- items -----
  setup_items(sd) {
    for (const c of sd.lineup) {
      let out = [];
      for (const k of c.items) {
        const fl = ITEMS[k].flags;
        if (fl.chef) out = out.concat([this.rng.choice(FOODS), k]);
        else out.push(k);
      }
      c.items_eff = out;
      c.fl = counter(); c.itst = counter();
      const types = new Set(c.types);
      for (const k of out) {
        const it = ITEMS[k];
        for (const a in it.stats) c.itst[a] += it.stats[a];
        for (const a in it.flags) {
          const v = it.flags[a];
          if (a === 'type') types.add(v);
          else if (a === 'gem') sd.gems[v] += 1;
          else if (a === 'rock' || a === 'food' || a === 'perm') { /* skip */ }
          else if (typeof v === 'number') c.fl[a] += v;
          else c.fl[a] = v;
        }
        if (it.flags.rock) for (const a in it.flags) if (a.startsWith('r_')) sd.rk[a] = Math.max(sd.rk[a] || 0, it.flags[a]);
        if (it.flags.battery) sd.battery += 1;
      }
      c.types = types;
      if (c.fl.tm) c.ability = 'TM_' + c.fl.tm;
      c.berries = out.filter(k => ITEMS[k].flags.berry);
    }
  }

  item_enter(sd, c) {
    const f = c.fl, st = c.itst, rk = sd.rk;
    if (f.cheap) c.ppmax = Math.max(2, c.ppmax - 1);
    if (st.hp || f.hpmult) {
      const add = st.hp + pyround(c.hp0 * f.hpmult);
      c.maxhp = Math.max(1, c.maxhp + add); c.hp = Math.min(c.maxhp, Math.max(1, c.hp + add));
    }
    c.perm.atk += st.atk + (rk.r_atk || 0); c.perm.defn += st.df;
    c.perm.sdef += st.sdf + (rk.r_sdf || 0); c.perm.spd += st.spd + (rk.r_spd || 0);
    c.ap += st.ap; c.charge += st.ch; c.shield += st.sh + (rk.r_shield || 0);
    c.critpct = st.crit + (rk.r_crit || 0);
    if (f.flameorb || f.rusted) c.perm.atk += Math.max(1, trunc(c.base.atk * .5 + .5));
    if (f.egg) for (const k of ['atk', 'defn', 'sdef']) if (c.base[k] > 0) c.perm[k] += ceil(c.base[k] * .5);
    if (f.swarm) c.swarm += trunc(f.swarm);
    if (f.abshield) { c.shield += 3; c.immturn = 3; }
    if (f.expshare) {
      const others = sd.fielded.filter(x => x !== c).concat(sd.lineup);
      if (others.length) {
        for (const [k, a] of [['atk', 'atk0'], ['defn', 'def0'], ['sdef', 'sdef0']]) {
          const best = Math.max(...others.map(x => x[a])); const gap = best - c.base[k] - c.perm[k];
          if (gap > 0) c.perm[k] += gap;
        }
      }
    }
    if (sd.battery && c.types.has('ELECTRIC')) c.perm.spd += Math.min(2, sd.battery);
    if (c.owed) { c.hp = Math.max(1, c.hp - c.owed); c.owed = 0; }
    if (f.poffin && c.berries.length) { c.shield += c.berries.reduce((a, k) => a + ITEMS[k].flags.berry, 0); c.berry_used = true; }
    if (f.juice) c.itn.juice = 1;
    if (f.curry) c.tmp.push(['atk', 2, 3]);
    c.shtot = c.shield;
  }

  blocks_status(tgt, name, r) {
    if (!NEG.includes(name)) return [false, r];
    const f = tgt.fl;
    if (tgt.pas === 'komala' && ['burn', 'poison', 'freeze', 'para'].includes(name)) return [true, r];
    if (tgt.pas === 'spinda' && name === 'confuse') return [true, r];
    if (f.immune_neg || tgt.immturn > 0) return [true, r];
    if (f.immune_sleep && name === 'sleep') return [true, r];
    if (tgt.imm.has(name)) return [true, r];
    if (f.boots && name === 'flinch') return [true, r];
    if (f.twist) { tgt.perm.atk += 1; return [true, r]; }
    if (tgt.side.rk.r_odd) r = Math.max(1, r - 1);
    if (f.vestburn && name === 'burn') return [true, r];
    return [false, r];
  }

  berry_check(c, trigger) {
    trigger = trigger || 'hp';
    if (c.berry_used || !c.berries.length || c.hp <= 0) return;
    if (trigger === 'hp' && c.hp * 2 > c.maxhp) return;
    let fire = null;
    for (const k of c.berries) {
      const fl = ITEMS[k].flags;
      if (trigger === 'cast' && !fl.b_charge) continue;
      if (trigger === 'hp' || trigger === 'cast') fire = fire || k;
    }
    if (trigger === 'cast' && c.casts !== 1) return;
    if (fire === null) return;
    c.berry_used = true;
    for (const k of c.berries) {
      const fl = ITEMS[k].flags;
      let heal = fl.berry;
      if (fl.b_aguav) {
        heal = Math.max(heal, ceil(c.maxhp / 2));
        if (fl.b_aguav === 1) c.st.confuse = Math.max(c.st.confuse, 1);
      }
      this.heal(c, trunc(heal * (c.healboost ? 1.3 : 1)));
      c.shield += fl.b_shield || 0; c.perm.sdef += fl.b_sdf || 0; c.perm.defn += fl.b_df || 0;
      c.perm.atk += fl.b_atk || 0; c.perm.spd += fl.b_spd || 0; c.ap += fl.b_ap || 0;
      c.critpct += fl.b_crit || 0; c.charge = Math.min(c.ppmax, c.charge + (fl.b_charge || 0));
      if (fl.b_heal) c.healboost = 1;
      if (fl.b_cure) { for (const n of NEG) c.st[n] = 0; c.st.poison_n = 0; c.immturn = 3; }
      if (fl.b_protect) c.protect = true;
      if (fl.b_spiky) c.spiky = [fl.b_spiky, 1];
      if (fl.b_reflect) c.reflect = [fl.b_reflect, 50];
      if (fl.b_immune) c.imm.add(fl.b_immune);
    }
    if (c.itn.juice) c.shield += 5;
    this.say(`${c.name} eats its berry`);
  }

  item_attack(me, foe, dealt, crit) {
    const f = me.fl;
    if (empty(f) && empty(me.side.rk) && !me.perm.xdmg) return;
    me.itn.att += 1; const a = me.itn.att;
    const ev = n => n && a % trunc(n) === 0;
    const rk = me.side.rk;
    const osd = this.sides[1 - me.side.idx];
    if (f.wide && a % 2 === 0) osd.pending += 1;
    if (me.perm.xdmg && foe.hp > 0) this.hit(me, foe, me.perm.xdmg, 'T');
    if (f.glove && foe.hp > 0) this.hit(me, foe, 1, 'T');
    if (f.wand && foe.hp > 0) {
      let x = 1;
      if (f.w_surround) x = 2;
      if (f.w_twoedge) { x = 3; if (a % 2 === 0) this.hit(me, me, 1, 'T'); }
      if (f.w_crit && crit) x += 2;
      if (f.w_spirit) x += Math.floor(me.casts / 2);
      this.hit(me, foe, x, 'S');
      if (f.w_guide) osd.pending += Math.floor((x + 1) / 2);
      if (ev(f.w_tunnel)) osd.pending += 2;
    }
    if (foe.hp <= 0) return;
    if (dealt <= 0) return;
    if (f.armorbreak) this.apply_st(foe, 'armor', 1);
    if (f.reaper && crit) this.hit(me, foe, 1, 'S');
    if (f.scope && crit) foe.charge = Math.max(0, foe.charge - 1);
    if (f.blackbelt && crit) me.shield += Math.floor((dealt + 1) / 2);
    if (f.shellbell) this.heal(me, 1);
    if (rk.r_blood && foe.st.wound > 0) this.heal(me, 1);
    const sh = f.shred;
    if (sh === 'df') foe.perm.defn = Math.max(foe.perm.defn - 1, -2);
    else if (sh === 'sdf') foe.perm.sdef = Math.max(foe.perm.sdef - 1, -2);
    if (ev(f.parat)) this.apply_st(foe, 'para', 1);
    if (f.upgrade && a % 2 === 0 && me.perm.upg < 4) { me.perm.upg += 1; me.perm.spd += 1; }
    if (f.blueorb && a % 3 === 0) { this.hit(me, foe, 1, 'S'); foe.charge = Math.max(0, foe.charge - 1); }
    if (f.loaded && a % 2 === 0) osd.pending += Math.max(1, trunc(dealt * .5));
    if (f.dst) { if (a % 2 === 0) me.charge += 1; }
    if (rk.r_freeze && a % rk.r_freeze === 0) this.apply_st(foe, 'freeze', 1);
    if (ev(f.w_steal)) { foe.maxhp = Math.max(1, foe.maxhp - 1); foe.hp = Math.min(foe.hp, foe.maxhp); me.maxhp += 1; me.hp += 1; }
    if (ev(f.w_spirit)) me.charge += 1;
    if (ev(f.w_conf)) { this.apply_st(foe, 'confuse', 1); foe.perm.sdef = Math.max(foe.perm.sdef - 1, -foe.base.sdef); }
    if (ev(f.w_petrify)) { this.apply_st(foe, 'flinch', 1); foe.perm.defn = Math.max(foe.perm.defn - 1, -foe.base.defn); }
    if (ev(f.w_slow)) this.apply_st(foe, 'para', 2);
    if (ev(f.w_sleep)) { this.apply_st(foe, 'sleep', 1); foe.perm.atk = Math.max(foe.perm.atk - 1, -foe.base.atk); }
    if (ev(f.w_warp)) this.apply_st(foe, 'flinch', 1);
    if (ev(f.w_switch)) foe.charge = Math.max(0, foe.charge - 1);
    if (ev(f.w_whirl)) { this.apply_st(foe, 'flinch', 1); this.hit(me, foe, 1, 'T'); }
  }

  item_first_hit(me, foe) {
    const fs = me.fl.first_status;
    if (fs && foe.hp > 0) {
      if (fs === 'freeze') this.apply_st(foe, 'freeze', 1);
      else if (fs === 'charm') this.apply_st(foe, 'charm', 2);
      else if (fs === 'flinch2') this.apply_st(foe, 'flinch', 2);
    }
  }

  item_on_hit(src, dst, amount, kind, basic, dmg_taken, absorbed) {
    const f = dst.fl;
    if (empty(f) && empty(dst.side.rk)) return;
    if (f.barb && basic) { this.hit(dst, src, 1, 'T'); this.apply_st(src, 'wound', 1); }
    if (f.w_pounce && basic) {
      dst.itn.hit += 1;
      if (dst.itn.hit % trunc(f.w_pounce) === 0) this.hit(dst, src, 2, 'S');
    }
    if (f.muscle) {
      dst.itn.mus += 1;
      if (dst.itn.mus % 3 === 0 && dst.perm.musn < 3) { dst.perm.musn += 1; dst.perm.atk += 1; dst.perm.defn += 1; dst.perm.spd += 1; }
    }
    if (f.explosive && !dst.expl_used && dst.shield <= 0 && absorbed > 0) {
      dst.expl_used = true; this.hit(dst, src, Math.max(1, Math.floor(dst.shtot / 2)), 'S');
    }
    if (dst.hp > 0) {
      if (f.bulb && !dst.bulb_used && dst.hp * 2 <= dst.maxhp) { dst.bulb_used = true; this.hit(dst, src, Math.max(1, dst.absorbed), 'S'); }
      if (f.charm30 && !dst.charm_used && dst.hp * 2 <= dst.maxhp) { dst.charm_used = true; dst.protect = true; dst.charge = Math.min(dst.ppmax, dst.charge + 1); }
      if (f.smoke && !dst.smoke_used && dst.hp * 2 <= dst.maxhp) { dst.smoke_used = true; dst.shield += 4; this.apply_st(src, 'para', 2); }
      if (dst.berries.length) this.berry_check(dst, 'hp');
    }
  }

  item_turn(c, foe) {
    const f = c.fl, rk = c.side.rk, n = c.rounds_on;
    if (c.immturn > 0) c.immturn -= 1;
    if (empty(f) && empty(rk)) return;
    if (f.soul) {
      if (c.ap < 4 + c.itst.ap) c.ap += 1;
      if (n % 3 === 0) c.charge = Math.min(c.ppmax, c.charge + 1);
    }
    if (f.greenorb && n % 2 === 0) {
      const over = c.hp + 1 > c.maxhp;
      this.heal(c, 1);
      if (over) c.charge = Math.min(c.ppmax, c.charge + 1);
    }
    if (f.mach && n % trunc(f.mach > 1 ? f.mach : 4) === 0 && c.perm.mach < 3) { c.perm.mach += 1; c.perm.spd += 1; }
    if (f.metronome && n % trunc(f.metronome) === 0) c.charge = Math.min(c.ppmax, c.charge + 1);
    if (f.pokerus && n % 3 === 0 && c.perm.pok < 3) { c.perm.pok += 1; c.perm.atk += 1; c.ap += 1; }
    if (f.flameorb && n % 2 === 0) c.hp -= 1;
    if (rk.r_heal && n % rk.r_heal === 0) this.heal(c, 1);
    if (rk.r_charge && n % rk.r_charge === 0) c.charge = Math.min(c.ppmax, c.charge + 1);
    if (rk.r_speed && n % rk.r_speed === 0 && c.perm.rs < 3) { c.perm.rs += 1; c.perm.spd += 1; }
  }

  // ----- synergies -----
  assign_syn(side) {
    const cnt = {}; const seen = new Set();
    const add = (t, n) => { cnt[t] = (cnt[t] || 0) + (n === undefined ? 1 : n); };
    for (const c of side.lineup) for (const t of c.types) { const key = t + '|' + c.family; if (!seen.has(key)) { seen.add(key); add(t); } }
    for (const g in side.gems) add(g, side.gems[g]);
    if (level_of('DRAGON', cnt.DRAGON || 0) >= 1) {
      for (const c of side.lineup) if (c.types.has('DRAGON')) {
        const sec = c.torder.slice(0, 2).filter(t => t !== 'DRAGON');
        if (sec.length) add(sec[0]);
      }
    }
    for (const c of side.lineup) {
      c.syn = {};
      for (const t of c.types) { const l = level_of(t, cnt[t] || 0); if (l > 0) c.syn[t] = l; }
    }
    side.light = level_of('LIGHT', cnt.LIGHT || 0); side.amorph = level_of('AMORPHOUS', cnt.AMORPHOUS || 0);
    side.ndrag = side.lineup.filter(c => c.types.has('DRAGON')).length;
    const ts = new Set(); for (const c of side.lineup) for (const t in c.syn) ts.add(t);
    side.nsyn = ts.size; side.cnt = cnt;
  }

  cook(sd) {
    const lin = sd.lineup;
    lin.forEach((c, i) => {
      const l = c.lv('GOURMET'); if (!l) return;
      const j = i + 1 < lin.length ? i + 1 : i - 1;
      if (j < 0) return;
      const t = lin[j], d = t.dish;
      for (const e of (DISH[c.family] || DEFAULT_DISH)[l - 1]) {
        const k = e[0];
        if (k === 'atk') t.perm.atk += e[1];
        else if (k === 'def') t.perm.defn += e[1];
        else if (k === 'sdef') t.perm.sdef += e[1];
        else if (k === 'spd') t.perm.spd += e[1];
        else if (k === 'ap') t.ap += e[1];
        else if (k === 'hp') { t.maxhp = Math.max(1, t.maxhp + e[1]); t.hp = Math.max(1, t.hp + e[1]); }
        else if (k === 'shield') t.perm.dshield += e[1];
        else if (k === 'shieldpct') t.perm.dshield += Math.max(2, trunc(t.maxhp * e[1] / 100 + .5));
        else if (k === 'charge') t.perm.dcharge += e[1];
        else if (k === 'protect') t.perm.dprotect = 1;
        else if (k === 'rage') t.tmp.push(['atk', e[1], 3]);
        else if (k === 'rand') {
          for (let q = 0; q < e[1]; q++) {
            const r = this.rng.choice(['atk', 'def', 'sdef', 'spd', 'hp']);
            if (r === 'hp') { t.maxhp += 2; t.hp += 2; } else t.perm[r === 'def' ? 'defn' : r] += 1;
          }
        } else if (k === 'first') { (d.first = d.first || []).push([e[1], e[2]]); }
        else if (k === 'crit' || k === 'regen') d[k] = (d[k] || 0) + e[1];
        else if (k !== 'dodge') d[k] = Math.max(d[k] || 0, e[1]);
        else d[k] = (k in d) ? Math.min(d[k], e[1]) : e[1];
      }
    });
  }

  spotlight(sd) {
    const lg = sd.light; if (!lg) return;
    const c = sd.active; c.ap += 1; c.perm.atk += 1;
    if (lg >= 2) c.charge = Math.min(c.ppmax, c.charge + 2);
    if (lg >= 3) { c.perm.defn += 1; c.perm.sdef += 1; c.protect = true; }
    this.say(`${c.name} stands in the spotlight`);
  }

  say(msg) { if (this.rec) this.buf.push(msg); }

  // ----- entering -----
  enter(side, card) {
    const i = side.lineup.indexOf(card); side.lineup.splice(i, 1);
    side.fielded.push(card); side.active = card;
    const L = t => card.lv(t);
    const pick = (t, arr) => L(t) ? arr[L(t) - 1] : 0;
    card.shield += pick('NORMAL', [5, 7, 10, 12]);
    if (L('NORMAL') === 4) { card.perm.atk += 1; card.ap += 1; }
    card.perm.defn += pick('FIGHTING', [1, 1, 2, 2]) + pick('ROCK', [2, 3, 5]);
    card.perm.sdef += pick('ICE', [1, 2, 2, 3]);
    card.ap += pick('PSYCHIC', [2, 3, 5]);
    if (L('WILD')) { const w = L('WILD'); card.perm.spd += [1, 1, 2, 2][w - 1]; card.perm.atk += [0, 1, 2, 2][w - 1]; }
    if (L('WATER')) card.charge += 2;
    if (L('DRAGON') >= 2) card.shield += side.ndrag;
    if (L('DRAGON') >= 3) { const k = Math.max(1, Math.floor(side.ndrag / 2)); card.perm.spd += 1; card.ap += k; }
    if (L('FIELD') && side.field_ko) {
      const k = side.field_ko; card.maxhp += [2, 3, 4][L('FIELD') - 1] * k; card.hp = card.maxhp;
      if (L('FIELD') >= 2) card.perm.spd += Math.min(3, k);
    }
    if (side.amorph) {
      const am = side.amorph, n = side.nsyn;
      const hpb = n * [1, 1, 2][am - 1]; card.maxhp += hpb; card.hp += hpb;
      if (am >= 2) card.perm.spd += Math.floor(n / [9, 3, 2][am - 1]);
    }
    card.swarm = pick('BUG', [1, 2, 2, 3]);
    card.disguise = card.name === 'Mimikyu' ? 1 : 0;
    if (L('BUG') === 3) card.perm.sdef += 1;
    card.shield += card.perm.dshield; card.charge += card.perm.dcharge;
    if (card.perm.dprotect) card.protect = true;
    const cr = side.carry;
    card.charge += cr.charge; card.shield += cr.shield; card.perm.spd += cr.spd;
    card.perm.defn += cr.def; card.perm.atk += cr.atk; card.rhalf = cr.revive > 0;
    this.heal(card, cr.heal); card.maxhp += cr.maxhp; card.hp += cr.maxhp;
    side.carry = counter();
    this.item_enter(side, card);
    if (side.pending) {
      if (!card.fl.boots) { this.say(`  splash ${side.pending} hits ${card.name}`); card.hp -= side.pending; }
      side.pending = 0;
    }
    card.charge = Math.min(card.charge, card.ppmax);
    this.say(`${card.name} enters the battle`);
  }

  heal(card, x) {
    if (x <= 0 || card.st.wound > 0) return;
    const b = card.hp; card.hp = Math.min(card.maxhp, card.hp + x);
    if (card.hp > b) this.say(`${card.name} heals ${card.hp - b}`);
  }

  // ----- damage -----
  apply_st(tgt, name, r, pw) {
    const [blocked, r2] = this.blocks_status(tgt, name, r); r = r2;
    if (blocked) return;
    if (name === 'burn') tgt.st.burn_pow = Math.max(pw || 1, tgt.st.burn > 0 ? tgt.st.burn_pow : 0);
    if (NEG.includes(name) && tgt.lv('AQUATIC') && !tgt.aqua_used) { tgt.aqua_used = true; return; }
    tgt.st[name] = Math.max(tgt.st[name], r);
    this.say(`${tgt.name} is ${STN[name] || name.toUpperCase()} (${r} turn${r !== 1 ? 's' : ''})`);
  }

  hit(src, dst, amount, kind, basic, ignore_def) {
    basic = !!basic; ignore_def = !!ignore_def;
    if (amount <= 0 || dst.hp <= 0) return 0;
    if (dst.fl.doll && (kind === 'P' || kind === 'S')) amount = Math.max(1, amount - 1);
    const lk = dst.st.locked > 0;      // LOCKED: this hit ignores Fly Away, dodge and evade; the lock is then used up
    if (lk) dst.st.locked = 0;
    if (basic && dst.fl.dodge && !lk) {
      dst.dodge_n += 1;
      if (dst.dodge_n % trunc(dst.fl.dodge) === 0) { this.say(`${dst.name} dodges`); return 0; }
    }
    if (basic && dst.dish.dodge && !lk) {
      dst.dodge_n2 += 1;
      if (dst.dodge_n2 % dst.dish.dodge === 0) { this.say(`${dst.name} dodges`); return 0; }
    }
    if (dst.protect) { this.say(`${dst.name} is protected`); return 0; }
    if (basic && dst.swarm > 0) {
      this.say(`${dst.name}'s swarm token blocks the attack`);
      dst.swarm -= 1;
      if (dst.lv('BUG') >= 9) src.hp -= 1;
      return 0;
    }
    if (basic && dst.lv('GHOST')) {
      dst.hits_in += 1;
      if (dst.hits_in % 4 === 0 && dst.lv('GHOST') >= 1 && !lk) {
        this.say(`${dst.name} evades`);
        if (dst.lv('GHOST') >= 4) this.hit(dst, src, 1, 'T');
        return 0;
      }
    }
    let blk;
    if (kind === 'P') blk = dst.eff('def');
    else if (kind === 'S') blk = ignore_def ? 0 : dst.eff('sdef');
    else blk = 0;
    let dmg = Math.max(1, amount - blk);
    if (blk > 0) {
      dst.absorbed += Math.min(amount, blk);
      if (kind === 'S' && dst.fl.lens && src !== dst) this.hit(dst, src, Math.min(blk, amount), 'T');
    }
    if (kind === 'S' && src.fl.nomicon && src !== dst) { this.apply_st(dst, 'burn', 3); dst.perm.sdef = Math.max(dst.perm.sdef - 1, -2); }
    const absorbed = Math.max(0, Math.min(dst.shield, dmg - 1)); dst.shield -= absorbed; const dmg_hp = dmg - absorbed;
    dst.hp -= dmg_hp; src.dealt += dmg;
    if (src === this.acting && src !== dst && src.lv('HUMAN') && dst.hp > -999) { if (basic) this.heal(src, [1, 2, 3][src.lv('HUMAN') - 1]); }
    this.say(`${src.name} hits ${dst.name} for ${dmg} ${{ P: 'physical', S: 'special', T: 'true' }[kind]}` + (absorbed ? ` (${absorbed} absorbed by shield)` : ''));
    this.ev && this.ev({ t: 'hit', src, dst, dmg, kind, absorbed });
    if (basic && kind === 'P') {
      if (dst.thorns > 0) { dst.thorns -= 1; src.perm.defn = Math.max(-src.base.defn, src.perm.defn - 1); }
      if (dst.reflect[0] > 0) this.hit(dst, src, trunc(amount * dst.reflect[1] / 100), 'S');
      if (dst.spiky[0] > 0) { src.st.wound = Math.max(src.st.wound, 2); this.hit(dst, src, dst.spiky[1], 'S'); }
      if (dst.lv('FIGHTING') >= 2) {
        dst.sf += 1;
        if (dst.sf % { 2: 4, 3: 3, 4: 2 }[dst.lv('FIGHTING')] === 0) { if (dst.lv('FIGHTING') >= 3) src.shield = 0; src.hp -= 1; }
      }
    }
    if (dst.hp <= 0 && !dst.revived) {
      for (const ally of dst.side.lineup) {
        if (ally.fl.cover && !ally.cover_used) { ally.cover_used = true; ally.owed += (1 - dst.hp); dst.hp = 1; break; }
      }
    }
    this.item_on_hit(src, dst, amount, kind, basic, dmg_hp, absorbed);
    if (dst.pas === 'pincurchin' && kind === 'S' && src !== dst && dst.hp > 0 && src.hp > 0) this.apply_st(src, 'para', 1);
    if (dst.hp > 0 && dst.dish.nanab && !dst.perm.nanabu && dst.hp * 2 <= dst.maxhp) { dst.perm.nanabu = 1; this.heal(dst, dst.dish.nanab); }
    if (dst.hp > 0 && dst.disguise && dst.hp * 2 <= dst.maxhp) { dst.disguise = 0; dst.perm.atk += 2; dst.protect = true; this.say(`${dst.name} is busted`); }
    if (dst.hp > 0) {
      if (dst.lv('FOSSIL') && !dst.fossil_used && dst.hp * 2 <= dst.maxhp) {
        dst.fossil_used = true; const l = dst.lv('FOSSIL');
        dst.shield += [2, 4, 6][l - 1]; dst.perm.atk += (l < 3 ? 1 : 2);
      }
      if (dst.lv('WILD') === 4 && !dst.fl.berserk && dst.hp * 2 <= dst.maxhp) { dst.fl.berserk = 1; dst.perm.atk += 2; dst.perm.spd += 2; dst.shield += 3; }
      if (dst.lv('FLYING') && !lk && dst.fly_used < [1, 1, 2, 3][dst.lv('FLYING') - 1] && dst.hp * 2 <= dst.maxhp) {
        dst.fly_used += 1; dst.protect = true;
        if (dst.fly_used === 1) dst.perm.spd += 1;
        if (dst.lv('FLYING') >= 2) dst.perm.sdef += 1;
      }
    }
    return dmg;
  }

  // ----- attacking -----
  attack(me, foe, free) {
    const L = t => me.lv(t);
    let base = me.eff('atk');
    if (me.st.confuse > 0) { base = Math.floor(base / 2); me.st.confuse = 0; }
    me.atk_n += 1;
    let crit = false, want = false;
    const gen = me.critpct + (me.dish.crit || 0) + (L('DARK') ? [1, 2, 3][L('DARK') - 1] : 0);
    if (gen) { me.critacc += gen; if (me.critacc >= 5) { me.critacc -= 5; want = true; } }
    if (want && !(foe.lv('ROCK') >= 2 || foe.fl.helmet || foe.side.rk.r_crit)) { crit = true; base = base * 2; this.say(`${me.name} lands a critical hit`); }
    if (me.fl.pads && foe.shield > 0) base *= 2;
    let tp = L('STEEL') ? Math.min(base, [1, 2, 4, 5][L('STEEL') - 1]) : 0;
    if (me.fl.redorb) tp = Math.min(base, tp + 1);
    let spec = 0;
    if (me.nextatk) { spec += me.nextatk; me.nextatk = 0; }
    let dealt = 0;
    if (foe.hp > 0) {
      dealt += this.hit(me, foe, base - tp, 'P', true);
      if (tp) dealt += this.hit(me, foe, tp, 'T');
      if (spec) dealt += this.hit(me, foe, spec, 'S');
    }
    if (L('ELECTRIC')) this.hit(me, foe, [1, 2, 3][L('ELECTRIC') - 1], 'S');
    if (foe.hp > 0 && dealt > 0) {
      if (L('FIRE') && me.atk_n % [3, 2, 2, 1][L('FIRE') - 1] === 0) this.apply_st(foe, 'burn', L('FIRE') === 4 ? 4 : 3, L('FIRE') >= 3 ? 2 : 1);
      if (L('POISON')) foe.st.poison_n = Math.min([1, 2, 3][L('POISON') - 1], foe.st.poison_n + 1);
      if (L('WILD')) this.apply_st(foe, 'wound', L('WILD') >= 3 ? 2 : 1);
      if (L('MONSTER') && me.first_attack) this.apply_st(foe, 'flinch', 1);
      if (L('GHOST') >= 2 && !me.cursed.has(foe)) {
        me.cursed.add(foe); foe.perm.defn -= 1;
        if (L('GHOST') >= 3) foe.perm.atk -= 1;
        if (L('GHOST') >= 4) foe.perm.sdef -= 1;
      }
      const dd = me.dish;
      if (!empty(dd)) {
        if (me.first_attack) for (const [st_, r_] of (dd.first || [])) this.apply_st(foe, st_, r_);
        if (dd.tart && me.perm.tartn < dd.tart) { me.perm.tartn += 1; foe.perm.defn -= 1; }
        if (dd.sludge) foe.st.poison_n = Math.min(dd.sludge, foe.st.poison_n + 1);
        if (dd.freezen && me.atk_n % dd.freezen === 0) this.apply_st(foe, 'freeze', 1);
        if (dd.charmn && me.atk_n % dd.charmn === 0) this.apply_st(foe, 'charm', 2);
      }
      if (L('FAIRY') && me.atk_n % [2, 2, 2, 1][L('FAIRY') - 1] === 0) {
        this.apply_st(foe, 'confuse', 1);
        if (L('FAIRY') >= 2) this.apply_st(foe, 'charm', 2);
        if (L('FAIRY') >= 3) foe.tmp.push(['spd', -1, 2]);
      }
      if (L('ICE') >= 2 && me.atk_n % { 2: 6, 3: 5, 4: 4 }[L('ICE')] === 0) this.apply_st(foe, 'freeze', 1);
    }
    if (me.first_attack && !empty(me.fl)) this.item_first_hit(me, foe);
    this.item_attack(me, foe, dealt, crit);
    me.first_attack = false;
    if (!free && me.st.para <= 0 && me.st.fatigue <= 0) {
      if (me.fl.nullify) me.perm.atk += 1;
      else me.charge += L('WATER') === 3 ? 2 : 1;
    }
    return dealt;
  }

  // ----- casting -----
  cast(me, foe) {
    me.casts += 1; me.charge = 0;
    let ops = powerOf(me)(me.v, me.raw, me, foe);
    if (me.fl.starpiece) ops = ops.map(o => ['S', 'P', 'T', 'Sp', 'drain', 'shield', 'heal'].includes(o[0]) ? [o[0], o[1] * 2, ...o.slice(2)] : o);
    let first = true;
    const mode = APM[me.ability] || 'first';
    const hasdmg = ops.some(o => ['S', 'P', 'T', 'Sp', 'drain', 'delay'].includes(o[0]));
    const ap_ = (mode === 'first' || mode === 'all') ? me.ap : (mode === 'half' || mode === 'each_half') ? Math.floor(me.ap / 2) : 0;
    let shield_done = false;
    for (const op of ops) {
      const k = op[0];
      if (k === 'S' || k === 'P' || k === 'T' || k === 'Sp') {
        const x = op[1] + ((first || mode === 'each_half') ? ap_ : 0);
        first = false;
        if (foe.hp <= 0) continue;
        const kind = (k === 'S' || k === 'Sp') ? 'S' : k;
        this.hit(me, foe, x, kind, false, (k === 'Sp' || me.lv('PSYCHIC') === 3));
        if (op.length > 2 && op[2]) this.sides[1 - me.side.idx].pending += Math.floor(x / 2);
        if (foe.hp <= 0) this.kill_hooks(me, foe);
      } else if (k === 'drain') {
        const x = op[1] + ((first || mode === 'each_half') ? ap_ : 0); first = false;
        const d = this.hit(me, foe, x, 'S'); this.heal(me, trunc(d * op[2]));
        if (foe.hp <= 0) this.kill_hooks(me, foe);
      } else if (k === 'shield') {
        if (me.st.wound <= 0) me.shield += op[1] + ((!hasdmg && !shield_done) ? ap_ : 0);
        shield_done = true;
      } else if (k === 'heal') { this.heal(me, op[1] + ((!hasdmg && !shield_done) ? ap_ : 0)); shield_done = true; }
      else if (k === 'st') this.apply_st(op[1] === 'foe' ? foe : me, op[2], op[3]);
      else if (k === 'buff') {
        const st_ = op[1] === 'def' ? 'defn' : op[1];
        if (st_ === 'ap') me.ap += op[2]; else me.perm[st_] += op[2];
        if (op[2] > 0) me.boosts += 1;
      } else if (k === 'tmp') { const tgt = op[1] === 'foe' ? foe : me; tgt.tmp.push([op[2], op[3], op[4]]); }
      else if (k === 'protect') me.protect = true;
      else if (k === 'carry') me.side.carry[op[1]] += op[2];
      else if (k === 'foecharge') foe.charge = Math.max(0, foe.charge + op[1]);
      else if (k === 'execute') { if (foe.hp > 0 && foe.hp <= op[1]) { foe.hp = 0; this.kill_hooks(me, foe); } }
      else if (k === 'koif') { if (foe.hp > 0 && op[1].some(n => foe.st[n] > 0) && !(op[2] && foe.types.has(op[2]))) { foe.hp = 0; this.kill_hooks(me, foe); } }
      else if (k === 'kocharge') { if (foe.hp <= 0) me.charge = Math.min(me.ppmax, me.charge + op[1]); }
      else if (k === 'koheal') { if (foe.hp <= 0) this.heal(me, trunc(foe.maxhp * op[1])); }
      else if (k === 'delay') this.sides[1 - me.side.idx].delays.push([op[1], op[2] + (op.length > 3 ? 0 : ap_), me.side.idx]);
      else if (k === 'atk') { for (let q = 0; q < op[1]; q++) if (foe.hp > 0) this.attack(me, foe, true); }
      else if (k === 'reflect') me.reflect = [op[1], op[2]];
      else if (k === 'spiky') me.spiky = [op[1], op[2]];
      else if (k === 'cure') { for (const n of NEG) me.st[n] = 0; me.st.poison_n = 0; }
      else if (k === 'ap_foe') foe.ap = Math.max(0, foe.ap + op[1]);
      else if (k === 'gcharge') me.charge = Math.min(me.ppmax, me.charge + op[1]);
      else if (k === 'mhp') { me.maxhp += op[1]; me.hp += op[1]; }
      else if (k === 'selfhurt') { me.hp -= op[1]; if (me.hp <= 0) me.hp = 1; }
      else if (k === 'nextatk') me.nextatk += op[1];
    }
    if (me.ability === 'DRUM_BEATING') me.cycle += 1;
    const f = me.fl;
    if (!empty(f)) {
      if (f.aqua) me.charge = Math.min(me.ppmax, me.charge + 1);
      if (f.stardust) me.shield += trunc(f.stardust);
      if (f.elixir && !me.elixir_used) { me.elixir_used = true; me.charge = me.ppmax; }
      if (f.terrain) me.side.carry.shield += 2;
      if (f.ball) me.side.carry.shield += 3;
      if (f.surf && !me.surf_used) { me.surf_used = true; this.sides[1 - me.side.idx].pending += 3; }
      if (me.berries.length) this.berry_check(me, 'cast');
    }
    const L = t => me.lv(t);
    if (L('FIRE') >= 2) me.perm.atk += 1;
    if (L('WATER') >= 2) me.charge = Math.min(me.ppmax, me.charge + 1);
    if (L('SOUND')) {
      if (me.perm.soundn < L('SOUND')) {
        me.perm.soundn += 1; me.perm.atk += 1;
        if (L('SOUND') === 3 && me.perm.soundn === 1) me.perm.spd += 1;
      }
      if (L('SOUND') === 3) me.side.carry.charge += 1;
    }
  }

  kill_hooks(killer, dead) {
    killer.kos += 1;
    const L = t => killer.lv(t), kp = killer.pas;
    if (kp === 'moxie' || kp === 'beastatk') killer.perm.atk += 1;
    else if (kp === 'beastap') killer.ap += 2;
    else if (kp === 'soul') { killer.ap += 2; killer.charge = Math.min(killer.ppmax, killer.charge + 1); }
    if (L('MONSTER') >= 2) {
      killer.perm.atk += 1; this.heal(killer, 1);
      if (L('MONSTER') >= 3) { killer.maxhp += 1; killer.hp += 1; }
      if (L('MONSTER') === 4) killer.perm.atk += 1;
    }
  }

  act(me, foe) {
    if (me.hp <= 0 || foe.hp <= 0) return;
    if (me.st.sleep > 0 || me.st.freeze > 0) { this.say(`${me.name} skips`); return; }
    this.say(`${me.name} attacks ${foe.name}`);
    this.acting = me;
    this.attack(me, foe, false);
    if (me.pas === 'durant' && foe.hp > 0) {
      const nb = me.side.lineup.filter(c => c !== me && c.types.has('BUG')).length;
      if (nb) this.hit(me, foe, nb, 'T');
    }
    if (me.pas === 'spinda' && foe.hp > 0 && foe.st.confuse > 0) this.hit(me, foe, 2, 'S');
    if (foe.hp <= 0) { this.kill_hooks(me, foe); return; }
    if (me.charge >= me.ppmax + (foe.lv('ELECTRIC') === 3 ? 1 : 0) && me.st.flinch <= 0 && !me.fl.nullify) {
      this.say(`${me.name} casts ${me.abname}`);
      this.ev && this.ev({ t: 'cast', src: me });
      this.cast(me, foe);
    }
  }

  // ----- snapshots for the replay -----
  snap(turn, mover, bar) {
    const sides = this.sides.map(sd => {
      const cards = this.orig[sd.idx].map(c => ({ hp: Math.max(0, c.hp), mx: c.maxhp, ent: sd.fielded.includes(c), dead: sd.fielded.includes(c) && c.hp <= 0 }));
      const a = sd.active; let act = null;
      if (a) {
        const st = {}; for (const k of Object.keys(a.st)) if (a.st[k] && k !== 'poison_n' && k !== 'burn_pow') st[k] = a.st[k];
        act = { i: this.orig[sd.idx].indexOf(a), hp: Math.max(0, a.hp), mx: a.maxhp, sh: a.shield, ch: a.charge, pp: a.ppmax,
          atk: a.eff('atk'), df: a.eff('def'), sd: a.eff('sdef'), sp: a.eff('spd'), ap: a.ap, st, pois: a.st.poison_n || 0, prot: a.protect, sw: a.swarm,
          syn: Object.assign({}, a.syn), items: a.items_eff.slice() };
      }
      return { cards, act };
    });
    this.snaps.push({ t: turn, mv: mover, bar, sides, ev: this.buf.slice() }); this.buf.length = 0;
  }

  end_turn(me, foe) {
    const c = me, L = t => c.lv(t), sd = me.side;
    if (c.hp > 0) {
      c.rounds_on += 1;
      if (c.st.burn > 0 && !(c.fl.vest || c.fl.vestburn)) c.hp -= (!(c.side.rk.r_atk && c.rounds_on % 2)) ? (c.st.burn_pow || 1) : 0;
      if (c.st.poison_n > 0) {
        let pn = c.st.poison_n;
        if (c.fl.vest) pn = Math.floor(pn / 2);
        if (c.pas === 'toxic') pn = Math.floor(pn / 2);
        pn = Math.max(0, pn - (c.side.rk.r_clay || 0));
        if (c.pas === 'komala') pn = 0;
        if (c.pas === 'gligar' && !c.gl_used && pn > 0) { c.gl_used = true; this.heal(c, pn); pn = 0; }
        c.hp -= pn;
      }
      this.item_turn(c, foe);
      if (L('GRASS')) {
        const h = [1, 2, 2, 3][L('GRASS') - 1];
        const over = Math.max(0, c.hp + h - c.maxhp); this.heal(c, h);
        if (L('GRASS') >= 3 && over && c.perm.gmax < (L('GRASS') === 3 ? 3 : 5)) { c.perm.gmax += 1; c.maxhp += 1; c.hp += 1; }
      }
      if (L('FIRE') >= 3 && c.fire_n < (L('FIRE') === 3 ? 4 : 6)) { c.fire_n += 1; c.perm.atk += 1; }
      if (L('GROUND')) {
        const lv = L('GROUND');
        if (lv >= 2 || c.rounds_on % 2 === 0) {
          const cap = { 1: 2, 2: 2, 3: 3, 4: 5 }[lv];
          if (c.ground_n < cap) { c.ground_n += 1; c.perm.defn += 1; if (lv >= 3) c.perm.atk += 1; }
        }
      }
      if (c.dish.regen) this.heal(c, c.dish.regen);
      if (L('AQUATIC') >= 2 && c.rounds_on === 3) {
        for (const n of NEG) c.st[n] = 0;
        if (foe && foe.hp > 0) this.hit(c, foe, { 2: 2, 3: 4, 4: 6 }[L('AQUATIC')], 'T');
        if (L('AQUATIC') >= 3) this.heal(c, L('AQUATIC') === 3 ? 2 : 4);
      }
    }
    const osd = this.sides[1 - sd.idx]; const nd = [];
    for (const dl of osd.delays) {
      if (dl[2] === sd.idx) {
        dl[0] -= 1;
        if (dl[0] <= 0) { const t = osd.active; if (t && t.hp > 0) this.hit(c, t, dl[1], 'S'); continue; }
      }
      nd.push(dl);
    }
    osd.delays = nd;
    for (const n of ['para', 'flinch', 'charm', 'wound', 'armor', 'fatigue', 'burn']) if (c.st[n] > 0) c.st[n] -= 1;
    c.tmp = c.tmp.map(t => [t[0], t[1], t[2] - 1]).filter(t => t[2] > 0);
    if (c.reflect[0] > 0) c.reflect = [c.reflect[0] - 1, c.reflect[1]];
    if (c.spiky[0] > 0) c.spiky = [c.spiky[0] - 1, c.spiky[1]];
  }

  run() {
    const [A, B] = this.sides;
    for (const sd of this.sides) this.enter(sd, sd.lineup[0]);
    for (const sd of this.sides) this.spotlight(sd);
    let bar = 0, last = null, turns = 0;
    if (this.rec) { this.say('Both sides reveal their lineups; Pokemon enter in set order'); this.snap(0, null, 0); }
    for (;;) {
      turns += 1; this.nrounds = turns / 2; this.tn = turns;
      if (turns > this.max_rounds * 2) return this.result(null, false, true);
      const a = A.active, b = B.active;
      let mover;
      if (bar > 0) mover = A;
      else if (bar < 0) mover = B;
      else if (last === null) {
        const sa = a.eff('spd'), sb = b.eff('spd');
        mover = sa > sb ? A : sb > sa ? B : (this.rng.random() < .5 ? A : B);
      } else mover = last === A ? B : A;
      const me = mover.active, foe = this.sides[1 - mover.idx].active;
      const cost = foe.eff('spd');
      me.protect = false;
      this.cur = { mover: mover.idx };
      if (me.st.sleep > 0 || me.st.freeze > 0) {
        this.say(`${me.name} skips`);
        me.st.sleep = Math.max(0, me.st.sleep - 1); me.st.freeze = Math.max(0, me.st.freeze - 1);
      } else { this.act(me, foe); this.acting = null; }
      this.end_turn(me, foe);
      bar += mover === A ? -cost : cost;
      last = mover;
      if (this.nrounds > 25 && me.hp > 0) {
        const od = 1 + Math.floor((this.nrounds - 25) / 5);
        me.hp -= od; this.say(`Overtime: ${me.name} takes ${od} true damage`);
      }
      for (const sd0 of this.sides) {
        const a0 = sd0.active;
        if (a0.hp <= 0 && (a0.fl.revive || a0.rhalf) && !a0.revived) {
          a0.revived = true; a0.hp = a0.fl.revive ? a0.maxhp : Math.max(1, Math.floor(a0.maxhp / 2));
          if (a0.fl.revive >= 2) sd0.carry.shield += 4;
          this.say(`${a0.name} is revived`);
          continue;
        }
        if (a0.hp <= 0) this.say(`${a0.name} faints`);
      }
      const dead = this.sides.filter(sd => sd.active.hp <= 0);
      for (const sd of dead) {
        sd.fallen += 1; const d = sd.active;
        if (d.types.has('FIELD')) sd.field_ko += 1;
        if (d.fl.rusted) sd.carry.atk += 1;
        if (d.fl.gracidea) sd.carry.spd += 1;
        if (d.fl.spelltag) { const o = this.sides[1 - sd.idx].active; if (o && o.hp > 0) o.hp -= 2; }
        if (d.lv('FLORA')) {
          const l = d.lv('FLORA'); sd.carry.maxhp += [3, 4, 4, 5][l - 1];
          if (l >= 3) sd.carry.atk += 1;
          if (l === 4) sd.carry.spd += 1;
        }
      }
      if (dead.length) {
        const lost = dead.filter(sd => !sd.lineup.length);
        if (lost.length === 2) return this.result(null, true);
        if (lost.length) return this.result(lost[0]);
        for (const sd of dead) {
          this.enter(sd, sd.lineup[0]);
          while (sd.active.hp <= 0) {
            sd.fallen += 1;
            if (!sd.lineup.length) return this.result(sd);
            this.enter(sd, sd.lineup[0]);
          }
        }
      }
      if (this.rec) this.snap(turns, mover.idx, bar);
    }
  }

  result(loser, draw, timeout) {
    if (this.rec) {
      this.say('Battle over: ' + (draw ? 'draw' : timeout ? 'time limit' : `side ${1 - loser.idx} wins`));
      this.snap(Math.trunc(this.nrounds * 2), null, 0);
    }
    const [A, B] = this.sides; let w;
    if (timeout) {
      const ta = A.lineup.reduce((x, c) => x + c.hp, 0) + Math.max(0, A.active.hp), tb = B.lineup.reduce((x, c) => x + c.hp, 0) + Math.max(0, B.active.hp);
      if (ta === tb) return { winner: null, left: 0, rounds: this.nrounds, timeout: true };
      w = ta > tb ? A : B;
    } else if (draw) return { winner: null, left: 0, rounds: this.nrounds, timeout: false };
    else w = loser === A ? B : A;
    const left = w.lineup.length + (w.active.hp > 0 ? 1 : 0);
    return { winner: w.idx, left, rounds: this.nrounds, timeout: !!timeout };
  }
}

const api = { Duel, BCard, makeRng, DATA, ITEMS, SYN_TH, level_of, pyround, NEG };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.PACEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
