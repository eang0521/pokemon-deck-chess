/* PAC digital — online rooms: connect to the room server, lobby screen, reconnects, countdowns.
   The server owns the game; this tab shows the state it sends (a per-seat view) and sends actions back. */
(function () {
'use strict';
const UI = window.UI, S = UI.state;
const ROOM_KEY = 'pac-room-v1';
const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
const $app = () => document.getElementById('app');

function saveRoom(r) { try { localStorage.setItem(ROOM_KEY, JSON.stringify(r)); } catch (e) { } }
function lastRoom() { try { return JSON.parse(localStorage.getItem(ROOM_KEY)); } catch (e) { return null; } }
function forget() { try { localStorage.removeItem(ROOM_KEY); } catch (e) { } }
function newCode() { let s = ''; for (let i = 0; i < 4; i++) s += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)]; return s; }

// one connection to one room; reconnects on its own until left
// token: only when rejoining a seat this browser held before; reconnects reuse the token the server gave
function Conn(code, name, hello, token) {
  const c = { code, name, ws: null, open: false, everOpen: false, failed: 0, left: false, tries: 0, id: 0, replays: {}, lobby: null, token: token || null, offset: 0, deadline: null, round: 0 };
  function connect() {
    let ws; try { ws = new WebSocket(`${window.PAC_SERVER}/room/${code}`); } catch (e) { UI.toast('Could not reach the game server.', 'bad'); return; }
    c.ws = ws;
    ws.onopen = () => { c.open = true; c.everOpen = true; c.tries = 0; ws.send(JSON.stringify(Object.assign({ t: 'hello', name, token: c.token || undefined }, hello))); hello = {}; repaint(); };
    ws.onmessage = e => { let m; try { m = JSON.parse(e.data); } catch (_) { return; } onMsg(m); };
    ws.onclose = () => {
      c.open = false; if (c.left) return;
      // never reached the server at all: online play isn't available, don't spin forever
      if (!c.everOpen && ++c.failed >= 2) {
        c.left = true; S.net = null; UI.api.showTitle();
        UI.toast('Could not reach the online game server. Solo and pass &amp; play still work.', 'bad'); return;
      }
      repaint();
      const wait = Math.min(8000, 500 * Math.pow(2, c.tries++));
      setTimeout(() => { if (!c.left) connect(); }, wait);
    };
  }
  function onMsg(m) {
    switch (m.t) {
      case 'joined': c.token = m.token; c.name = m.name; saveRoom({ code, token: m.token, name: m.name }); break;
      case 'lobby': c.lobby = m; if (!S.g) showLobby(c); break;
      case 'replay': c.replays[m.r] = m.replay; break;
      case 'res': UI.api.afterAct(m); break;
      case 'error':
        UI.toast(m.msg, 'bad');
        if (m.fatal) { c.left = true; try { c.ws.close(); } catch (e) { } if (lastRoom() && lastRoom().code === code) forget(); S.net = null; UI.api.showTitle(); }
        break;
      case 'state': {
        c.offset = m.now - Date.now(); c.deadline = m.deadline; c.online = m.online || []; c.wait = m.wait;
        const v = m.view; const g = window.PACGame.Game.deserialize(v);
        if (v.round !== c.round) { if (c.round) S.newRound = true; c.round = v.round; S.watched = {}; }
        S.g = g; S.seat = v.seat;
        if (g.phase === 'end') forget();
        UI.api.sync();
        break;
      }
    }
  }
  function send(m) { if (c.ws && c.open) { c.ws.send(JSON.stringify(m)); return true; } UI.toast('Reconnecting to the game server…', 'bad'); return false; }
  Object.assign(c, {
    act(a) { send({ t: 'act', a, id: ++c.id }); return { ok: true, pending: true }; },
    start() { send({ t: 'start' }); },
    setTurn(turn) { send({ t: 'settings', turn }); },
    replay(r) { return c.replays[r]; },
    leave() { c.left = true; try { send({ t: 'leave' }); c.ws.close(); } catch (e) { } }
  });
  connect();
  return c;
}
function repaint() { if (S.g) UI.renderBoard(); else if (S.net && S.net.lobby) showLobby(S.net); }

