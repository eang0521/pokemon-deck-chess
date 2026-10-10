/* PAC online room: lobby, the authoritative game, bot pacing, turn timers and disconnects.
   Platform-neutral: the Node server (server/node.js) and the Cloudflare Durable Object (server/worker.js)
   hand it connections and messages, and give it `io` for sending, timers and persistence.

   Client -> server: {t:'hello', name, token?, create?} {t:'start'} {t:'settings', turn} {t:'act', a, id} {t:'leave'} {t:'ping'}
   Server -> client: {t:'joined', token, code} {t:'lobby', ...} {t:'state', view, wait, deadline} {t:'replay', r, replay}
                     {t:'res', id, ok, err?, msg?} {t:'error', msg, fatal?} {t:'pong'} */
'use strict';

const BOT_DELAY = 550;        // ms between visible bot actions
const AWAY_AFTER = 20000;     // ms a disconnected player has before a bot takes over their seat
const PICK_SECS = 60, RESULTS_SECS = 150;
const TURN_CHOICES = [0, 30, 45, 60, 90]; // shop turn limit in seconds (0 = no limit)
const MAX_PLAYERS = 8;

function token() { let s = ''; const a = 'abcdefghijklmnopqrstuvwxyz0123456789'; for (let i = 0; i < 24; i++) s += a[Math.floor(Math.random() * a.length)]; return s; }
const clean = n => String(n || '').replace(/[\u0000-\u001f<>]/g, '').trim().slice(0, 14) || 'Player';

class Room {
  // deps: { G, Flow } ; io: { send(conn, obj), close(conn), now(), setTimeout, clearTimeout, save(snapshot) }
  // opts (tests): { botDelay, awayAfter, pickSecs, resultsSecs } override the defaults above
  constructor(code, deps, io, opts) {
    this.code = code; this.G = deps.G; this.Flow = deps.Flow; this.io = io;
    this.opt = Object.assign({ botDelay: BOT_DELAY, awayAfter: AWAY_AFTER, pickSecs: PICK_SECS, resultsSecs: RESULTS_SECS }, opts);
    this.members = [];            // { token, name, conn, host, seat, awayTimer }
    this.settings = { turn: 45 };
    this.g = null; this.deadline = null; this.waitKey = null; this.timer = null;
    this.driving = false; this.again = false; this.closed = false;
  }

