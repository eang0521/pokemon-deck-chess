// Restart check against a room server that persists rooms (Cloudflare): phase 1 starts a game and saves the
// player token; phase 2 (after the server restarts) reconnects with it and expects the same game back.
//   node tests/restart_test.js ws://127.0.0.1:8790 start   -> prints CODE TOKEN ROUND
//   node tests/restart_test.js ws://127.0.0.1:8790 resume CODE TOKEN
const WebSocket = require('../server/node_modules/ws');
const [BASE, mode, CODE, TOKEN] = process.argv.slice(2);
const ws = new WebSocket(`${BASE}/room/${mode === 'start' ? (CODE || 'RS' + Math.floor(Math.random() * 90 + 10)) : CODE}`);
let token = TOKEN, last = null;
ws.on('open', () => ws.send(JSON.stringify(mode === 'start' ? { t: 'hello', name: 'Res', create: true } : { t: 'hello', name: 'Res', token })));
ws.on('message', d => {
  const m = JSON.parse(d.toString());
  if (m.t === 'joined') token = m.token;
  if (m.t === 'lobby' && mode === 'start') ws.send(JSON.stringify({ t: 'start' }));
  if (m.t === 'error') { console.log('ERROR', m.msg); process.exit(1); }
  if (m.t === 'state') {
    last = m.view;
    // play: pick first, ready, pass
    if (m.wait.seats.includes(m.view.seat)) {
      const me = m.view.players[m.view.seat];
      const a = m.view.phase === 'pick' ? { t: 'pick', uid: me.deal[0] } : m.view.phase === 'results' ? { t: 'ready' } : { t: 'pass' };
      ws.send(JSON.stringify({ t: 'act', a, id: 1 }));
    }
    if (mode === 'start' && m.view.round >= 3) setTimeout(() => { console.log(new URL(ws.url).pathname.split('/').pop(), token, last.round); process.exit(0); }, 1500);
    if (mode === 'resume') { console.log('resumed round', m.view.round, 'phase', m.view.phase, 'away', m.view.players[m.view.seat].away); process.exit(0); }
  }
});
setTimeout(() => { console.log('TIMEOUT'); process.exit(1); }, 120000);
