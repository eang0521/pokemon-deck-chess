/* PAC digital — game rules: decks, shop, economy, picks, hatch, duels, scoring. */
(function (root) {
'use strict';
const E = (typeof PACEngine !== 'undefined') ? PACEngine : require('./engine.js');
const { Duel, BCard, makeRng, DATA, ITEMS, level_of } = E;

const TIERS = ['I', 'II', 'III', 'IV', 'V'];
const GATE = { I: 1, II: 3, III: 4, IV: 5, V: 6 };
const XP_CUM = { 2: 0, 3: 2, 4: 6, 5: 14, 6: 30, 7: 56, 8: 94 };
const MAX_LEVEL = 8;
const TRADE = { I: 0, II: 2, III: 4, IV: 7, V: 14 };
const bonusOf = r => r <= 3 ? 0 : r <= 6 ? 1 : r <= 9 ? 2 : 3;
const PICKS = { 1: { key: 'starter', label: 'Starter' }, 2: { key: 'II', bundle: true, label: 'Additional Tier II' }, 5: { key: 'III', bundle: true, label: 'Additional Tier III' }, 6: { key: 'unique', label: 'Unique' },
  8: { key: 'IV', bundle: true, label: 'Additional Tier IV' }, 9: { key: 'legendary', label: 'Legendary' } };
const levelFromXp = xp => { let l = 2; for (let k = 3; k <= MAX_LEVEL; k++) if (xp >= XP_CUM[k]) l = k; return l; };
const isUnholdable = key => !!ITEMS[key].flags.unholdable;
const NAME_TYPES = DATA.syn_th;

class Game {
  constructor(seed, opts) {
    opts = opts || {};
    this.seed = seed >>> 0; this.rng = makeRng(this.seed);
    this.uid = 1; this.round = 0; this.phase = 'setup'; this.log = []; this.history = [];
    this.specs = DATA.cards;
    const mk = spec => ({ uid: this.uid++, spec, items: [] });
    this.deck = { I: [], II: [], III: [], IV: [], V: [] }; this.picks = { I: [], II: [], III: [], IV: [], V: [], unique: [], legendary: [] }; this.hatch = { II: [], III: [], IV: [] };
    this.fam = {};
    for (const s of this.specs) {
      (this.fam[s.family] = this.fam[s.family] || []).push(s);
      if (s.pool === 'core') this.deck[s.tier].push(mk(s));
      else if (s.pool === 'add') this.picks[s.tier].push(mk(s));
      else if (s.pool === 'unique') this.picks.unique.push(mk(s));
      else if (s.pool === 'legendary') this.picks.legendary.push(mk(s));
      else if (s.pool === 'hatch') this.hatch[s.tier].push(mk(s));
    }
    for (const k in this.deck) this.rng.shuffle(this.deck[k]);
    for (const k in this.picks) this.rng.shuffle(this.picks[k]);
    for (const k in this.hatch) this.rng.shuffle(this.hatch[k]);
    this.ideck = [];
    for (const it of DATA.itemdeck) for (let i = 0; i < it.copies; i++) this.ideck.push({ uid: this.uid++, key: it.key, tier: it.tier, price: it.price, text: it.text, chips: it.chips });
    this.rng.shuffle(this.ideck);
    this.row = { I: [null, null, null], II: [null, null, null], III: [null, null, null], IV: [null, null, null], V: [null, null, null] };
    for (const t of TIERS) for (let i = 0; i < 3; i++) this.row[t][i] = this.draw(t);
    this.irow = [null, null, null, null];
    this.discard = { cards: [], items: [] }; // out of play for the rest of the game
    for (let i = 0; i < 4; i++) this.irow[i] = this.idraw();
    this.players = [];
    const defs = opts.players || [];
    for (let i = 0; i < 8; i++) {
      const d = defs[i] || {};
      this.players.push({ idx: i, name: d.name || ('Player ' + (i + 1)), bot: i !== (opts.human === undefined ? 0 : opts.human), persona: d.persona || null, gold: 5, xp: 0, level: 2,
        cards: [], order: [], inv: [], points: 20, streak: 0, wins: 0, losses: 0, draws: 0, inc: null, deal: null, stats: { evolve: 0, bought: 0, items: 0, picks: 0, hatch: 0, interest: 0, streakGold: 0, kos: 0 }, last: null, hist: [20] });
    }
    this.human = opts.human === undefined ? 0 : opts.human;
    this.shop = null; this.pendingPick = null; this.results = null;
  }

  // ---------- decks ----------
  draw(t) {
    if (this.deck[t].length) return this.deck[t].pop();
    if (this.picks[t] && this.picks[t].length) return this.picks[t].pop();
    return null;
  }
  idraw() { return this.ideck.length ? this.ideck.pop() : null; }
  idrawStarter(tier = 'I') {
    // topmost item of the given tier that a Pokemon can hold (gems can't be held)
    for (let i = this.ideck.length - 1; i >= 0; i--) { const it = this.ideck[i]; if (it.tier === tier && !isUnholdable(it.key)) return this.ideck.splice(i, 1)[0]; }
    return null;
  }
  returnCard(c, owner) {
    if (owner) { for (const it of c.items) owner.inv.push(it); }
    c.items = [];
    const s = c.spec;
    if (s.pool === 'core') this.deck[s.tier].unshift(c);
    else if (s.pool === 'add') this.picks[s.tier].unshift(c);
    else if (s.pool === 'unique') this.picks.unique.unshift(c);
    else if (s.pool === 'legendary') this.picks.legendary.unshift(c);
    else if (s.pool === 'hatch') this.hatch[s.tier].unshift(c);
  }
  returnItem(it) { this.ideck.unshift(it); }
  say(msg, kind) { this.log.push({ r: this.round, msg, kind: kind || '' }); }

  // ---------- player helpers ----------
  P(i) { return this.players[i]; }
  cardOf(p, uid) { return p.cards.find(c => c.uid === uid); }
  itemOf(p, uid) { return p.inv.find(i => i.uid === uid); }
  lineupCards(p) { return p.order.map(u => this.cardOf(p, u)).filter(Boolean); }
  benchCards(p) { const s = new Set(p.order); return p.cards.filter(c => !s.has(c.uid)); }
  hasBow(c) { return c.items.some(i => ITEMS[i.key].flags.slot); }
  lineupCap(p) { return p.level + this.lineupCards(p).filter(c => this.hasBow(c)).length; }
  lineupCount(p) { return this.lineupCards(p).filter(c => !this.hasBow(c)).length; }
  canAddToLineup(p, c) { return this.hasBow(c) || this.lineupCount(p) < p.level; }
  addCard(p, c, silent) {
    p.cards.push(c);
    if (this.canAddToLineup(p, c)) p.order.push(c.uid);
    return c;
  }
  removeCard(p, c) { p.cards = p.cards.filter(x => x !== c); p.order = p.order.filter(u => u !== c.uid); }
  evolveTargets(p, h) {
    // owned cards the shop card h can evolve (same family, higher value, core/additional shop cards)
    if (!h || h.spec.pool === 'hatch') return [];
    if (GATE[h.spec.tier] > p.level) return [];
    return p.cards.filter(c => c.spec.family === h.spec.family && h.spec.value > c.spec.value && c.spec.pool !== 'hatch' && c.spec.price > 0);
  }
  setLineup(p, uids) {
    // uids: ordered list of card uids to field. returns {ok,err}
    const seen = new Set(); const cs = [];
    for (const u of uids) { const c = this.cardOf(p, u); if (!c || seen.has(u)) continue; seen.add(u); cs.push(c); }
    const normal = cs.filter(c => !this.hasBow(c)).length;
    if (normal > p.level) return { ok: false, err: `Your lineup holds ${p.level} Pokemon at level ${p.level}.` };
    p.order = cs.map(c => c.uid);
    return { ok: true };
  }
  attachItem(p, itemUid, cardUid) {
    const it = this.itemOf(p, itemUid), c = this.cardOf(p, cardUid);
    if (!it || !c) return { ok: false, err: 'Not found.' };
    if (isUnholdable(it.key)) return { ok: false, err: 'That item cannot be held: it works from beside your lineup.' };
    if (c.items.length >= 3) return { ok: false, err: 'A Pokemon holds at most 3 items.' };
    if (ITEMS[it.key].flags.evo_only && !this.canEvolveFurther(c)) return { ok: false, err: 'Only a Pokemon that can still evolve can hold this.' };
    p.inv = p.inv.filter(x => x !== it); c.items.push(it);
    return { ok: true };
  }
  canEvolveFurther(c) { return (this.fam[c.spec.family] || []).some(h => h.value > c.spec.value && h.pool !== 'hatch' && h.price > 0); }
  detachItem(p, itemUid) {
    for (const c of p.cards) {
      const it = c.items.find(i => i.uid === itemUid);
      if (it) { c.items = c.items.filter(i => i !== it); p.inv.push(it); return { ok: true }; }
    }
    return { ok: false, err: 'Not found.' };
  }
  // ---------- economy ----------
  streakGold(p) { const a = Math.abs(p.streak); return a < 2 ? 0 : a === 2 ? 1 : a === 3 ? 2 : 3; }
  interest(p) { return Math.min(3, Math.floor(p.gold / 5)); }
  addXp(p, x) {
    p.xp += x; const old = p.level; p.level = levelFromXp(p.xp);
    if (p.level > old) { this.autoFill(p); return true; }
    return false;
  }
  autoFill(p) {
    // fill free lineup slots with the best benched cards (the human can rearrange afterwards)
    const bench = this.benchCards(p).sort((a, b) => b.spec.value - a.spec.value);
    for (const c of bench) { if (this.canAddToLineup(p, c)) p.order.push(c.uid); }
  }
  buyXp(p) {
    if (p.level >= MAX_LEVEL) return { ok: false, err: 'Already at the top level.' };
    if (p.gold < 4) return { ok: false, err: 'Buying XP costs 4 gold.' };
    p.gold -= 4; const up = this.addXp(p, 4); p.stats.xpbuy = (p.stats.xpbuy || 0) + 1;
    return { ok: true, levelUp: up };
  }

  // ---------- round start ----------
  beginRound() {
    this.round++;
    const r = this.round;
    for (const p of this.players) {
      const it = this.interest(p), sg = this.streakGold(p);
      const scale = p.inv.filter(i => ITEMS[i.key].flags.econ_income).length;
      p.inc = { base: 0, interest: 0, streak: 0, scale, xp: 0 };
      if (r > 1) {
        p.inc.base = 5; p.inc.interest = it; p.inc.streak = sg; p.inc.xp = 2;
        p.gold += 5 + it + sg; p.stats.interest += it; p.stats.streakGold += sg;
        this.addXp(p, 2);
      }
      p.gold += scale; p.deal = null;
    }
    this.pendingPick = null;
    const ev = PICKS[r];
    if (ev) {
      const order = this.shopOrder();
      if (ev.key === 'starter' || ev.bundle) {
        // each dealt card is bundled with a random holdable item of the same tier (never a gem)
        const tier = ev.key === 'starter' ? 'I' : ev.key;
        for (const p of order) {
          const deal = [], gifts = [];
          for (let i = 0; i < 3; i++) { const c = ev.key === 'starter' ? this.draw('I') : this.picks[ev.key].pop(); if (!c) break; deal.push(c); gifts.push(this.idrawStarter(tier)); }
          p.deal = deal; p.dealItems = gifts;
        }
      } else {
        const pool = this.picks[ev.key];
        for (const p of order) {
          const deal = [];
          for (let i = 0; i < 5 && pool.length; i++) deal.push(pool.pop());
          p.deal = deal; p.dealItems = null;
        }
      }
      this.pickEvent = ev;
      for (const p of this.players) if (p.bot && p.deal) this.botPick(p);
      const hp = this.players[this.human];
      if (hp && hp.deal) { this.phase = 'pick'; this.pendingPick = hp.deal; return; }
    }
    this.startShop();
  }
  botPick(p) {
    const deal = p.deal; if (!deal || !deal.length) return;
    const chosen = root.PACBots.pickChoice(this, p, deal);
    this.finishPick(p, chosen);
  }
  finishPick(p, c) {
    if (this.pickEvent.key === 'starter' || this.pickEvent.bundle) {
      const starter = this.pickEvent.key === 'starter', pool = starter ? null : this.picks[this.pickEvent.key];
      const gifts = p.dealItems || [], gift = gifts[p.deal.indexOf(c)];
      p.deal.forEach((d, i) => {
        if (d === c) return;
        if (starter) this.discard.cards.push(d); else pool.unshift(d);
        if (gifts[i]) this.discard.items.push(gifts[i]);
      });
      p.deal = null; p.dealItems = null; this.addCard(p, c);
      if (gift) p.inv.push(gift);
      if (!starter) p.stats.picks++;
      this.say(`${p.name} ${starter ? (p.name === 'You' ? 'start' : 'starts') : (p.name === 'You' ? 'pick' : 'picks')} ${c.spec.name}${gift ? ' + ' + ITEMS[gift.key].name : ''}`, 'pick');
      return;
    }
    const pool = this.picks[this.pickEvent.key];
    for (const d of p.deal) if (d !== c) pool.unshift(d);
    p.deal = null; this.addCard(p, c); p.stats.picks++;
    this.say(`${p.name} ${p.name === 'You' ? 'pick' : 'picks'} ${c.spec.name}`, 'pick');
  }
  humanPick(uid) {
    const p = this.players[this.human]; const c = (p.deal || []).find(x => x.uid === uid);
    if (!c) return { ok: false, err: 'Not one of the dealt cards.' };
    this.finishPick(p, c); this.pendingPick = null; this.startShop(); return { ok: true, card: c };
  }

  // ---------- shop ----------
  shopOrder() {
    return this.players.slice().map(p => [p, this.rng.random()]).sort((a, b) => (a[0].points - b[0].points) || (a[0].level - b[0].level) || (a[1] - b[1])).map(x => x[0]);
  }
  startShop() {
    this.phase = 'shop';
    this.shop = { order: this.shopOrder(), pos: 0, acted: false, sweeps: 1, humanDone: false };
    for (const p of this.players) if (p.bot) root.PACBots.free(this, p);
  }
  // advance one seat. returns {done} | {human:true, player} | {player, desc}
  stepShop() {
    const S = this.shop;
    if (S.pos >= S.order.length) {
      if (!S.acted) return { done: true };
      S.order = this.shopOrder(); S.pos = 0; S.acted = false; S.sweeps++;
    }
    const p = S.order[S.pos];
    if (!p.bot) return { human: true, player: p };
    root.PACBots.free(this, p);
    const desc = root.PACBots.turn(this, p);
    S.pos++;
    if (desc) { S.acted = true; this.say(desc, 'bot'); }
    return { player: p, desc: desc || null };
  }
  humanDid(acted) { const S = this.shop; if (acted) S.acted = true; S.pos++; }
  humanPass() { const S = this.shop; S.pos++; return { ok: true }; }
  tradeCredit(p, uids) {
    let credit = 0; const cards = [], items = [];
    for (const u of uids || []) {
      const c = this.cardOf(p, u);
      if (c) { cards.push(c); credit += c.spec.trade; continue; }
      const it = this.itemOf(p, u);
      if (it) { items.push(it); credit += TRADE[it.tier]; continue; }
      return null;
    }
    return { credit, cards, items };
  }
  applyTrade(p, tc) {
    for (const c of tc.cards) { this.removeCard(p, c); this.returnCard(c, p); }
    for (const it of tc.items) { p.inv = p.inv.filter(x => x !== it); this.returnItem(it); }
  }
  buyCard(p, tier, slot, tradeUids) {
    const c = this.row[tier][slot];
    if (!c) return { ok: false, err: 'That slot is empty.' };
    if (GATE[tier] > p.level) return { ok: false, err: `Tier ${tier} opens at level ${GATE[tier]}.` };
    const tc = this.tradeCredit(p, tradeUids); if (!tc) return { ok: false, err: 'Invalid trade-in.' };
    const cost = Math.max(0, c.spec.price - tc.credit);
    if (cost > p.gold) return { ok: false, err: `You need ${cost} gold.` };
    p.gold -= cost; this.applyTrade(p, tc);
    this.row[tier][slot] = this.draw(tier);
    this.addCard(p, c); p.stats.bought++;
    if (tc.cards.length + tc.items.length) p.stats.tradein = (p.stats.tradein || 0) + 1;
    return { ok: true, card: c, cost };
  }
  evolveCard(p, tier, slot, ownedUid) {
    const h = this.row[tier][slot], c = this.cardOf(p, ownedUid);
    if (!h || !c) return { ok: false, err: 'Not found.' };
    if (!this.evolveTargets(p, h).includes(c)) return { ok: false, err: 'That Pokemon cannot evolve into this card.' };
    const cost = Math.max(0, h.spec.price - c.spec.price);
    if (cost > p.gold) return { ok: false, err: `You need ${cost} gold.` };
    p.gold -= cost;
    this.row[tier][slot] = this.draw(tier);
    // new card takes the old one's place and its items
    h.items = c.items; c.items = [];
    p.cards[p.cards.indexOf(c)] = h; p.order = p.order.map(u => u === c.uid ? h.uid : u);
    this.returnCard(c, null);
    p.stats.evolve++;
    return { ok: true, card: h, cost, from: c };
  }
  churn(p, tier, slot) {
    const c = this.row[tier][slot];
    if (!c) return { ok: false, err: 'That slot is empty.' };
    if (p.gold < 1) return { ok: false, err: 'Churn costs 1 gold.' };
    p.gold -= 1;
    this.deck[tier].unshift(c);
    this.row[tier][slot] = this.draw(tier);
    return { ok: true, card: this.row[tier][slot] };
  }
  buyItem(p, slot, tradeUids) {
    const it = this.irow[slot];
    if (!it) return { ok: false, err: 'That slot is empty.' };
    if (GATE[it.tier] > p.level) return { ok: false, err: `Tier ${it.tier} opens at level ${GATE[it.tier]}.` };
    const tc = this.tradeCredit(p, tradeUids); if (!tc) return { ok: false, err: 'Invalid trade-in.' };
    const cost = Math.max(0, it.price - tc.credit);
    if (cost > p.gold) return { ok: false, err: `You need ${cost} gold.` };
    p.gold -= cost; this.applyTrade(p, tc);
    this.irow[slot] = this.idraw(); p.inv.push(it); p.stats.items++;
    return { ok: true, item: it, cost };
  }

  // ---------- scoring helpers ----------
  typeCounts(cards) {
    const cnt = {}, seen = new Set();
    for (const c of cards) for (const t of c.spec.types) { const k = t + '|' + c.spec.family; if (!seen.has(k)) { seen.add(k); cnt[t] = (cnt[t] || 0) + 1; } }
    return cnt;
  }
  gemKeys(p) { return p.inv.filter(i => ITEMS[i.key].flags.gem).map(i => i.key); }
  buildSide(p) {
    const cs = this.lineupCards(p);
    const bc = cs.map(c => new BCard(c.spec, c.items.map(i => i.key)));
    if (bc.length) bc[0].items = bc[0].items.concat(this.gemKeys(p));
    return { cards: cs, bc };
  }

  // ---------- battles ----------
  rawPairs(r) {
    const n = 8, seats = [0, 1, 2, 3, 4, 5, 6, 7];
    const k = (r - 1) % (n - 1);
    const rest = seats.slice(1);
    const rot = k ? [seats[0]].concat(rest.slice(-k), rest.slice(0, -k)) : seats.slice();
    const out = [];
    for (let i = 0; i < n / 2; i++) out.push([rot[i], rot[n - 1 - i]]);
    return out;
  }
  opponentOf(idx, r) { for (const [a, b] of this.rawPairs(r || this.round)) { if (a === idx) return this.players[b]; if (b === idx) return this.players[a]; } return null; }
  pairings(r) { return this.rawPairs(r).map(([a, b]) => this.rng.random() < .5 ? [b, a] : [a, b]); }
  humanReady() { return this.lineupCards(this.players[this.human]).length > 0; }
  runBattles() {
    const r = this.round; this.phase = 'duel';
    for (const p of this.players) if (p.bot) { root.PACBots.free(this, p); root.PACBots.arrange(this, p); }
    const out = []; let humanReplay = null;
    for (const [ia, ib] of this.pairings(r)) {
      const a = this.players[ia], b = this.players[ib];
      const sa = this.buildSide(a), sb = this.buildSide(b);
      const involvesHuman = (ia === this.human || ib === this.human);
      let res, duel = null;
      if (!sa.bc.length || !sb.bc.length) {
        res = { winner: !sa.bc.length && !sb.bc.length ? null : !sa.bc.length ? 1 : 0, left: Math.max(sa.bc.length, sb.bc.length), rounds: 0, forfeit: true };
      } else {
        duel = new Duel(sa.bc, sb.bc, makeRng((this.rng.random() * 4294967296) >>> 0), { rec: involvesHuman, streaks: [Math.max(0, -a.streak), Math.max(0, -b.streak)] });
        res = duel.run();
      }
      const rec = { r, a: ia, b: ib, winner: res.winner === null ? null : (res.winner === 0 ? ia : ib), left: res.left, rounds: res.rounds, pts: 0, hatch: [] };
      // post-battle: KO gold, food is used up
      for (const [pl, side, sd] of [[a, sa, 0], [b, sb, 1]]) {
        if (duel) for (const bcard of duel.orig[sd]) {
          const ko = bcard.kos || 0;
          pl.stats.kos += ko;
          if (ko && bcard.items.some(k => ITEMS[k].flags.econ_ko)) pl.gold += ko * Math.max(...bcard.items.map(k => ITEMS[k].flags.econ_ko || 0));
        }
        for (const c of side.cards) c.items = c.items.filter(i => ITEMS[i.key].cat !== 'Food');
      }
      if (res.winner === null) {
        a.streak = b.streak = 0; a.draws++; b.draws++; a.last = b.last = 'draw';
      } else {
        const w = res.winner === 0 ? a : b, l = res.winner === 0 ? b : a;
        const pts = res.left + bonusOf(r); rec.pts = pts;
        w.points += pts; l.points -= pts; w.wins++; l.losses++;
        w.streak = w.streak > 0 ? w.streak + 1 : 1; l.streak = l.streak < 0 ? l.streak - 1 : -1;
        w.last = 'win'; l.last = 'loss';
        // Baby synergy: a Hatch card after each lost duel
        const lc = this.lineupCards(l); const cnt = this.typeCounts(lc); const bl = level_of('BABY', cnt.BABY || 0);
        if (bl) {
          const tk = ['II', 'III', 'IV'][bl - 1]; const dk = this.hatch[tk];
          if (dk.length) { const hc = dk.pop(); this.addCard(l, hc); l.stats.hatch++; rec.hatch.push({ player: l.idx, card: hc }); }
        }
      }
      out.push(rec);
      if (involvesHuman && duel) {
        const meSide = ia === this.human ? 0 : 1;
        humanReplay = this.makeReplay(duel, a, b, res, meSide, r);
      }
    }
    for (const p of this.players) p.hist.push(p.points);
    this.results = { r, pairs: out, replay: humanReplay };
    this.history.push(this.results);
    this.phase = 'results';
    return this.results;
  }
  makeReplay(duel, a, b, res, meSide, r) {
    const side = i => ({ name: [a, b][i].name, idx: [a, b][i].idx, cards: duel.orig[i].map(c => ({ id: c.id, name: c.name, spec: c.spec, items: c.items_eff.slice(), syn: Object.assign({}, c.syn), types: Array.from(c.types), hp0: c.hp0, ab: c.abname })), light: duel.sides[i].light, gems: duel.sides[i].gems && Object.assign({}, duel.sides[i].gems) });
    return { r, sides: [side(0), side(1)], snaps: duel.snaps, result: res, me: meSide, bonus: bonusOf(r) };
  }
  endRound() {
    if (this.round >= 12) { this.phase = 'end'; return; }
    this.beginRound();
  }
  standings() {
    return this.players.slice().sort((x, y) => (y.points - x.points) || (y.wins - x.wins) || (y.gold - x.gold));
  }
}


// ---------- save / load ----------
Game.prototype.serialize = function () {
  const cards = new Map(), items = new Map();
  const addItem = it => { if (it) items.set(it.uid, it); return it ? it.uid : null; };
  const addCard = c => { if (!c) return null; cards.set(c.uid, { u: c.uid, s: c.spec.id, i: c.items.map(addItem) }); return c.uid; };
  const pl = this.players.map(p => ({ idx: p.idx, name: p.name, bot: p.bot, persona: p.persona, gold: p.gold, xp: p.xp, level: p.level, cards: p.cards.map(addCard), order: p.order.slice(), inv: p.inv.map(addItem),
    points: p.points, streak: p.streak, wins: p.wins, losses: p.losses, draws: p.draws, inc: p.inc, deal: p.deal ? p.deal.map(addCard) : null, dealItems: p.dealItems ? p.dealItems.map(addItem) : null, stats: p.stats, last: p.last, hist: p.hist, churned: p.churned || null }));
  const lists = o => { const r = {}; for (const k in o) r[k] = o[k].map(addCard); return r; };
  const data = { v: 1, seed: this.seed, rng: this.rng.getState(), uid: this.uid, round: this.round, phase: this.phase, human: this.human, log: this.log.slice(-120),
    players: pl, deck: lists(this.deck), picks: lists(this.picks), hatch: lists(this.hatch), row: Object.fromEntries(Object.keys(this.row).map(t => [t, this.row[t].map(addCard)])),
    irow: this.irow.map(addItem), ideck: this.ideck.map(addItem), discard: { cards: this.discard.cards.map(addCard), items: this.discard.items.map(addItem) }, pickEvent: this.pickEvent || null,
    shop: this.shop ? { order: this.shop.order.map(p => p.idx), pos: this.shop.pos, acted: this.shop.acted, sweeps: this.shop.sweeps } : null,
    pendingPick: this.pendingPick ? this.pendingPick.map(c => c.uid) : null };
  data.cards = Array.from(cards.values()); data.items = Array.from(items.values());
  return data;
};
Game.deserialize = function (d) {
  const g = new Game(d.seed, { players: d.players.map(p => ({ name: p.name, persona: p.persona })), human: d.human });
  g.rng.setState(d.rng); g.uid = d.uid; g.round = d.round; g.phase = d.phase; g.log = d.log || []; g.history = []; g.results = null;
  const items = new Map(d.items.map(i => [i.uid, i]));
  const cards = new Map(d.cards.map(c => [c.u, { uid: c.u, spec: g.specs[c.s], items: c.i.map(u => items.get(u)) }]));
  const C = u => u == null ? null : cards.get(u), I = u => u == null ? null : items.get(u);
  const lists = o => { const r = {}; for (const k in o) r[k] = o[k].map(C); return r; };
  g.deck = lists(d.deck); g.picks = lists(d.picks); g.hatch = lists(d.hatch);
  g.row = {}; for (const t in d.row) g.row[t] = d.row[t].map(C);
  g.irow = d.irow.map(I); g.ideck = d.ideck.map(I);
  g.discard = d.discard ? { cards: d.discard.cards.map(C), items: d.discard.items.map(I) } : { cards: [], items: [] };
  g.players = d.players.map(p => Object.assign({}, p, { cards: p.cards.map(C), inv: p.inv.map(I), deal: p.deal ? p.deal.map(C) : null, dealItems: p.dealItems ? p.dealItems.map(I) : null }));
  g.pickEvent = d.pickEvent;
  g.shop = d.shop ? { order: d.shop.order.map(i => g.players[i]), pos: d.shop.pos, acted: d.shop.acted, sweeps: d.shop.sweeps, humanDone: false } : null;
  g.pendingPick = d.pendingPick ? d.pendingPick.map(C) : null;
  g.human = d.human;
  return g;
};

const api = { Game, TIERS, GATE, XP_CUM, TRADE, PICKS, MAX_LEVEL, bonusOf, levelFromXp, isUnholdable };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.PACGame = api;
})(typeof window !== 'undefined' ? window : globalThis);