  // ---------- connections ----------
  online() { return this.members.filter(m => m.conn); }
  memberOf(conn) { return this.members.find(m => m.conn === conn); }
  onMessage(conn, raw) {
    let m; try { m = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) { return; }
    if (!m || typeof m.t !== 'string') return;
    if (m.t === 'ping') return this.io.send(conn, { t: 'pong' });
    if (m.t === 'hello') return this.hello(conn, m);
    const me = this.memberOf(conn); if (!me) return this.io.send(conn, { t: 'error', msg: 'Say hello first.' });
    if (m.t === 'start') return this.start(me);
    if (m.t === 'settings') { if (me.host && !this.g && TURN_CHOICES.includes(+m.turn)) { this.settings.turn = +m.turn; this.sendLobby(); } return; }
    if (m.t === 'act') return this.act(me, m);
    if (m.t === 'leave') return this.leave(me);
  }
  hello(conn, m) {
    let me = m.token && this.members.find(x => x.token === m.token);
    if (me) {
      // reconnect: take the seat back from the bot
      if (me.conn && me.conn !== conn) this.io.close(me.conn);
      me.conn = conn; this.io.clearTimeout(me.awayTimer); me.awayTimer = null;
      if (this.g && me.seat !== null) { const p = this.g.players[me.seat]; if (p.away) { p.away = false; this.g.say(`${p.name} is back`, 'sys'); } }
    } else {
      if (!this.members.length && !this.g && !m.create) { this.io.send(conn, { t: 'error', msg: `There is no room ${this.code}. Check the code, or create a new room.`, fatal: true }); return; }
      if (this.g) { this.io.send(conn, { t: 'error', msg: 'That game has already started.', fatal: true }); return; }
      if (this.members.length >= MAX_PLAYERS) { this.io.send(conn, { t: 'error', msg: 'That room is full (8 players).', fatal: true }); return; }
      me = { token: token(), name: clean(m.name), conn, host: !this.members.length, seat: null, awayTimer: null };
      this.members.push(me);
    }
    this.io.send(conn, { t: 'joined', token: me.token, code: this.code, name: me.name });
    if (this.g) { this.sendState(me); this.drive(); } else this.sendLobby();
    this.persist();
  }
  onClose(conn) {
    const me = this.memberOf(conn); if (!me) return;
    me.conn = null;
    if (!this.g) {
      // lobby: drop the player; the next one becomes host
      this.members = this.members.filter(x => x !== me);
      if (me.host && this.members.length) this.members[0].host = true;
      this.sendLobby(); this.persist(); return;
    }
    if (me.seat === null) return;
    me.awayTimer = this.io.setTimeout(() => {
      me.awayTimer = null;
      if (me.conn || !this.g) return;
      const p = this.g.players[me.seat];
      if (!p.away) { p.away = true; this.g.say(`${p.name} disconnected: a bot plays for them until they return`, 'sys'); }
      this.broadcast(); this.drive();
    }, this.opt.awayAfter);
  }
  leave(me) {
    const c = me.conn; me.conn = null;
    if (c) this.io.close(c);
    if (!this.g) {
      this.members = this.members.filter(x => x !== me);
      if (me.host && this.members.length) this.members[0].host = true;
      this.sendLobby(); this.persist(); return;
    }
    const p = this.g.players[me.seat];
    if (p && !p.away) { p.away = true; this.g.say(`${p.name} left: a bot plays for them`, 'sys'); }
    this.broadcast(); this.drive();
  }

  // ---------- lobby ----------
  lobbyMsg() {
    return { t: 'lobby', code: this.code, settings: this.settings, turnChoices: TURN_CHOICES,
      members: this.members.map(m => ({ name: m.name, host: m.host, online: !!m.conn })) };
  }
  sendLobby() { const msg = this.lobbyMsg(); for (const m of this.online()) this.io.send(m.conn, Object.assign({ you: this.members.indexOf(m) }, msg)); }
  start(me) {
    if (this.g) return;
    if (!me.host) return this.io.send(me.conn, { t: 'error', msg: 'Only the host can start the game.' });
    const players = this.online();
    if (!players.length) return;
    const seed = (Math.floor(Math.random() * 4294967295)) >>> 0;
    this.members = players;
    this.members.forEach((m, i) => { m.seat = i; });
    this.g = new this.G.Game(seed, { players: this.Flow.seatDefs(this.members.map(m => m.name), seed) });
    this.g.say(`Room ${this.code} · ${this.members.length} player${this.members.length > 1 ? 's' : ''} · seed ${seed}`, 'sys');
    this.drive();
  }

