// End-to-end test over real WebSockets against a running room server (Node or Cloudflare):
//   node tests/net_test.js ws://localhost:8787 [players]
// Players create/join a room, the host starts, everyone plays to the end; one player drops and rejoins mid-game.
const { load } = require('./load');
const { G } = load();
const WebSocket = require('../server/node_modules/ws');

const BASE = process.argv[2] || 'ws://localhost:8787';
const N = +(process.argv[3] || 2);
const code = 'T' + Math.random().toString(36).slice(2, 5).toUpperCase().replace(/[^A-Z0-9]/g, 'X');
let fails = 0; const fail = (...m) => { fails++; console.log('  FAIL', ...m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

class Player {
  constructor(name, create) { this.name = name; this.create = create; this.id = 0; this.state = null; this.lobby = null; this.token = null; this.replays = 0; this.acts = 0; this.errors = []; }
  connect() {
    return new Promise(res => {
      this.ws = new WebSocket(`${BASE}/room/${code}`);
      this.ws.on('open', () => { this.ws.send(JSON.stringify({ t: 'hello', name: this.name, create: this.create, token: this.token || undefined })); this.create = false; res(); });
      this.ws.on('message', d => this.receive(JSON.parse(d.toString())));
      this.ws.on('error', e => this.errors.push(String(e.message)));
    });
  }
  receive(m) {
    if (m.t === 'joined') this.token = m.token;
    else if (m.t === 'lobby') this.lobby = m;
    else if (m.t === 'replay') this.replays++;
    else if (m.t === 'error') this.errors.push(m.msg);
    else if (m.t === 'res') { this.pending = false; if (!m.ok && /buy/.test((this.last || {}).t)) this.act({ t: 'pass' }); }
    else if (m.t === 'state') { this.state = m; this.think(); }
  }
  think() {
    const s = this.state; if (this.pending || this.ws.readyState !== 1) return;
    const seat = s.view.seat; if (!s.wait.seats.includes(seat)) return;
    const g = G.Game.deserialize(s.view), p = g.players[seat];
    let a = null;
    if (g.phase === 'pick') a = { t: 'pick', uid: p.deal[0].uid };
    else if (g.phase === 'results') a = { t: 'ready' };
    else if (g.phase === 'shop') {
      const o = []; for (const t of G.TIERS) if (G.GATE[t] <= p.level) g.row[t].forEach((c, sl) => { if (c && c.spec.price <= p.gold) o.push({ t: 'buyCard', tier: t, slot: sl }); });
      a = o.length && Math.random() < 0.6 ? o[Math.floor(Math.random() * o.length)] : { t: 'pass' };
    }
    if (a) { this.pending = true; this.last = a; this.acts++; this.ws.send(JSON.stringify({ t: 'act', a, id: ++this.id })); }
  }
  phase() { return this.state && this.state.view.phase; }
}
async function until(fn, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (fn()) return true; await sleep(50); } fail('timeout:', what); return false; }

(async () => {
  console.log(`server ${BASE}, room ${code}, ${N} players`);
  const ps = Array.from({ length: N }, (_, i) => new Player('Net' + i, i === 0));
  await ps[0].connect(); await until(() => ps[0].lobby, 5000, 'lobby');
  for (const p of ps.slice(1)) await p.connect();
  await until(() => ps[0].lobby && ps[0].lobby.members.length === N, 5000, 'all in lobby');
  ps[0].ws.send(JSON.stringify({ t: 'settings', turn: 0 })); ps[0].ws.send(JSON.stringify({ t: 'start' }));
  await until(() => ps.every(p => p.state), 10000, 'game started');
  const t0 = Date.now();
  if (N > 1) {
    await until(() => ps[1].state && ps[1].state.view.round >= 3, 300000, 'round 3');
    console.log(`  round 3 after ${Math.round((Date.now() - t0) / 1000)}s; ${ps[1].name} drops and rejoins`);
    ps[1].ws.close(); await sleep(1500); ps[1].pending = false; await ps[1].connect();
    await until(() => ps[1].state && !ps[1].state.view.players[ps[1].state.view.seat].away, 10000, 'rejoined');
  }
  await until(() => ps.every(p => p.phase() === 'end'), 900000, 'game end');
  const g = G.Game.deserialize(ps[0].state.view);
  if (g.round !== 12) fail('ended at round', g.round);
  if (g.players.reduce((a, p) => a + p.points, 0) !== 160) fail('points');
  console.log(`  finished in ${Math.round((Date.now() - t0) / 1000)}s; acts ${ps.map(p => p.acts).join('/')}; replays ${ps.map(p => p.replays).join('/')}; errors ${ps.flatMap(p => p.errors).length}`);
  for (const p of ps) p.ws.close();
  console.log(fails ? `FAILED: ${fails}` : 'ALL OK');
  process.exit(fails ? 1 : 0);
})();
