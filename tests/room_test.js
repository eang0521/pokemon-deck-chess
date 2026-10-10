// Headless test of server/room.js with fake clients speaking the real message protocol (no network).
// Run: node tests/room_test.js
const { load } = require('./load');
const { G, Flow } = load();
const { Room } = require('../server/room.js');

let fails = 0; const fail = (...m) => { fails++; console.log('  FAIL', ...m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function makeIo(roomRef) {
  return {
    send(conn, obj) { if (!conn.closed) setImmediate(() => conn.receive(JSON.parse(JSON.stringify(obj)))); },
    close(conn) { if (conn.closed) return; conn.closed = true; setImmediate(() => roomRef.room.onClose(conn)); },
    now: () => Date.now(), setTimeout, clearTimeout,
    save(snap) { roomRef.snap = JSON.parse(JSON.stringify(snap)); }
  };
}
function makeRoom(code, opts) {
  const ref = {}; ref.room = new Room(code, { G, Flow }, makeIo(ref), Object.assign({ botDelay: 1, awayAfter: 40, pickSecs: 60, resultsSecs: 60 }, opts));
  return ref;
}

class Client {
  constructor(ref, name, opts) { this.ref = ref; this.name = name; this.opts = opts || {}; this.id = 0; this.log = []; this.errors = []; this.state = null; this.lobby = null; this.pending = false; this.rejected = 0; this.acts = 0; this.replays = 0; }
  connect(hello) {
    this.conn = { closed: false, receive: m => this.receive(m) };
    this.ref.room.onMessage(this.conn, JSON.stringify(Object.assign({ t: 'hello', name: this.name, token: this.token }, hello)));
  }
  send(m) { if (!this.conn.closed) this.ref.room.onMessage(this.conn, JSON.stringify(m)); }
  drop() { this.conn.closed = true; this.ref.room.onClose(this.conn); }
  receive(m) {
    this.log.push(m.t);
    if (m.t === 'joined') this.token = m.token;
    else if (m.t === 'lobby') this.lobby = m;
    else if (m.t === 'error') this.errors.push(m.msg);
    else if (m.t === 'replay') this.replays++;
    else if (m.t === 'res') { this.pending = false; if (!m.ok) { this.rejected++; if (this.lastAct && /buy|evolve|churn/.test(this.lastAct.t)) this.act({ t: 'pass' }); } }
    else if (m.t === 'state') { this.state = m; this.think(); }
  }
  game() { return G.Game.deserialize(this.state.view); }
  think() {
    const s = this.state; if (this.opts.idle || this.pending || this.conn.closed) return;
    const seat = s.view.seat; if (!s.wait.seats.includes(seat)) return;
    const g = this.game(), p = g.players[seat];
    let a;
    if (g.phase === 'pick') a = { t: 'pick', uid: p.deal[0].uid };
    else if (g.phase === 'results') a = { t: 'ready' };
    else if (g.phase === 'shop') {
      const opts = [];
      for (const t of G.TIERS) if (G.GATE[t] <= p.level) g.row[t].forEach((c, sl) => { if (c && c.spec.price <= p.gold) opts.push({ t: 'buyCard', tier: t, slot: sl }); });
      a = opts.length && Math.random() < 0.6 ? opts[Math.floor(Math.random() * opts.length)] : { t: 'pass' };
    }
    if (a) this.act(a);
  }
  act(a) { this.pending = true; this.lastAct = a; this.acts++; this.send({ t: 'act', a, id: ++this.id }); }
  phase() { return this.state && this.state.view.phase; }
}
async function until(fn, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (fn()) return true; await sleep(10); } fail('timeout waiting for', what); return false; }

(async () => {
  // A: one player, full game
  console.log('A: 1 player, full game');
  { const R = makeRoom('AAAA'); const c = new Client(R, 'Solo'); c.connect({ create: true });
    await until(() => c.lobby, 1000, 'lobby');
    if (!c.lobby.members[0].host) fail('creator is not host');
    c.send({ t: 'start' });
    await until(() => c.phase() === 'end', 60000, 'game end');
    const g = c.game(); if (g.round !== 12) fail('ended at round', g.round);
    if (c.replays < 10) fail('few replays', c.replays);
    console.log(`  rounds ${g.round}, acts ${c.acts}, replays ${c.replays}, rejected ${c.rejected}`); R.room.close(); }

  // B: 4 players; disconnect + reconnect with token; a permanent leaver; bad joins
  console.log('B: 4 players, disconnect/reconnect, leaver, bad joins');
  { const R = makeRoom('BBBB');
    const ghost = new Client(R, 'Ghost'); ghost.connect({});            // joining a room nobody created
    await until(() => ghost.errors.length, 1000, 'no-room error');
    const cs = ['Ann', 'Ben', 'Cat', 'Dan'].map(n => new Client(R, n));
    cs[0].connect({ create: true }); for (const c of cs.slice(1)) c.connect({});
    await until(() => cs.every(c => c.lobby && c.lobby.members.length === 4), 1000, 'lobby of 4');
    cs[1].send({ t: 'start' }); await sleep(30);
    if (!cs[1].errors.some(e => /host/.test(e))) fail('non-host start allowed');
    cs[0].send({ t: 'start' });
    await until(() => cs.every(c => c.state), 3000, 'state for all');
    const late = new Client(R, 'Late'); late.connect({});
    await until(() => late.errors.length, 1000, 'already-started error');
    // out-of-turn shop action is rejected
    await until(() => cs[0].phase() === 'shop', 20000, 'shop');
    // Ben drops for longer than the grace period, then comes back with his token
    const g0 = cs[1].game().round; cs[1].drop();
    await sleep(120);
    const awaySeen = cs[0].state.view.players[cs[1].state.view.seat].away;
    if (!awaySeen) fail('dropped player not marked away');
    cs[1].connect({});
    await until(() => cs[1].state && !cs[1].state.view.players[cs[1].state.view.seat].away, 3000, 'reconnected player back');
    // Dan leaves for good
    cs[3].send({ t: 'leave' });
    await until(() => cs.slice(0, 3).every(c => c.phase() === 'end'), 120000, 'game end');
    const g = cs[0].game();
    if (!g.players[cs[3].state.view.seat].away) fail('leaver not away');
    if (g.players.reduce((a, p) => a + p.points, 0) !== 160) fail('points not conserved');
    console.log(`  ended round ${g.round}; Ben dropped in round ${g0}; acts ${cs.map(c => c.acts).join('/')}`); R.room.close(); }

  // C: 8 players incl. one idle; shop turn timer keeps the game moving; 9th player refused
  console.log('C: 8 players, one idle, turn timers');
  { const R = makeRoom('CCCC', { timeScale: 0.002 });
    const cs = Array.from({ length: 8 }, (_, i) => new Client(R, 'P' + i, { idle: i === 5 }));
    cs[0].connect({ create: true }); for (const c of cs.slice(1)) c.connect({});
    await until(() => cs[0].lobby && cs[0].lobby.members.length === 8, 1000, 'lobby of 8');
    const ninth = new Client(R, 'Nine'); ninth.connect({});
    await until(() => ninth.errors.some(e => /full/.test(e)), 1000, 'room full error');
    cs[0].send({ t: 'settings', turn: 30 }); cs[0].send({ t: 'start' });
    await until(() => cs.every(c => c.phase() === 'end'), 120000, 'game end');
    const g = cs[0].game();
    const idle = g.players[cs[5].state.view.seat];
    const timeouts = g.log.filter(l => /ran out of time/.test(l.msg)).length;
    if (!g.log.length) fail('no log');
    console.log(`  ended round ${g.round}; idle player ${idle.name} finished with ${idle.points} pts; timeouts in last log ${timeouts}`); R.room.close(); }

  // D: restart mid-game from the saved snapshot; players reconnect with tokens and finish
  console.log('D: server restart mid-game');
  { const R = makeRoom('DDDD');
    const cs = ['Eve', 'Fay'].map(n => new Client(R, n)); cs[0].connect({ create: true }); cs[1].connect({});
    await until(() => cs[0].lobby && cs[0].lobby.members.length === 2, 1000, 'lobby of 2');
    cs[0].send({ t: 'start' });
    await until(() => cs[0].state && cs[0].state.view.round >= 4, 60000, 'round 4');
    const snap = R.snap; const round = snap.game.round;
    R.room.close(); for (const c of cs) c.conn.closed = true;
    const R2 = makeRoom('DDDD'); R2.room.restore(snap);
    for (const c of cs) { c.ref = R2; c.pending = false; c.connect({}); }
    await until(() => cs.every(c => c.phase() === 'end'), 120000, 'game end after restart');
    console.log(`  restarted at round ${round}, finished round ${cs[0].game().round}`); R2.room.close(); }

  console.log(fails ? `FAILED: ${fails}` : 'ALL OK');
  process.exit(fails ? 1 : 0);
})();
