/* PAC rooms on Cloudflare: the Worker routes /room/CODE to one Durable Object per room code,
   which runs server/room.js and keeps the room in storage so it survives restarts. */
import './shim.js';
import '../js/data.js';
import '../js/engine.js';
import G from '../js/game.js';
import '../js/bots.js';
import Flow from '../js/flow.js';
import RoomMod from './room.js';
const { Room } = RoomMod;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === '/' || url.pathname === '/health') return new Response('PAC rooms ok', { headers: { 'content-type': 'text/plain' } });
    const m = /^\/room\/([A-Z0-9]{4,6})$/.exec(url.pathname);
    if (!m) return new Response('not found', { status: 404 });
    if (req.headers.get('Upgrade') !== 'websocket') return new Response('expected a websocket', { status: 426 });
    const stub = env.ROOMS.get(env.ROOMS.idFromName(m[1]));
    url.searchParams.set('code', m[1]);
    return stub.fetch(new Request(url, req));
  }
};

export class RoomDO {
  constructor(state) { this.state = state; this.room = null; this.saveTimer = null; this.pending = null; }
  async ensure(code) {
    if (this.room) return this.room;
    const io = {
      send(ws, obj) { try { ws.send(JSON.stringify(obj)); } catch (e) { } },
      close(ws) { try { ws.close(1000, 'bye'); } catch (e) { } },
      now: () => Date.now(),
      setTimeout: (f, ms) => setTimeout(f, ms),
      clearTimeout: id => clearTimeout(id),
      save: snap => this.save(snap)
    };
    this.room = new Room(code, { G, Flow }, io);
    const snap = await this.state.storage.get('room');
    if (snap) this.room.restore(snap);
    return this.room;
  }
  // coalesce saves: the room changes many times a second while bots play
  save(snap) {
    this.pending = snap;
    if (this.saveTimer) return;
    this.saveTimer = setTimeout(() => { this.saveTimer = null; const s = this.pending; this.pending = null; this.state.storage.put('room', s); }, 400);
  }
  async fetch(req) {
    const code = new URL(req.url).searchParams.get('code');
    const room = await this.ensure(code);
    const [client, server] = Object.values(new WebSocketPair());
    server.accept();
    server.addEventListener('message', e => room.onMessage(server, typeof e.data === 'string' ? e.data : ''));
    server.addEventListener('close', () => room.onClose(server));
    server.addEventListener('error', () => room.onClose(server));
    return new Response(null, { status: 101, webSocket: client });
  }
}