function begin(code, name, hello, token) {
  if (S.net) { S.net.left = true; try { S.net.ws.close(); } catch (e) { } }
  S.g = null; UI.closeModals();
  $app().innerHTML = `<div class="title"><div class="t-card curtain"><div class="t-logo">Room ${code}<small>connecting…</small></div></div></div>`;
  S.net = Conn(code, name, hello, token);
}

function showLobby(c) {
  const L = c.lobby; if (!L || S.g) return;
  const me = L.members[L.you] || {}, host = !!me.host;
  const link = `${location.origin}${location.pathname}?room=${L.code}`;
  const seats = [];
  for (let i = 0; i < 8; i++) {
    const m = L.members[i];
    seats.push(m ? `<div class="seat"><span>${UI.esc(m.name)}${i === L.you ? ' <small class="muted">(you)</small>' : ''}</span><span class="tag">${m.host ? 'host' : ''}${m.online ? '' : ' · offline'}</span></div>`
      : `<div class="seat bot"><span>Bot</span><span class="tag">fills this seat</span></div>`);
  }
  const turnSel = `<select id="lobby-turn" ${host ? '' : 'disabled'}>${L.turnChoices.map(s => `<option value="${s}" ${s === L.settings.turn ? 'selected' : ''}>${s ? s + ' seconds' : 'no limit'}</option>`).join('')}</select>`;
  $app().innerHTML = `<div class="title"><div class="t-card lobby">
    <div class="t-logo">Room <span class="code">${UI.esc(L.code)}</span><small>${L.members.length} of 8 players · bots fill the rest</small></div>
    <p class="t-sub">Share the code, or this link: <a href="${UI.esc(link)}">${UI.esc(link)}</a> <button class="btn ghost" data-act="room-copy" data-link="${UI.esc(link)}">Copy link</button></p>
    <div class="seats">${seats.join('')}</div>
    <div class="set"><label>Shop turn time limit ${turnSel}</label></div>
    <div class="t-btns">${host ? `<button class="btn big" data-act="room-start">Start game</button>` : `<span class="muted">Waiting for the host to start…</span>`}
      <button class="btn ghost" data-act="room-leave">Leave room</button></div>
    ${c.open ? '' : '<p class="warn">Reconnecting…</p>'}
  </div></div>`;
  const sel = document.getElementById('lobby-turn'); if (sel && host) sel.onchange = () => c.setTurn(+sel.value);
}

// countdown for the seat on turn (server time, corrected for this device's clock)
function clock() {
  const c = S.net; if (!c || !c.deadline) return '';
  return ` <span class="clock" data-dl="${c.deadline - c.offset}">${Math.max(0, Math.ceil((c.deadline - c.offset - Date.now()) / 1000))}s</span>`;
}
setInterval(() => {
  for (const el of document.querySelectorAll('.clock[data-dl]')) el.textContent = Math.max(0, Math.ceil((+el.dataset.dl - Date.now()) / 1000)) + 's';
}, 500);
function badge() { const c = S.net; return c ? `<span class="net-badge ${c.open ? '' : 'off'}" title="Room ${c.code}">${c.open ? 'online · ' + c.code : 'reconnecting…'}</span>` : ''; }

document.addEventListener('click', e => {
  const t = e.target.closest('[data-act]'); if (!t) return;
  switch (t.dataset.act) {
    case 'room-start': S.net && S.net.start(); break;
    case 'room-leave': if (S.net) { S.net.leave(); S.net = null; } forget(); UI.api.showTitle(); break;
    case 'room-copy': { const l = t.dataset.link; (navigator.clipboard ? navigator.clipboard.writeText(l) : Promise.reject()).then(() => UI.toast('Link copied.', 'good'), () => UI.toast(l)); break; }
  }
});

UI.net = {
  create(name) { begin(newCode(), name, { create: true }); },
  join(code, name) { begin(code.replace(/[^A-Z0-9]/g, '').slice(0, 6), name, {}); },
  rejoin() { const r = lastRoom(); if (r) begin(r.code, r.name || S.name, {}, r.token); },
  lastRoom, forget, clock, badge
};
})();
