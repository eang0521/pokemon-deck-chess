/* PAC room server for Node: serves the website and the online rooms (WebSocket at /room/CODE) on one port.
   Local play-testing:   cd server && npm install && npm start   then open http://localhost:8787
   Also deployable as-is to any Node host (Render, Fly.io, Railway...). Rooms live in memory. */
'use strict';
const http = require('http'), fs = require('fs'), path = require('path');
const { WebSocketServer } = require('ws');
const { load } = require('../tests/load');
const { G, Flow } = load();
const { Room } = require('./room.js');

const PORT = +process.env.PORT || 8787;
const ROOT = path.join(__dirname, '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.ico': 'image/x-icon' };
const PUBLIC = /^\/(index\.html|js\/[\w.-]+\.js|css\/[\w.-]+\.css|assets\/[\w/.-]+)?$/;

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname === '/health') { res.writeHead(200, { 'content-type': 'text/plain' }); res.end('ok'); return; }
  if (!PUBLIC.test(url.pathname) || url.pathname.includes('..')) { res.writeHead(404); res.end('not found'); return; }
  const file = path.join(ROOT, url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname));
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-cache' });
    res.end(buf);
  });
});

const rooms = new Map();
function roomFor(code) {
  let r = rooms.get(code);
  if (!r) {
    r = new Room(code, { G, Flow }, {
      send(ws, obj) { if (ws.readyState === 1) ws.send(JSON.stringify(obj)); },
      close(ws) { try { ws.close(); } catch (e) { } },
      now: () => Date.now(), setTimeout, clearTimeout
    });
    rooms.set(code, r);
  }
  return r;
}
// forget rooms nobody has been connected to for an hour
setInterval(() => { for (const [code, r] of rooms) { if (!r.online().length && Date.now() - (r.lastSeen || 0) > 3600e3) { r.close(); rooms.delete(code); } } }, 60e3).unref();

const wss = new WebSocketServer({ noServer: true, maxPayload: 64 * 1024 });
server.on('upgrade', (req, socket, head) => {
  const m = /^\/room\/([A-Z0-9]{4,6})$/.exec(new URL(req.url, 'http://x').pathname);
  if (!m) { socket.destroy(); return; }
  wss.handleUpgrade(req, socket, head, ws => {
    const room = roomFor(m[1]);
    ws.on('message', data => { room.lastSeen = Date.now(); room.onMessage(ws, data.toString()); });
    ws.on('close', () => { room.lastSeen = Date.now(); room.onClose(ws); });
    ws.on('error', () => { });
  });
});
server.listen(PORT, () => console.log(`PAC server on http://localhost:${PORT}  (rooms at ws://localhost:${PORT}/room/CODE)`));
