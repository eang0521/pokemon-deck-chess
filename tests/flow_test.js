// Headless test of the multi-seat game core + flow: 1-8 human seats driven only through PACFlow.apply,
// random disconnects (away) and returns, and per-seat views. Run: node tests/flow_test.js [games]
const { load } = require('./load');
const { G, Flow, E } = load();

const games = +(process.argv[2] || 24);
let fails = 0; const fail = (...m) => { fails++; if (fails < 15) console.log('FAIL', ...m); };
let actions = 0, rejected = 0, maxView = 0, totalView = 0, views = 0;

function agentAct(g, seat, rng) {
  const p = g.players[seat];
  if (g.phase === 'pick') { const c = p.deal[Math.floor(rng() * p.deal.length)]; return { t: 'pick', uid: c.uid }; }
  if (g.phase === 'results') return { t: 'ready' };
  if (g.phase === 'shop') {
    if (rng() < 0.2 && p.gold >= 4 && p.level < 6) return { t: 'xp' };
    if (rng() < 0.15) return { t: 'auto' };
    const opts = [];
    for (const t of G.TIERS) if (G.GATE[t] <= p.level) g.row[t].forEach((c, s) => { if (c && c.spec.price <= p.gold) opts.push({ t: 'buyCard', tier: t, slot: s }); });
    g.irow.forEach((it, s) => { if (it && G.GATE[it.tier] <= p.level && it.price <= p.gold) opts.push({ t: 'buyItem', slot: s }); });
    if (opts.length && rng() < 0.7) return opts[Math.floor(rng() * opts.length)];
    return { t: 'pass' };
  }
  return null;
}

for (let gi = 0; gi < games; gi++) {
  const nh = (gi % 8) + 1;
  const rng = E.makeRng(1000 + gi).random.bind(E.makeRng(1000 + gi));
  const r2 = E.makeRng(77 + gi); const rnd = () => r2.random();
  const defs = []; for (let i = 0; i < 8; i++) defs.push(i < nh ? { name: 'H' + i, human: true } : { name: 'Bot' + i, persona: null });
  const g = new G.Game(5000 + gi, { players: defs });
  if (g.humans().length !== nh) fail('human count', nh, g.humans().length);
  let steps = 0;
  while (g.phase !== 'end') {
    if (++steps > 200000) { fail('stuck game', gi, g.phase, g.round); break; }
    // random disconnects / returns
    if (rnd() < 0.002) { const h = g.humans()[Math.floor(rnd() * nh)]; h.away = !h.away; }
    const ev = Flow.next(g);
    if (ev) continue;
    const w = Flow.waiting(g);
    if (!w.seats.length) { fail('waiting on nobody', gi, g.phase); break; }
    const seat = w.seats[Math.floor(rnd() * w.seats.length)];
    // a seat that is not waited on must be refused shop actions
    const other = g.humans().find(h => !w.seats.includes(h.idx));
    if (other && g.phase === 'shop') { const r = Flow.apply(g, other.idx, { t: 'pass' }); if (r.ok) fail('out-of-turn pass accepted', gi); }
    const a = agentAct(g, seat, rnd);
    const r = Flow.apply(g, seat, a); actions++;
    if (!r.ok) { rejected++; if (a.t === 'pick' || a.t === 'ready' || a.t === 'pass') fail('basic action rejected', a.t, r.err); else Flow.apply(g, seat, { t: 'pass' }); }
    // views: every so often, check one seat's view hides the right things and round-trips
    if (rnd() < 0.02) {
      const s = g.humans()[Math.floor(rnd() * nh)].idx;
      const v = Flow.view(g, s); const js = JSON.stringify(v); views++; totalView += js.length; maxView = Math.max(maxView, js.length);
      if (v.rng !== undefined || v.ideck.length || Object.values(v.deck).some(x => x.length)) fail('view leaks decks');
      v.players.forEach((q, i) => { if (i !== s && q.deal) fail('view leaks another deal'); });
      const cg = G.Game.deserialize(JSON.parse(js));
      if (cg.players[s].gold !== g.players[s].gold || cg.players[s].cards.length !== g.players[s].cards.length) fail('view round-trip mismatch');
    }
  }
  if (g.round !== 12) fail('game ended at round', g.round);
  // every human got a replay in their last round unless they forfeited
  const pts = g.players.reduce((a, p) => a + p.points, 0);
  if (pts !== 160) fail('points not conserved', pts);
}
console.log(`games ${games} | actions ${actions} (rejected buy/xp ${rejected}) | views ${views}, avg ${Math.round(totalView / Math.max(1, views) / 1024)}KB, max ${Math.round(maxView / 1024)}KB`);
console.log(fails ? `FAILED: ${fails}` : 'ALL OK');
process.exit(fails ? 1 : 0);
