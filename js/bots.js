/* PAC digital — bots. Seven personalities, simple greedy value-for-gold logic. They never look at another player's lineup or gold. */
(function (root) {
'use strict';
const E = (typeof PACEngine !== 'undefined') ? PACEngine : require('./engine.js');
const { DATA, ITEMS, SYN_TH, level_of } = E;
const G = (typeof PACGame !== 'undefined') ? PACGame : require('./game.js');
const { GATE, TRADE } = G;

const PERSONAS = [
  { key: 'banker', name: 'Brock', title: 'The Banker', blurb: 'Banks gold for interest. Buys only clear upgrades.', floor: 10, xpKeep: 15, buyGain: 1.6, evoGain: 1.0, bank: 6, order: 'tank', maxLevel: 7 },
  { key: 'leveler', name: 'Misty', title: 'The Leveler', blurb: 'Buys XP hard to reach the high tiers early.', floor: 2, xpKeep: 7, buyGain: 1.2, evoGain: 1.0, order: 'strong', maxLevel: 7, levelPush: true },
  { key: 'specialist', name: 'Erika', title: 'Type Specialist', blurb: 'Picks two favorite types and builds around them.', floor: 4, xpKeep: 8, buyGain: 1.0, evoGain: 1.0, order: 'strong', maxLevel: 7, favBonus: 3.5 },
  { key: 'evolver', name: 'Surge', title: 'The Evolver', blurb: 'Loves evolution lines and churns the shop for them.', floor: 3, xpKeep: 8, buyGain: 1.0, evoGain: 0.3, order: 'fast', maxLevel: 7, evoBonus: 1.8, churn: true },
  { key: 'hoarder', name: 'Sabrina', title: 'Item Hoarder', blurb: 'Spends on items first and loads up her best Pokemon.', floor: 4, xpKeep: 10, buyGain: 1.0, evoGain: 1.0, order: 'closer', maxLevel: 7, itemFirst: true },
  { key: 'bruiser', name: 'Koga', title: 'The Bruiser', blurb: 'Straight value for gold, strongest Pokemon first.', floor: 1, xpKeep: 10, buyGain: 1.0, evoGain: 1.0, order: 'strong', maxLevel: 7 },
  { key: 'gambler', name: 'Blue', title: 'The Gambler', blurb: 'Banks when ahead, goes all in when behind.', floor: 6, xpKeep: 10, buyGain: 1.0, evoGain: 1.0, order: 'random', maxLevel: 7, adaptive: true },
];

function pers(p) { return p.persona || PERSONAS[5]; }
function typesCount(specs) {
  const cnt = {}, seen = new Set();
  for (const s of specs) for (const t of s.types) { const k = t + '|' + s.family; if (!seen.has(k)) { seen.add(k); cnt[t] = (cnt[t] || 0) + 1; } }
  return cnt;
}
function stage(g, spec) { return (g.fam[spec.family] || []).some(h => h.value > spec.value && h.pool !== 'hatch' && h.price > 0); }
function scoreSpec(g, p, spec, roster) {
  const ps = pers(p);
  let syn = 0; const cnt = typesCount(roster);
  for (const t of spec.types) {
    const n = cnt[t] || 0; const th = SYN_TH[t] || [2, 3, 4]; const nxt = th.filter(x => x > n);
    syn += (n ? 1 : 0) + ((nxt.length && n + 1 >= nxt[0]) ? 2 : 0);
    if (ps.fav && ps.fav.includes(t)) syn += ps.favBonus || 3;
  }
  let sc = spec.value + 1.2 * syn;
  if (ps.evoBonus && stage(g, spec)) sc += ps.evoBonus;
  return sc;
}
function cardScore(g, p, c, roster) { return scoreSpec(g, p, c.spec, roster.map(x => x.spec)); }
function lost(p, cost) { return Math.min(3, Math.floor(p.gold / 5)) - Math.min(3, Math.floor(Math.max(0, p.gold - cost) / 5)); }
function floorOf(g, p) {
  const ps = pers(p);
  if (g.round >= 11) return 0;
  if (!ps.adaptive) return ps.floor;
  const pts = g.players.map(x => x.points).sort((a, b) => a - b);
  const med = pts[4];
  return p.points < med - 3 ? 0 : p.points > med + 3 ? 10 : 5;
}

// lineup quality: raw value plus how many synergy levels the lineup activates
function effTypes(c, extra) { const s = new Set(c.spec.types); for (const i of c.items) { const t = ITEMS[i.key].flags.type; if (t) s.add(t); } if (extra) s.add(extra); return s; }
function lineupScore(g, p, cards, gems, extraTypeFor) {
  const cnt = {}, seen = new Set();
  const types = cards.map(c => effTypes(c, extraTypeFor && extraTypeFor.card === c ? extraTypeFor.type : null));
  cards.forEach((c, i) => { for (const t of types[i]) { const k = t + '|' + c.spec.family; if (!seen.has(k)) { seen.add(k); cnt[t] = (cnt[t] || 0) + 1; } } });
  for (const gk of gems || []) { const t = ITEMS[gk].flags.gem; cnt[t] = (cnt[t] || 0) + 1; }
  let s = 0;
  cards.forEach((c, i) => {
    s += c.spec.value;
    for (const t of types[i]) s += 1.8 * level_of(t, cnt[t] || 0);
    const ps = pers(p);
    if (ps.fav) for (const t of types[i]) if (ps.fav.includes(t)) s += 0.5;
  });
  return s;
}

// ---------- free actions: XP, lineup, items ----------
function xp(g, p) {
  const ps = pers(p); const keep = g.round >= 11 ? 0 : ps.adaptive ? (floorOf(g, p) + 4) : ps.xpKeep;
  let guard = 0;
  while (p.level < ps.maxLevel && guard++ < 20) {
    const need = p.cards.length < p.level;
    const ok = p.level >= 4 ? p.gold >= keep + 4 : (p.gold >= 4 && !need);
    if (!ok) break;
    if (p.level <= 3 && need) break;
    g.buyXp(p);
  }
}
function arrange(g, p) {
  const ps = pers(p);
  const all = p.cards.slice();
  if (!all.length) { p.order = []; return; }
  const gems = g.gemKeys(p);
  const cap = p.level;
  let chosen = all.slice().sort((a, b) => b.spec.value - a.spec.value).slice(0, cap);
  let bench = all.filter(c => !chosen.includes(c));
  let best = lineupScore(g, p, chosen, gems);
  for (let pass = 0; pass < 3; pass++) {
    let improved = false;
    for (let i = 0; i < chosen.length; i++) for (let j = 0; j < bench.length; j++) {
      const t = chosen.slice(); t[i] = bench[j];
      const s = lineupScore(g, p, t, gems);
      if (s > best + 1e-9) { best = s; const out = chosen[i]; chosen = t; bench[j] = out; improved = true; }
    }
    if (!improved) break;
  }
  // gold bow holders add a slot
  let extra = chosen.filter(c => g.hasBow(c)).length;
  if (extra) { const rest = bench.filter(c => !g.hasBow(c)).sort((a, b) => b.spec.value - a.spec.value); while (extra-- > 0 && rest.length) chosen.push(rest.shift()); }
  const hp = c => c.spec.hp + 2 * c.spec.df + 2 * c.spec.sdf;
  const key = { strong: c => -c.spec.value, tank: c => -hp(c), fast: c => -c.spec.spd, closer: c => c.spec.value }[ps.order];
  if (key) chosen.sort((a, b) => key(a) - key(b));
  else g.rng.shuffle(chosen);
  p.order = chosen.map(c => c.uid);
}
function attach(g, p) {
  // move items off the bench, then hand out loose items
  const inLine = () => g.lineupCards(p);
  for (const c of g.benchCards(p)) for (const it of c.items.slice()) g.detachItem(p, it.uid);
  const gems = g.gemKeys(p);
  const loose = p.inv.filter(i => !G.isUnholdable(i.key));
  for (const it of loose) {
    const fl = ITEMS[it.key].flags;
    const ok = c => c.items.length < 3 && !c.items.some(x => x.key === it.key) && (!fl.evo_only || g.canEvolveFurther(c));
    let pool = inLine().filter(ok);
    if (!pool.length) pool = g.benchCards(p).filter(ok);
    if (!pool.length) continue;
    let target;
    if (fl.type) {
      let bs = -1e9;
      for (const c of pool) { const s = lineupScore(g, p, inLine(), gems, { card: c, type: fl.type }) + (inLine().includes(c) ? 0 : -50) + g.rng.random() * 0.01; if (s > bs) { bs = s; target = c; } }
    } else if (fl.slot) {
      target = pool.slice().sort((a, b) => b.spec.value - a.spec.value)[0];
    } else {
      target = pool.slice().sort((a, b) => (b.spec.value - a.spec.value) + (a.items.length - b.items.length) * 1.0)[0];
    }
    g.attachItem(p, it.uid, target.uid);
  }
}
function free(g, p) { xp(g, p); arrange(g, p); attach(g, p); if (g.lineupCards(p).length) { /* re-sort once items exist */ } }

// ---------- one shop action ----------
function evoStep(g, p) {
  const ps = pers(p);
  const cs = p.cards.slice().sort((a, b) => b.spec.value - a.spec.value);
  let best = null;
  for (const c of cs) for (const t of G.TIERS) for (let s = 0; s < g.row[t].length; s++) {
    const h = g.row[t][s]; if (!h) continue;
    if (!g.evolveTargets(p, h).includes(c)) continue;
    const cost = Math.max(0, h.spec.price - c.spec.price);
    const gain = h.spec.value - c.spec.value;
    if (cost > p.gold || gain < ps.evoGain) continue;
    if (ps.bank && g.round < 11 && lost(p, cost) > 0 && gain < 1.0 + 2 * lost(p, cost)) continue;
    if (!best || gain > best.gain) best = { c, t, s, h, cost, gain };
  }
  if (best) { const r = g.evolveCard(p, best.t, best.s, best.c.uid); if (r.ok) return `${p.name} evolves ${best.c.spec.name} into ${best.h.spec.name}`; }
  return null;
}
function cardStep(g, p) {
  const ps = pers(p); const floor = floorOf(g, p);
  const cap = p.level + 4; const need = p.cards.length < p.level;
  const cands = [];
  for (const t of G.TIERS) { if (GATE[t] > p.level) continue; g.row[t].forEach((c, s) => { if (c) cands.push({ c, t, s }); }); }
  if (!cands.length) return null;
  const weakest = p.cards.length ? p.cards.reduce((a, b) => cardScore(g, p, a, p.cards) <= cardScore(g, p, b, p.cards) ? a : b) : null;
  let best = null, bs = -1e9;
  for (const { c, t, s } of cands) {
    const sc = scoreSpec(g, p, c.spec, p.cards.map(x => x.spec).concat([c.spec]));
    if (need || p.cards.length < cap) {
      const cost = c.spec.price; if (cost > p.gold) continue;
      if (!need && p.gold - cost < floor) continue;
      const gain = sc - (weakest && !need ? cardScore(g, p, weakest, p.cards) : 0);
      if (need || gain > ps.buyGain + (ps.bank && g.round < 11 ? ps.bank * lost(p, cost) : 0)) { if (gain > bs || (best === null && need)) { bs = gain; best = { c, t, s, out: null, cost }; } }
    } else if (weakest) {
      const cost = Math.max(0, c.spec.price - weakest.spec.trade); if (cost > p.gold) continue;
      const gain = sc - cardScore(g, p, weakest, p.cards);
      if (gain > ps.buyGain + 0.5 + (ps.bank && g.round < 11 ? ps.bank * lost(p, cost) : 0) && gain > bs) { bs = gain; best = { c, t, s, out: weakest, cost }; }
    }
  }
  if (!best && need) {
    const aff = cands.filter(x => x.c.spec.price <= p.gold);
    if (aff.length) { const x = aff.reduce((a, b) => scoreSpec(g, p, a.c.spec, p.cards.map(y => y.spec).concat([a.c.spec])) >= scoreSpec(g, p, b.c.spec, p.cards.map(y => y.spec).concat([b.c.spec])) ? a : b); best = { c: x.c, t: x.t, s: x.s, out: null, cost: x.c.spec.price }; }
  }
  if (!best) return null;
  const r = g.buyCard(p, best.t, best.s, best.out ? [best.out.uid] : []);
  if (!r.ok) return null;
  return `${p.name} buys ${best.c.spec.name}` + (best.out ? ` (trading in ${best.out.spec.name})` : '');
}
function itemStep(g, p) {
  const ps = pers(p); const floor = floorOf(g, p);
  if (p.gold < 2) return null;
  if (p.cards.length < p.level) return null;
  const gems = g.gemKeys(p);
  const lineup = g.lineupCards(p);
  const base = lineupScore(g, p, lineup, gems);
  let best = null, bw = 0;
  g.irow.forEach((it, s) => {
    if (!it || GATE[it.tier] > p.level) return;
    if (it.price > p.gold - (ps.itemFirst ? 0 : floor)) return;
    if (ps.bank && g.round < 11 && lost(p, it.price) > 0) return;
    const fl = ITEMS[it.key].flags; let w;
    if (fl.gem) { w = (lineupScore(g, p, lineup, gems.concat([it.key])) - base) * 4 - it.price * 0.3; }
    else if (fl.econ_income) w = (12 - g.round) * 0.7;
    else {
      const holders = p.cards.filter(c => c.items.length < 3 && !c.items.some(x => x.key === it.key) && (!fl.evo_only || g.canEvolveFurther(c)));
      if (!holders.length) return;
      w = it.price + g.rng.random() * 1.5;
      if (fl.type) { const hs = lineup.filter(c => c.items.length < 3 && !c.items.some(x => x.key === it.key)); let m = 0; for (const c of hs) m = Math.max(m, lineupScore(g, p, lineup, gems, { card: c, type: fl.type }) - base); w += m * 3; }
    }
    if (w > bw) { bw = w; best = s; }
  });
  if (best === null || bw < (ps.itemFirst ? 4 : 2.5)) return null;
  const it = g.irow[best];
  const r = g.buyItem(p, best, []);
  if (!r.ok) return null;
  return `${p.name} buys ${ITEMS[it.key].name}`;
}
function churnStep(g, p) {
  const ps = pers(p);
  if (!ps.churn || p.gold < 4 + floorOf(g, p)) return null;
  if (p.churned && p.churned.r === g.round && p.churned.n >= 3) return null;
  // find an owned card that has a stronger family member still in a deck
  for (const c of p.cards.slice().sort((a, b) => b.spec.value - a.spec.value)) {
    const ups = (g.fam[c.spec.family] || []).filter(h => h.value > c.spec.value && h.pool === 'core' && GATE[h.tier] <= p.level);
    if (!ups.length) continue;
    const tier = ups[0].tier;
    const slots = g.row[tier].map((x, i) => [x, i]).filter(([x]) => x && !g.evolveTargets(p, x).length);
    if (!slots.length) continue;
    const [, i] = slots[g.rng.int(slots.length)];
    const r = g.churn(p, tier, i);
    if (r.ok) { p.churned = { r: g.round, n: (p.churned && p.churned.r === g.round ? p.churned.n : 0) + 1 }; return `${p.name} churns a Tier ${tier} card`; }
  }
  return null;
}
function turn(g, p) {
  const ps = pers(p);
  let d = evoStep(g, p);
  if (d) return d;
  if (ps.itemFirst) { d = itemStep(g, p); if (d) return d; }
  d = cardStep(g, p); if (d) return d;
  d = itemStep(g, p); if (d) return d;
  d = churnStep(g, p); if (d) return d;
  return null;
}
function pickChoice(g, p, deal) {
  let best = null, bs = -1e9;
  for (const c of deal) {
    const s = scoreSpec(g, p, c.spec, p.cards.map(x => x.spec).concat([c.spec])) + g.rng.random() * 0.3;
    if (s > bs) { bs = s; best = c; }
  }
  return best;
}

const api = { PERSONAS, turn, free, arrange, attach, xp, pickChoice, lineupScore, scoreSpec };
if (typeof module !== 'undefined' && module.exports) { module.exports = api; globalThis.PACBots = api; } else root.PACBots = api;
})(typeof window !== 'undefined' ? window : globalThis);