  // ---------- game ----------
  act(me, m) {
    if (!this.g || me.seat === null) return this.io.send(me.conn, { t: 'res', id: m.id, ok: false, err: 'The game has not started.' });
    const r = this.Flow.apply(this.g, me.seat, m.a);
    this.io.send(me.conn, Object.assign({ t: 'res', id: m.id }, r));
    if (r.ok) { this.broadcast(); this.drive(); }
  }
  // run bots and transitions until a human is needed; paced so players can follow bot moves
  async drive() {
    if (!this.g || this.closed) return;
    if (this.driving) { this.again = true; return; }
    this.driving = true;
    try {
      do {
        this.again = false;
        for (;;) {
          if (!this.online().length || this.closed) return;      // nobody watching: pause until someone reconnects
          const ev = this.Flow.next(this.g);
          if (!ev) break;
          if (ev.t === 'battles') this.sendReplays();
          if (ev.t === 'bot' && ev.desc) { this.broadcast(); await this.sleep(this.opt.botDelay); }
          else if (ev.t === 'round') this.broadcast();
        }
      } while (this.again);
    } finally { this.driving = false; }
    this.armTimer();
    this.broadcast();
    this.persist();
  }
  sleep(ms) { return new Promise(r => this.io.setTimeout(r, ms)); }
  sendReplays() {
    const res = this.g.results; if (!res) return;
    for (const m of this.online()) { const rp = res.replays[m.seat]; if (rp) this.io.send(m.conn, { t: 'replay', r: res.r, replay: rp }); }
  }
  // deadlines: the seat on turn (shop), unpicked seats (pick), unconfirmed results; expiry acts for them
  // what the table is waiting on right now; a deadline only applies while this stays the same
  waitKeyOf(g) { return g.phase === 'shop' ? `s${g.round}.${g.shop.sweeps}.${g.shop.pos}` : `${g.phase}${g.round}`; }
  armTimer() {
    const g = this.g, w = this.Flow.waiting(g);
    const key = this.waitKeyOf(g);
    if (!w.seats.length || g.phase === 'end') { this.clearTimer(); return; }
    if (key === this.waitKey && this.timer) return;
    this.clearTimer(); this.waitKey = key;
    const secs = g.phase === 'shop' ? this.settings.turn : g.phase === 'pick' ? (this.settings.turn ? this.opt.pickSecs : 0) : (this.settings.turn ? this.opt.resultsSecs : 0);
    if (!secs) return;
    this.deadline = this.io.now() + secs * 1000;
    this.timer = this.io.setTimeout(() => { this.timer = null; this.expire(key); }, secs * 1000 * (this.opt.timeScale || 1));
  }
  clearTimer() { if (this.timer) this.io.clearTimeout(this.timer); this.timer = null; this.deadline = null; this.waitKey = null; }
  expire(key) {
    const g = this.g; if (!g || key !== this.waitKey) return;
    const w = this.Flow.waiting(g);
    if (g.phase === 'shop') for (const s of w.seats) { g.humanPass(s); g.say(`${g.players[s].name} ran out of time and passes`, 'sys'); }
    else if (g.phase === 'pick') { for (const s of w.seats) { g.botPick(g.players[s]); g.say(`${g.players[s].name} ran out of time: a pick was made for them`, 'sys'); } if (!g.waitingPick().length) g.startShop(); }
    else if (g.phase === 'results') for (const s of w.seats) g.markReady(s);
    this.deadline = null; this.waitKey = null;
    this.broadcast(); this.drive();
  }
  stateFor(m) {
    const g = this.g, w = this.Flow.waiting(g);
    const deadline = this.deadline && this.waitKey === this.waitKeyOf(g) ? this.deadline : null;
    return { t: 'state', view: this.Flow.view(g, m.seat), wait: w, deadline, now: this.io.now(),
      online: this.members.filter(x => x.conn).map(x => x.seat) };
  }
  sendState(m) { if (m.conn) this.io.send(m.conn, this.stateFor(m)); }
  broadcast() { if (this.g) for (const m of this.online()) this.sendState(m); }

  // ---------- persistence ----------
  snapshot() {
    // battle replays are large and only needed live: they are not kept across restarts
    const game = this.g ? this.g.serialize() : null;
    if (game && game.results) game.results = { r: game.results.r, pairs: game.results.pairs, replays: {} };
    return { code: this.code, settings: this.settings, game,
      members: this.members.map(m => ({ token: m.token, name: m.name, host: m.host, seat: m.seat })) };
  }
  persist() { if (this.io.save) this.io.save(this.snapshot()); }
  restore(snap) {
    if (!snap) return;
    this.settings = snap.settings || this.settings;
    this.members = (snap.members || []).map(m => Object.assign({ conn: null, awayTimer: null }, m));
    if (snap.game) {
      this.g = this.G.Game.deserialize(snap.game);
      // nobody is connected after a restart: everyone counts as away until they reconnect
      for (const m of this.members) if (m.seat !== null) this.g.players[m.seat].away = true;
    }
  }
  close() { this.closed = true; this.clearTimer(); for (const m of this.members) this.io.clearTimeout(m.awayTimer); }
}

module.exports = { Room, TURN_CHOICES };
