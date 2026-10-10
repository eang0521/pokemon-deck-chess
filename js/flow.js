/* PAC digital — table flow shared by the browser (solo / pass-and-play) and the room server (online):
   apply() validates and applies one seat's action, next() runs one automatic step (bots, battles, rounds)
   until a human is needed, waiting() says who that is, view() is what one seat is allowed to see. */
(function (root) {
'use strict';
const G = (typeof PACGame !== 'undefined') ? PACGame : require('./game.js');
const B = (typeof PACBots !== 'undefined') ? PACBots : require('./bots.js');
const E = (typeof PACEngine !== 'undefined') ? PACEngine : require('./engine.js');
const { GATE, TIERS, TRADE } = G;
const ITEMS = E.ITEMS;

// can this seat afford any shop action? (used for auto-pass)
function canDoAnything(g, p) {
  const credit = p.cards.reduce((a, c) => a + c.spec.trade, 0) + p.inv.reduce((a, i) => a + TRADE[i.tier], 0);
  if (p.gold >= 1) for (const t of TIERS) if (GATE[t] <= p.level && g.row[t].some(Boolean)) return true; // churn
  for (const t of TIERS) {
    if (GATE[t] > p.level) continue;
    for (const c of g.row[t]) {
      if (!c) continue;
      if (Math.max(0, c.spec.price - credit) <= p.gold) return true;
      for (const o of g.evolveTargets(p, c)) if (Math.max(0, c.spec.price - o.spec.price) <= p.gold) return true;
    }
  }
  for (const it of g.irow) if (it && GATE[it.tier] <= p.level && Math.max(0, it.price - credit) <= p.gold) return true;
  return false;
}

const FREE_PHASES = ['pick', 'shop', 'results'];
const bad = err => ({ ok: false, err });

// apply one action for one seat; returns { ok, err?, msg? } (msg is a toast for that seat)
function apply(g, seat, a) {
  const p = g.players[seat];
  if (!p || p.bot) return bad('That seat is not yours.');
  if (!a || typeof a.t !== 'string') return bad('Unknown action.');
  const myTurn = g.turnSeat() === seat;
  const needTurn = () => myTurn ? null : bad(g.phase === 'shop' ? 'It is not your turn.' : 'The shop is closed.');
  const needFree = () => FREE_PHASES.includes(g.phase) ? null : bad('Not right now.');
  let r;
  switch (a.t) {
    case 'pick': {
      r = g.humanPick(seat, +a.uid); if (!r.ok) return r;
      return { ok: true, msg: `You picked <b>${esc(r.card.spec.name)}</b>` };
    }
    case 'buyCard': {
      const e = needTurn(); if (e) return e;
      r = g.buyCard(p, a.tier, +a.slot, (a.trade || []).map(Number)); if (!r.ok) return r;
      g.say(`${p.name} buys ${r.card.spec.name}`, 'me', seat); g.humanDid(seat, true);
      return { ok: true, msg: `Bought <b>${esc(r.card.spec.name)}</b>` };
    }
    case 'buyItem': {
      const e = needTurn(); if (e) return e;
      r = g.buyItem(p, +a.slot, (a.trade || []).map(Number)); if (!r.ok) return r;
      g.say(`${p.name} buys ${ITEMS[r.item.key].name}`, 'me', seat); g.humanDid(seat, true);
      return { ok: true, msg: `Bought <b>${esc(ITEMS[r.item.key].name)}</b>` };
    }
    case 'evolve': {
      const e = needTurn(); if (e) return e;
      r = g.evolveCard(p, a.tier, +a.slot, +a.own); if (!r.ok) return r;
      g.say(`${p.name} evolves ${r.from.spec.name} into ${r.card.spec.name}`, 'me', seat); g.humanDid(seat, true);
      return { ok: true, msg: `<b>${esc(r.from.spec.name)}</b> evolves into <b>${esc(r.card.spec.name)}</b>!`, kind: 'good' };
    }
    case 'churn': {
      const e = needTurn(); if (e) return e;
      r = g.churn(p, a.tier, +a.slot); if (!r.ok) return r;
      g.say(`${p.name} churns the Tier ${a.tier} market`, 'me', seat); g.humanDid(seat, true);
      return { ok: true, msg: 'Churned a card (1 gold).' };
    }
    case 'pass': {
      const e = needTurn(); if (e) return e;
      r = g.humanPass(seat); if (!r.ok) return r;
      g.say(`${p.name} passes`, 'me', seat);
      return { ok: true };
    }
    case 'xp': {
      const e = needFree(); if (e) return e;
      r = g.buyXp(p); if (!r.ok) return r;
      return { ok: true, msg: r.levelUp ? `Level up! Lineup size is now ${p.level}.` : '+4 XP', kind: r.levelUp ? 'good' : '' };
    }
    case 'lineup': {
      const e = needFree(); if (e) return e;
      return g.setLineup(p, (a.order || []).map(Number));
    }
    case 'attach': {
      const e = needFree(); if (e) return e;
      return g.attachItem(p, +a.item, +a.card);
    }
    case 'detach': {
      const e = needFree(); if (e) return e;
      return g.detachItem(p, +a.item);
    }
    case 'auto': {
      const e = needFree(); if (e) return e;
      B.arrange(g, p); B.attach(g, p);
      return { ok: true, msg: 'Lineup and items arranged.', kind: 'dim' };
    }
    case 'ready': return g.markReady(seat);
    case 'autoPass': p.autoPass = !!a.on; return { ok: true };
  }
  return bad('Unknown action.');
}
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

// one automatic step; returns an event, or null when the table is waiting on a human
function next(g) {
  switch (g.phase) {
    case 'setup': g.beginRound(); return { t: 'round', r: g.round };
    case 'pick': {
      const p = g.waitingPick().find(q => g.isAuto(q));
      if (!p) return null;
      g.botPick(p); if (!g.waitingPick().length) g.startShop();
      return { t: 'botpick', seat: p.idx };
    }
    case 'shop': {
      const r = g.stepShop();
      if (r.done) { g.runBattles(); return { t: 'battles', r: g.round }; }
      if (r.human) {
        const p = r.player;
        if (p.autoPass && !canDoAnything(g, p)) { g.humanPass(p.idx); g.say(`${p.name} passes (nothing affordable)`, 'me', p.idx); return { t: 'autopass', seat: p.idx }; }
        return null;
      }
      return { t: 'bot', seat: r.player.idx, desc: r.desc };
    }
    case 'results':
      if (!g.allReady()) return null;
      g.endRound();
      return { t: 'round', r: g.round, end: g.phase === 'end' };
  }
  return null;
}

// who the table is waiting on: { phase, seats: [human seats that must act], turn: seat on turn or null }
function waiting(g) {
  const live = p => !g.isAuto(p);
  let seats = [];
  if (g.phase === 'pick') seats = g.waitingPick().filter(live).map(p => p.idx);
  else if (g.phase === 'shop') { const t = g.turnSeat(); if (t !== null && live(g.players[t])) seats = [t]; }
  else if (g.phase === 'results') seats = g.players.filter(p => live(p) && !p.ready).map(p => p.idx);
  return { phase: g.phase, seats, turn: g.phase === 'shop' ? g.turnSeat() : null };
}

// what one seat may see: no deck order, no RNG state, no other seat's pick offer, no other seat's replay
function view(g, seat) {
  const d = g.serialize();
  d.counts = { deck: {}, picks: {}, hatch: {}, ideck: g.ideck.length };
  for (const k of ['deck', 'picks', 'hatch']) for (const t in d[k]) { d.counts[k][t] = d[k][t].length; d[k][t] = []; }
  d.ideck = []; d.discard = { cards: [], items: [] }; delete d.rng;
  d.players.forEach((p, i) => { if (i !== seat) { p.dealN = p.deal ? p.deal.length : 0; p.deal = null; p.dealItems = null; } });
  if (d.results) d.results = { r: d.results.r, pairs: d.results.pairs };
  // keep only the cards and items the view still refers to
  const cu = new Set(), iu = new Set();
  const C = u => { if (u != null) cu.add(u); }, I = u => { if (u != null) iu.add(u); };
  for (const p of d.players) { p.cards.forEach(C); p.inv.forEach(I); (p.deal || []).forEach(C); (p.dealItems || []).forEach(I); }
  for (const t in d.row) d.row[t].forEach(C);
  d.irow.forEach(I);
  d.cards = d.cards.filter(c => cu.has(c.u));
  for (const c of d.cards) c.i.forEach(I);
  d.items = d.items.filter(i => iu.has(i.uid));
  d.seat = seat;
  return d;
}

// seat defs for a new table: humans take the first seats, bots (shuffled personalities) fill the rest
function seatDefs(names, seed) {
  const tmp = E.makeRng(seed ^ 0x9e3779b9);
  const personas = tmp.shuffle(B.PERSONAS.slice());
  const defs = names.slice(0, 8).map(name => ({ name, human: true }));
  for (let i = 0; defs.length < 8; i++) {
    const ps = Object.assign({}, personas[i % personas.length]);
    if (ps.key === 'specialist') { const ts = Object.keys(E.DATA.syn_th).filter(t => t !== 'BABY' && t !== 'AMORPHOUS'); ps.fav = [ts[tmp.int(ts.length)], ts[tmp.int(ts.length)]]; }
    // a bot never shares a name with a person at the table
    const taken = defs.some(d => d.name.toLowerCase() === ps.name.toLowerCase());
    defs.push({ name: taken ? ps.name + ' (bot)' : ps.name, persona: ps, human: false });
  }
  return defs;
}

const api = { apply, next, waiting, view, canDoAnything, seatDefs };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.PACFlow = api;
})(typeof window !== 'undefined' ? window : globalThis);
