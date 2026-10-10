/* PAC digital — flow control: title, new game, table flow, dialogs, picks, results, save/load.
   Every player action goes through act(): local games (solo, pass-and-play) apply it here with PACFlow,
   online games send it to the room server (js/net.js), which sends back the new state. */
(function () {
'use strict';
const UI = window.UI, D = window.PAC_DATA, G = window.PACGame, B = window.PACBots, E = window.PACEngine, Flow = window.PACFlow, ITEMS = D.items;
const S = UI.state;
const { GATE, TIERS, TRADE } = G;
const SAVE_KEY = 'pac-digital-save-v4', PREF_KEY = 'pac-digital-prefs-v1';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const me = () => S.g.players[S.seat];
const $app = () => document.getElementById('app');
Object.assign(S, { seat: 0, watched: {}, net: null });

// ---------- preferences ----------
function loadPrefs() { try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch (e) { return {}; } }
function savePrefs() { try { localStorage.setItem(PREF_KEY, JSON.stringify({ botDelay: S.botDelay, autoPass: S.autoPass, duelMode: S.duelMode, name: S.name, hotNames: S.hotNames })); } catch (e) { } }
Object.assign(S, { botDelay: 420, autoPass: true, duelMode: 'animated', name: 'You', hotNames: [] }, loadPrefs());

// ---------- save / load (local games only; online games live on the server) ----------
function saveGame() {
  if (!S.g || S.net || S.g.phase === 'end') return;
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(S.g.serialize())); } catch (e) { /* storage unavailable */ }
}
function loadSaved() { try { const j = localStorage.getItem(SAVE_KEY); return j ? JSON.parse(j) : null; } catch (e) { return null; } }
function clearSave() { try { localStorage.removeItem(SAVE_KEY); } catch (e) { } }

// ---------- title ----------
function showTitle() {
  if (S.net) { S.net.leave(); S.net = null; }
  S.g = null; UI.closeModals();
  const saved = loadSaved(), room = UI.net && UI.net.lastRoom();
  const nh = saved ? saved.players.filter(p => !p.bot).length : 0;
  $app().innerHTML = `<div class="title">
    <div class="t-card">
      <div class="t-logo">Pokémon Auto Chess<small>the board game · digital prototype</small></div>
      <p class="t-sub">1 to 8 players; bots fill the empty seats. Twelve rounds of shopping, building and duels. Most points after round 12 wins.</p>
      <div class="t-form">
        <label>Your name <input id="in-name" maxlength="14" value="${UI.esc(S.name)}"></label>
        <label>Seed <small>(optional, same seed = same shop &amp; bots)</small> <input id="in-seed" placeholder="random" inputmode="numeric"></label>
      </div>
      <div class="t-modes">
        <div class="t-mode"><h4>Solo</h4><p>You against 7 bots, on this device.</p>
          <div class="t-btns"><button class="btn big" data-act="new-game">New game</button>
          ${saved ? `<button class="btn big alt" data-act="continue-game">Continue · round ${saved.round}${nh > 1 ? ` · ${nh} players` : ''}</button>` : ''}</div></div>
        <div class="t-mode"><h4>Pass &amp; play</h4><p>2 to 8 people share this device and take turns.</p>
          <div class="t-btns"><button class="btn" data-act="hotseat-setup">Set up players</button></div></div>
        <div class="t-mode"><h4>Online</h4><p>Everyone on their own device. Share the room code.</p>
          <div class="t-btns"><button class="btn" data-act="room-create">Create room</button>
            <span class="t-join"><input id="in-room" maxlength="6" placeholder="CODE" autocapitalize="characters"><button class="btn" data-act="room-join">Join</button></span>
            ${room ? `<button class="btn alt" data-act="room-rejoin">Rejoin ${UI.esc(room.code)}</button>` : ''}</div></div>
      </div>
      <div class="t-btns"><button class="btn ghost" data-act="show-rules">How to play</button></div>
      <div class="t-bots"><h4>The bots <small>(personalities are shuffled between seats each game)</small></h4>
        ${B.PERSONAS.map(p => `<div class="bp"><b>${UI.esc(p.name)}</b> <i>${UI.esc(p.title)}</i><br><span>${UI.esc(p.blurb)}</span></div>`).join('')}</div>
      <p class="t-foot">Personal, non-commercial prototype. Solo and pass &amp; play work offline and autosave in this browser.</p>
    </div></div>`;
  const q = new URLSearchParams(location.search).get('room');
  if (q) document.getElementById('in-room').value = q.toUpperCase();
}
function readName() { const n = (document.getElementById('in-name').value || 'You').trim().slice(0, 14) || 'You'; S.name = n; savePrefs(); return n; }
function readSeed() { const s = (document.getElementById('in-seed') || {}).value; return s && s.trim() ? (parseInt(s.trim(), 10) >>> 0) : (Math.floor(Math.random() * 4294967295) >>> 0); }

function startLocal(names, seed) {
  S.g = new G.Game(seed, { players: Flow.seatDefs(names, seed) });
  S.g.say(`New game · seed ${seed}`, 'sys');
  for (const p of S.g.humans()) p.autoPass = S.autoPass;
  S.seat = S.g.human; S.watched = {}; S.mtab = 'shop';
  UI.closeModals();
  pump();
}
function newGame() { startLocal([readName()], readSeed()); }
function hotseatSetup() {
  readName();
  const names = (S.hotNames && S.hotNames.length ? S.hotNames : [S.name, 'Player 2']).slice(0, 8);
  const rows = n => Array.from({ length: n }, (_, i) => `<label>Player ${i + 1} <input data-hot="${i}" maxlength="14" value="${UI.esc(names[i] || (i === 0 ? S.name : 'Player ' + (i + 1)))}"></label>`).join('');
  const m = UI.modal(`<h2>Pass &amp; play</h2><p class="muted">Everyone shares this device. When it's someone else's turn the screen asks you to hand it over. Empty seats are bots.</p>
    <div class="set"><label>Players <select id="hot-n">${[2, 3, 4, 5, 6, 7, 8].map(n => `<option ${n === Math.max(2, names.length) ? 'selected' : ''}>${n}</option>`).join('')}</select></label></div>
    <div class="set hot-names" id="hot-names">${rows(Math.max(2, names.length))}</div>
    <div class="mbtns"><button class="btn big" data-act="hotseat-start">Start</button></div>`);
  m.querySelector('#hot-n').onchange = e => {
    const cur = Array.from(m.querySelectorAll('[data-hot]')).map(i => i.value);
    m.querySelector('#hot-names').innerHTML = rows(+e.target.value);
    m.querySelectorAll('[data-hot]').forEach((i, k) => { if (cur[k]) i.value = cur[k]; });
  };
}
function hotseatStart() {
  const names = Array.from(document.querySelectorAll('[data-hot]')).map((i, k) => (i.value || '').trim().slice(0, 14) || ('Player ' + (k + 1)));
  S.hotNames = names; savePrefs();
  startLocal(names, readSeed());
}
function continueGame() {
  const d = loadSaved(); if (!d) return;
  try { S.g = G.Game.deserialize(d); } catch (e) { console.error(e); UI.toast('Could not load that save.', 'bad'); clearSave(); return; }
  const w = Flow.waiting(S.g);
  S.seat = w.seats.length ? w.seats[0] : S.g.human; S.watched = {};
  UI.closeModals();
  pump();
}

// ---------- acting ----------
function act(a) {
  if (!S.g) return { ok: false };
  if (S.net) return S.net.act(a);
  const r = Flow.apply(S.g, S.seat, a);
  afterAct(r);
  if (r.ok) { saveGame(); if (S.pumping) UI.renderBoard(); pump(); }
  return r;
}
function afterAct(r) { if (!r) return; if (!r.ok) UI.toast(r.err || 'Not allowed.', 'bad'); else if (r.msg) UI.toast(r.msg, r.kind || ''); }
UI.myTurn = () => !!(S.g && S.g.phase === 'shop' && S.g.turnSeat() === S.seat && !S.pumping);

// local table: run bots, battles and round changes until a human has to act, then show that human's screen
async function pump() {
  if (S.pumping) { S.pumpAgain = true; return; }
  S.pumping = true;
  try {
    do {
      S.pumpAgain = false;
      for (;;) {
        if (!S.g || S.net) return;
        const ev = Flow.next(S.g);
        if (!ev) break;
        if (ev.t === 'bot') { if (ev.desc) { UI.renderBoard(); if (S.botDelay) await sleep(S.botDelay); } }
        else if (ev.t === 'autopass' && S.g.humans().length === 1) UI.toast('Nothing you can afford: passing.', 'dim');
        else if (ev.t === 'round') { S.watched = {}; if (!ev.end) S.newRound = true; }
        saveGame();
      }
    } while (S.pumpAgain);
  } finally { S.pumping = false; }
  sync();
}

// show the right screen for the current state (local and online)
function sync() {
  const g = S.g; if (!g) return;
  if (g.phase === 'end') { showEnd(); return; }
  const w = Flow.waiting(g);
  // pass & play: hand the device to whoever the table is waiting on
  if (!S.net && g.humans().length > 1 && w.seats.length && !w.seats.includes(S.seat)) { showCurtain(w.seats[0]); return; }
  if (S.curtain) return;
  UI.renderBoard();
  if (S.newRound) { S.newRound = false; roundIntro(); }
  // close dialogs the state has moved past, then open the one it needs
  const kindOf = () => { const t = UI.topModal(); return t && t.dataset.kind; };
  const picking = g.phase === 'pick' && me().deal && me().deal.length;
  if ((kindOf() === 'results' && g.phase !== 'results') || (kindOf() === 'pick' && !picking)) UI.closeModals();
  if (picking && kindOf() !== 'pick') showPick();
  if (g.phase === 'results') resultsFlow();
}
function showCurtain(seat) {
  S.curtain = seat; UI.closeModals();
  const p = S.g.players[seat], w = Flow.waiting(S.g);
  const what = S.g.phase === 'pick' ? 'choose a Pokémon' : S.g.phase === 'results' ? 'see the round results' : 'take a shop turn';
  $app().innerHTML = `<div class="title"><div class="t-card curtain"><div class="t-logo">Pass to ${UI.esc(p.name)}<small>round ${S.g.round} · ${what}</small></div>
    <p class="t-sub">Hand the device to <b>${UI.esc(p.name)}</b>.${w.seats.length > 1 ? ` Then: ${w.seats.filter(s => s !== seat).map(s => UI.esc(S.g.players[s].name)).join(', ')}.` : ''}</p>
    <div class="t-btns"><button class="btn big" data-act="take-seat" data-seat="${seat}">I'm ${UI.esc(p.name)}</button></div></div></div>`;
}
function takeSeat(seat) { S.curtain = null; S.seat = seat; S.mtab = 'shop'; S.selItem = null; S.hint = ''; sync(); }

function roundIntro() {
  const p = me(), i = p.inc;
  if (!i || S.g.round === 1) { UI.toast(`<b>Round 1</b> — you start with 5 gold at level 2. Choose a starter Pokémon!`); return; }
  const parts = [`5 base`]; if (i.interest) parts.push(`${i.interest} interest`); if (i.streak) parts.push(`${i.streak} streak`); if (i.scale) parts.push(`${i.scale} Red Scale`);
  UI.toast(`<b>Round ${S.g.round}</b> — income <b>+${5 + i.interest + i.streak + i.scale}</b> gold (${parts.join(', ')}) and +2 XP`);
}
function showPick() {
  const g = S.g, deal = me().deal; const ev = g.pickEvent;
  const starter = ev.key === 'starter', bundle = starter || !!ev.bundle, gifts = me().dealItems || [];
  const cards = deal.map((c, i) => `<div class="pickc">${UI.cardDetail(c.spec, c)}${bundle && gifts[i] ? `<div class="pickgift"><small>Comes with (unattached)</small>${UI.itemTile(gifts[i], { noPrice: true })}</div>` : ''}<button class="btn big" data-act="do-pick" data-uid="${c.uid}">Take ${UI.esc(c.spec.name)}</button></div>`).join('');
  const n = deal.length, word = ['zero', 'one', 'two', 'three', 'four', 'five'][n] || n;
  const blurb = bundle && !starter ? `Pick one of ${word}. Each comes with a random item of the same tier that goes to your Items panel. The Pokémon you don't take are shuffled into that tier's market deck; their items go back to the bottom of the item deck.`
    : !bundle ? `${word[0].toUpperCase() + word.slice(1)} cards were dealt to you. Keep one; the others go to the bottom of the pool. It joins your bench (or lineup if there is room).`
    : starter ? 'Choose your starting Pokémon. Each comes with a Tier I item that goes to your Items panel, ready to give to any Pokémon. The other two are shuffled into the Tier I market deck (their items are discarded).'
    : '';
  const m = UI.modal(`<h2>${starter ? 'Choose your starter' : UI.esc(ev.label) + ' pick'}${g.humans().length > 1 ? ` <small class="muted">· ${UI.esc(me().name)}</small>` : ''}</h2><p class="muted">${blurb}</p><div class="pickrow${n > 3 ? ' many' : ''}">${cards}</div>`, { locked: true, closable: false, cls: 'wide' });
  m.dataset.kind = 'pick';
}

// ---------- results ----------
async function resultsFlow() {
  const g = S.g, res = g.results; if (!res) return;
  const key = res.r + ':' + S.seat;
  if (!S.watched[key]) {
    S.watched[key] = 'playing';
    const replay = S.net ? S.net.replay(res.r) : (res.replays || {})[S.seat];
    if (replay) {
      UI.closeModals();
      const mine = res.pairs.find(x => x.a === S.seat || x.b === S.seat);
      const hatch = mine && mine.hatch.find(h => h.player === S.seat);
      const extra = hatch ? `<p class="hatchnote">🥚 Baby synergy: you hatch <b>${UI.esc(hatch.name)}</b> (Tier ${hatch.tier})!</p>` : '';
      await UI.playDuel(replay, { speed: 1, instant: S.duelMode === 'instant', extraHtml: extra });
    }
    S.watched[key] = 'done';
    if (!S.g || S.g.phase !== 'results' || S.g.results.r !== res.r) { sync(); return; }
  }
  if (S.watched[key] !== 'done') return;
  showResults(res);
}
function showResults(res) {
  const g = S.g;
  const rows = res.pairs.map(x => {
    const a = g.players[x.a], b = g.players[x.b]; const w = x.winner;
    const cell = (pl) => `<span class="${w === pl.idx ? 'wn' : w === null ? '' : 'ls'}">${UI.esc(pl.name)}</span>`;
    return `<tr class="${(x.a === S.seat || x.b === S.seat) ? 'you' : ''}"><td>${cell(a)}</td><td class="vs">vs</td><td>${cell(b)}</td><td class="res">${w === null ? 'draw' : (UI.esc(g.players[w].name) + ' wins <b>±' + x.pts + '</b>')}</td></tr>`;
  }).join('');
  const rank = g.standings();
  const tbl = rank.map((p, i) => { const d = p.points - p.hist[p.hist.length - 2]; return `<tr class="${p.idx === S.seat ? 'you' : ''}"><td>${i + 1}</td><td>${UI.esc(p.name)}</td><td>${p.points}</td><td class="${d > 0 ? 'up' : d < 0 ? 'dn' : ''}">${d > 0 ? '+' : ''}${d}</td><td>${p.wins}–${p.losses}</td></tr>`; }).join('');
  const hatches = res.pairs.flatMap(x => x.hatch).filter(h => h.player !== S.seat).map(h => `${UI.esc(g.players[h.player].name)} hatched ${UI.esc(h.name)}`);
  const last = g.round >= 12;
  const waitingOn = g.players.filter(p => !g.isAuto(p) && !p.ready && p.idx !== S.seat).map(p => UI.esc(p.name));
  const btn = !me().ready ? `<button class="btn big" data-act="next-round">${last ? 'See final results' : 'Next round'}</button>`
    : `<div class="muted">Waiting for ${waitingOn.join(', ') || 'the others'}…</div>`;
  const top = UI.topModal();
  const html = `<h2>Round ${res.r} results</h2>
    <table class="rtab"><tbody>${rows}</tbody></table>
    ${hatches.length ? `<p class="muted">${hatches.join(' · ')}</p>` : ''}
    <h4>Standings</h4><table class="rtab st"><thead><tr><th></th><th>Player</th><th>Pts</th><th>Δ</th><th>W–L</th></tr></thead><tbody>${tbl}</tbody></table>
    <div class="mbtns" id="res-btns">${btn}</div>`;
  // refresh in place while waiting on others (online) instead of re-opening the dialog
  if (top && top.dataset.kind === 'results' && top.dataset.r === String(res.r)) { const b = top.querySelector('#res-btns'); if (b) b.innerHTML = btn; return; }
  UI.closeModals();
  const m = UI.modal(html, { locked: true, closable: false, cls: 'results' });
  m.dataset.kind = 'results'; m.dataset.r = res.r;
}
function showEnd() {
  const g = S.g; if (!S.net) clearSave();
  UI.closeModals();
  const rank = g.standings(); const my = rank.findIndex(p => p.idx === S.seat) + 1;
  const ord = n => n + (['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) ? 0 : Math.min(n % 10, 4) % 4 || 0] || 'th');
  const p = me(), multi = g.humans().length > 1;
  const roster = g.lineupCards(p).map(c => UI.tile(c, { price: false, items: false, cls: 'mini' })).join('');
  const kind = q => q.idx === S.seat ? 'You' : q.bot ? UI.esc(q.persona ? q.persona.title : 'Bot') : 'Player';
  const head = multi ? (my === 1 ? `${UI.esc(p.name)} wins!` : `${UI.esc(rank[0].name)} wins!`) : (my === 1 ? 'You won!' : 'Game over');
  $app().innerHTML = `<div class="title"><div class="t-card end">
    <div class="t-logo">${head}<small>${multi ? UI.esc(p.name) + ' finished' : 'you finished'} ${ord(my)} of 8 with ${p.points} points</small></div>
    <table class="rtab st big"><thead><tr><th></th><th>Player</th><th>Points</th><th>Wins</th><th>Level</th><th>Kind</th></tr></thead><tbody>${rank.map((q, i) => `<tr class="${q.idx === S.seat ? 'you' : ''}"><td>${i + 1}</td><td>${UI.esc(q.name)}</td><td>${q.points}</td><td>${q.wins}</td><td>${q.level}</td><td>${kind(q)}</td></tr>`).join('')}</tbody></table>
    <div class="endstats"><span>Evolutions <b>${p.stats.evolve}</b></span><span>KOs <b>${p.stats.kos}</b></span><span>Interest earned <b>${p.stats.interest}</b></span><span>Streak gold <b>${p.stats.streakGold}</b></span><span>Cards bought <b>${p.stats.bought}</b></span><span>Items bought <b>${p.stats.items}</b></span></div>
    <h4>${multi ? UI.esc(p.name) + "'s" : 'Your'} final lineup</h4><div class="endroster">${roster || '—'}</div>
    ${!S.net && multi ? `<div class="t-btns">${g.humans().filter(h => h.idx !== S.seat).map(h => `<button class="btn ghost" data-act="end-view" data-seat="${h.idx}">${UI.esc(h.name)}'s view</button>`).join('')}</div>` : ''}
    <div class="t-btns"><button class="btn big" data-act="to-title">Play again</button></div></div></div>`;
}

// ---------- dialogs ----------
function tradeList(p, preselect) {
  const cards = p.cards.map(c => `<label class="tr-row"><input type="checkbox" data-tr="${c.uid}"> ${UI.portrait(c.spec, 'tiny')} <span>${UI.esc(c.spec.name)}${c.items.length ? ` <small>(+${c.items.length} item${c.items.length > 1 ? 's' : ''} returned to you)</small>` : ''}</span><b>+${c.spec.trade}</b></label>`).join('');
  const items = p.inv.map(i => `<label class="tr-row"><input type="checkbox" data-tr="${i.uid}"> ${UI.itemImg(i.key, 'tiny')} <span>${UI.esc(ITEMS[i.key].name)}</span><b>+${TRADE[i.tier]}</b></label>`).join('');
  if (!cards && !items) return '<div class="muted">You have nothing to trade in.</div>';
  return `<div class="trlist">${cards}${items}</div>`;
}
function openShopCard(tier, slot) {
  const g = S.g, p = me(); const c = g.row[tier][slot]; if (!c) return;
  const locked = GATE[tier] > p.level;
  const evo = g.evolveTargets(p, c);
  const html = `<div class="dlg">
    <div class="dl-left">${UI.cardDetail(c.spec, c)}</div>
    <div class="dl-right">
      ${locked ? `<div class="warn">Tier ${tier} opens at level ${GATE[tier]}. You are level ${p.level}.</div>` : ''}
      ${!UI.myTurn() ? `<div class="warn">It is not your turn yet. You can look, but only act on your turn.</div>` : ''}
      <h4>Buy <span class="muted">· ${UI.coin(c.spec.price)} (trade-in ${c.spec.trade})</span></h4>
      <p class="muted sm">Trade in cards or items as payment (their trade-in value is credited, no change given).</p>
      ${tradeList(p)}
      <div class="mbtns"><button class="btn big" id="dlg-buy">Buy for <span id="dlg-cost">${c.spec.price}</span> gold</button></div>
      ${evo.length ? `<h4>Evolve <span class="muted">· your old card is credited at its full price, items move over</span></h4>${evo.map(o => `<div class="evo-row">${UI.portrait(o.spec, 'tiny')} <span>${UI.esc(o.spec.name)} → ${UI.esc(c.spec.name)}</span><button class="btn" data-act="do-evolve" data-own="${o.uid}">Evolve · ${Math.max(0, c.spec.price - o.spec.price)}g</button></div>`).join('')}` : ''}
      <h4>Churn <span class="muted">· 1 gold</span></h4>
      <div class="mbtns"><button class="btn ghost" data-act="do-churn" ${p.gold < 1 || locked ? 'disabled' : ''}>Discard this card and draw a new one (1g)</button></div>
    </div></div>`;
  const m = UI.modal(html, { cls: 'wide' });
  m.dataset.tier = tier; m.dataset.slot = slot; m.dataset.kind = 'card';
  wireTrade(m, c.spec.price, () => !!(UI.myTurn() && !locked));
}
function openShopItem(slot) {
  const g = S.g, p = me(); const it = g.irow[slot]; if (!it) return;
  const locked = GATE[it.tier] > p.level;
  const html = `<div class="dlg"><div class="dl-left">${UI.itemDetail(it.key, it.tier, it.price)}</div><div class="dl-right">
    ${locked ? `<div class="warn">Tier ${it.tier} items open at level ${GATE[it.tier]}.</div>` : ''}
    ${!UI.myTurn() ? `<div class="warn">It is not your turn yet.</div>` : ''}
    <h4>Buy <span class="muted">· ${UI.coin(it.price)} (trade-in ${TRADE[it.tier]})</span></h4>${tradeList(p)}
    <div class="mbtns"><button class="btn big" id="dlg-buy">Buy for <span id="dlg-cost">${it.price}</span> gold</button></div></div></div>`;
  const m = UI.modal(html, { cls: 'wide' }); m.dataset.slot = slot; m.dataset.kind = 'item';
  wireTrade(m, it.price, () => !!(UI.myTurn() && !locked));
}
function wireTrade(m, price, canAct) {
  const p = me();
  const credit = () => Array.from(m.querySelectorAll('[data-tr]:checked')).reduce((a, i) => { const u = +i.dataset.tr; const c = S.g.cardOf(p, u); return a + (c ? c.spec.trade : TRADE[S.g.itemOf(p, u).tier]); }, 0);
  const upd = () => {
    const cost = Math.max(0, price - credit()); m.querySelector('#dlg-cost').textContent = cost;
    const b = m.querySelector('#dlg-buy'); b.disabled = !canAct() || cost > p.gold;
    b.title = !canAct() ? 'Not available right now' : cost > p.gold ? 'Not enough gold' : '';
  };
  m.addEventListener('change', upd); upd();
  m.querySelector('#dlg-buy').onclick = () => {
    const trade = Array.from(m.querySelectorAll('[data-tr]:checked')).map(i => +i.dataset.tr);
    UI.closeModals();
    act(m.dataset.kind === 'card' ? { t: 'buyCard', tier: m.dataset.tier, slot: +m.dataset.slot, trade } : { t: 'buyItem', slot: +m.dataset.slot, trade });
  };
}
function openOwned(uid) {
  const g = S.g, p = me(); const c = g.cardOf(p, uid); if (!c) return;
  const inLine = p.order.includes(uid); const idx = p.order.indexOf(uid);
  const loose = p.inv.filter(i => !G.isUnholdable(i.key));
  const html = `<div class="dlg"><div class="dl-left">${UI.cardDetail(c.spec, null)}</div><div class="dl-right">
    <h4>Position</h4>
    <div class="mbtns left">${inLine ? `<button class="btn" data-act="to-bench" data-uid="${uid}" data-reopen="1">Send to bench</button><button class="btn" data-act="mv-left" data-uid="${uid}" data-reopen="1" ${idx === 0 ? 'disabled' : ''}>◀ Earlier</button><button class="btn" data-act="mv-right" data-uid="${uid}" data-reopen="1" ${idx === p.order.length - 1 ? 'disabled' : ''}>Later ▶</button>`
      : `<button class="btn" data-act="to-line" data-uid="${uid}" data-reopen="1">Add to lineup</button>`}</div>
    <h4>Items <span class="muted">(${c.items.length}/3)</span></h4>
    <div class="held">${c.items.map(i => `<div class="held-row">${UI.itemImg(i.key)} <div><b>${UI.esc(ITEMS[i.key].name)}</b><br>${UI.rich(ITEMS[i.key].text)}</div><button class="btn ghost" data-act="detach" data-item="${i.uid}" data-uid="${uid}">Remove</button></div>`).join('') || '<div class="muted">No items held.</div>'}</div>
    ${loose.filter(i => !c.items.some(x => x.key === i.key)).length && c.items.length < 3 ? `<h4>Give an item</h4><div class="held">${loose.filter(i => !c.items.some(x => x.key === i.key)).map(i => `<div class="held-row">${UI.itemImg(i.key)} <div><b>${UI.esc(ITEMS[i.key].name)}</b><br>${UI.rich(ITEMS[i.key].text)}</div><button class="btn" data-act="give" data-item="${i.uid}" data-uid="${uid}">Give</button></div>`).join('')}</div>` : ''}
    <p class="muted sm">To sell or swap a Pokémon, trade it in as payment when you buy something.</p>
  </div></div>`;
  UI.closeModals(); const m = UI.modal(html, { cls: 'wide' }); m.dataset.kind = 'owned'; m.dataset.uid = uid;
}
function reopenIfOwned(uid) { const m = UI.topModal(); if (m && m.dataset.kind === 'owned') openOwned(uid); }

function showHint() {
  // ask a simple greedy bot what it would do with your gold and cards (on a copy, nothing happens to your game)
  try {
    const copy = G.Game.deserialize(JSON.parse(JSON.stringify(S.g.serialize())));
    const p = copy.players[S.seat]; p.persona = Object.assign({}, B.PERSONAS[5]);
    B.free(copy, p);
    const d = B.turn(copy, p);
    S.hint = d ? 'A simple bot would: ' + d.replace(p.name, 'you').replace(/^you (\w+)s /, (m, v) => 'you ' + v + ' ') : 'A simple bot would pass here.';
  } catch (e) { S.hint = 'No hint available.'; }
  UI.renderBoard();
}

// ---------- lineup operations (computed here, sent as one new order) ----------
function toLine(uid, pos) {
  const g = S.g, p = me(); const c = g.cardOf(p, uid); if (!c) return false;
  let order = p.order.filter(u => u !== uid);
  if (pos === undefined || pos > order.length) pos = order.length;
  const free = order.map(u => g.cardOf(p, u)).filter(x => !g.hasBow(x)).length < p.level || g.hasBow(c);
  if (free) order.splice(pos, 0, uid);
  else { const occ = p.order[pos]; if (occ && occ !== uid) { order = p.order.slice(); order[pos] = uid; if (p.order.includes(uid)) { order = p.order.filter(u => u !== uid); order.splice(pos, 0, uid); } } else { UI.toast('Your lineup is full: drop onto a Pokémon to swap, or send one to the bench first.', 'bad'); return false; } }
  return act({ t: 'lineup', order }).ok;
}
function toBench(uid) { const p = me(); act({ t: 'lineup', order: p.order.filter(u => u !== uid) }); }
function move(uid, d) { const p = me(); const i = p.order.indexOf(uid), j = i + d; if (i < 0 || j < 0 || j >= p.order.length) return; const o = p.order.slice(); [o[i], o[j]] = [o[j], o[i]]; act({ t: 'lineup', order: o }); }

const isPhone = () => window.matchMedia('(max-width:480px)').matches;
function giveItem(itemUid, cardUid) {
  const r = act({ t: 'attach', item: itemUid, card: cardUid });
  S.selItem = null; return r.ok;
}

// ---------- rules / settings ----------
function showRules() {
  UI.modal(`<h2>How to play</h2><div class="rules">
    <p><b>Goal.</b> Everyone starts with 20 points. After each duel the winner gains, and the loser loses, <i>surviving Pokémon + round bonus</i> (R1–3 +0, R4–6 +1, R7–9 +2, R10–12 +3). Most points after round 12 wins. Nobody is eliminated.</p>
    <p><b>A round.</b> Income → (pick event) → shop → duel. Income is 5 + interest (1 per 5 gold banked, max 3) + streak gold (2 in a row +1, 3 → +2, 4+ → +3, wins or losses) and +2 XP. Round 1 has no income.</p>
    <p><b>The shop.</b> Each tier has a market deck of 32 random Pokémon of that tier, with 4 face up at all times. Players take turns, worst score first, one action each: buy a card or item, evolve, churn (1 gold) or pass. It repeats until everybody has passed. <b>Once you pass, you can't buy anything else this round.</b> A Pokémon can't hold two of the same item. Tier II opens at level 3, III at 4, IV at 5, V at 6. Buying XP (4 gold = 4 XP), moving cards and giving items are free and don't use your turn.</p>
    <p><b>Level and lineup.</b> Level 3 needs 2 XP total, then 6, 14, 30, 56 (levels 4–7). Your lineup holds as many Pokémon as your level. Order matters: your first Pokémon starts the fight and the next one enters when one is knocked out.</p>
    <p><b>Trade-in.</b> You never sell for gold. Instead trade cards or items in as payment: trade-in value I 0, II 2, III 4, IV 7, V 14, Unique 12, Legendary 25 (Unique and Legendary cards can't be bought, so their price shows —). <b>Evolve</b> only if the evolved card is face up in the shop: your old card counts at its full price.</p>
    <p><b>Picks.</b> Before round 1 everyone chooses 1 of 3 Tier I Additional cards as a starter, and before rounds 2, 5 and 8 1 of 3 Additional cards (Tier II/III/IV). Each is bundled with a random item of the same tier (any item, gems included). Every Pokémon you don't take is shuffled into the market deck of its tier; before round 6 a Unique and before round 9 a Legendary, each chosen from 5 cards (no items).</p>
    <p><b>Duels.</b> Each Pokémon attacks, gains 1 charge, and casts its charge power when its charge reaches PP. A faster foe pushes the initiative bar; synergies activate from your whole lineup and stay fixed. Hover any card for details. 5 crit tokens = one ×2 crit.</p>
    <p><b>Shields &amp; overtime.</b> Shield soaks damage but never the last point: every hit deals at least 1 damage to HP. After round 25 of a duel, each Pokémon takes true damage after its own turn (1, then +1 every 5 rounds) that ignores shield.</p>
    <p><b>Baby synergy.</b> After you lose a duel with Baby level I/II/III you hatch a Tier II/III/IV Hatch card.</p>
    <p class="muted">Shortcuts: P pass · X buy XP · Esc close dialogs.</p></div>`, { cls: 'wide' });
}
function showSettings() {
  UI.modal(`<h2>Settings</h2>
    <div class="set"><label>Bot turn speed <select id="set-speed"><option value="420" ${S.botDelay === 420 ? 'selected' : ''}>Normal</option><option value="140" ${S.botDelay === 140 ? 'selected' : ''}>Fast</option><option value="0" ${S.botDelay === 0 ? 'selected' : ''}>Instant</option></select></label>
    <label>Your duels <select id="set-duel"><option value="animated" ${S.duelMode === 'animated' ? 'selected' : ''}>Animated, step by step</option><option value="instant" ${S.duelMode === 'instant' ? 'selected' : ''}>Jump to the result (log stays)</option></select></label>
    <label class="chk"><input type="checkbox" id="set-ap" ${S.autoPass ? 'checked' : ''}> Auto-pass my turn when I can't afford anything</label></div>
    <div class="mbtns"><button class="btn" data-act="save-settings">Save</button><button class="btn ghost" data-act="to-title">Quit to title</button></div>`);
}

// ---------- event delegation ----------
document.addEventListener('click', e => {
  const t = e.target.closest('[data-act]'); if (!t) return;
  const a = t.dataset.act; const uid = t.dataset.uid ? +t.dataset.uid : null;
  switch (a) {
    case 'new-game': newGame(); break;
    case 'continue-game': continueGame(); break;
    case 'hotseat-setup': hotseatSetup(); break;
    case 'hotseat-start': hotseatStart(); break;
    case 'take-seat': takeSeat(+t.dataset.seat); break;
    case 'end-view': S.seat = +t.dataset.seat; showEnd(); break;
    case 'room-create': UI.net && UI.net.create(readName()); break;
    case 'room-join': { const code = (document.getElementById('in-room').value || '').trim().toUpperCase(); if (!code) { UI.toast('Type the room code first.', 'bad'); break; } UI.net && UI.net.join(code, readName()); break; }
    case 'room-rejoin': UI.net && UI.net.rejoin(); break;
    case 'to-title': UI.closeModals(); showTitle(); break;
    case 'show-rules': showRules(); break;
    case 'show-settings': showSettings(); break;
    case 'save-settings': {
      S.botDelay = +document.getElementById('set-speed').value; S.duelMode = document.getElementById('set-duel').value; S.autoPass = document.getElementById('set-ap').checked; savePrefs(); UI.closeModals();
      if (S.g && S.net) act({ t: 'autoPass', on: S.autoPass });
      else if (S.g) { for (const p of S.g.humans()) p.autoPass = S.autoPass; saveGame(); }
      break;
    }
    case 'close-modal': { const m = t.closest('.modal'); if (m && m.close) m.close(); else UI.closeModals(); break; }
    case 'buy-xp': act({ t: 'xp' }); UI.renderBoard(); break;
    case 'pass': if (UI.myTurn()) { S.hint = ''; act({ t: 'pass' }); } break;
    case 'shop-card': if (e.shiftKey && UI.myTurn()) { act({ t: 'buyCard', tier: t.dataset.tier, slot: +t.dataset.slot, trade: [] }); break; } openShopCard(t.dataset.tier, +t.dataset.slot); break;
    case 'shop-item': if (e.shiftKey && UI.myTurn()) { act({ t: 'buyItem', slot: +t.dataset.slot, trade: [] }); break; } openShopItem(+t.dataset.slot); break;
    case 'hint': showHint(); break;
    case 'auto-lineup': act({ t: 'auto' }); UI.renderBoard(); break;
    case 'do-evolve': { const m = t.closest('.modal'); UI.closeModals(); act({ t: 'evolve', tier: m.dataset.tier, slot: +m.dataset.slot, own: +t.dataset.own }); break; }
    case 'do-churn': { const m = t.closest('.modal'); UI.closeModals(); act({ t: 'churn', tier: m.dataset.tier, slot: +m.dataset.slot }); break; }
    case 'do-pick': act({ t: 'pick', uid }); break;
    case 'next-round': act({ t: 'ready' }); break;
    case 'card-open': {
      if (S.selItem) { giveItem(S.selItem, uid); UI.renderBoard(); break; }
      openOwned(uid); break;
    }
    case 'sel-item': {
      S.selItem = S.selItem === +t.dataset.item ? null : +t.dataset.item;
      // on phones the Items tab hides the lineup, so jump there to pick the holder
      const tabbed = S.selItem && S.mtab === 'items' && isPhone();
      if (tabbed) { S.mtab = 'lineup'; window.scrollTo(0, 0); }
      UI.renderBoard(); if (S.selItem) UI.toast(tabbed ? 'Now tap a Pokémon to give it the item.' : 'Now click a Pokémon to give it the item.', 'dim'); break;
    }
    case 'mtab': S.mtab = t.dataset.tab; window.scrollTo(0, 0); UI.renderBoard(); break;
    case 'item-card': e.stopPropagation(); act({ t: 'detach', item: +t.dataset.item }); UI.renderBoard(); break;
    case 'to-bench': e.stopPropagation(); toBench(uid); UI.renderBoard(); reopenIfOwned(uid); break;
    case 'to-line': e.stopPropagation(); toLine(uid); UI.renderBoard(); reopenIfOwned(uid); break;
    case 'mv-left': e.stopPropagation(); move(uid, -1); UI.renderBoard(); reopenIfOwned(uid); break;
    case 'mv-right': e.stopPropagation(); move(uid, 1); UI.renderBoard(); reopenIfOwned(uid); break;
    case 'detach': act({ t: 'detach', item: +t.dataset.item }); UI.renderBoard(); openOwned(uid); break;
    case 'give': if (giveItem(+t.dataset.item, uid)) { UI.renderBoard(); openOwned(uid); } break;
  }
});
document.addEventListener('keydown', e => {
  if (!S.g || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (document.body.classList.contains('in-duel')) return;
  if (e.key === 'Escape') { const m = UI.topModal(); if (m && m.close && !m.querySelector('.m-x') === false) m.close(); }
  if (e.key === 'p' && UI.myTurn() && !document.body.classList.contains('has-modal')) document.querySelector('[data-act="pass"]') && document.querySelector('[data-act="pass"]').click();
  if (e.key === 'x' && !document.body.classList.contains('has-modal')) document.querySelector('[data-act="buy-xp"]') && document.querySelector('[data-act="buy-xp"]').click();
});

// drag and drop (mouse via HTML5 drag events, touch via the long-press handlers below; both drop through dropOn)
let dragData = null;
const DROP_ZONES = '[data-zone],.vcard[data-uid],.tile[data-uid],.slot[data-drop]';
function dragFrom(el) {
  const c = el && el.closest && el.closest('[data-uid][draggable="true"]'), i = el && el.closest && el.closest('[data-item][draggable="true"]');
  return i ? { t: 'i', u: +i.dataset.item, el: i } : c ? { t: 'c', u: +c.dataset.uid, el: c } : null;
}
function markOver(z) { document.querySelectorAll('.over').forEach(x => x !== z && x.classList.remove('over')); if (z) z.classList.add('over'); }
function endDrag() { dragData = null; document.body.classList.remove('dragging'); markOver(null); }
// apply a drop of dd onto element el; returns true when something happened
function dropOn(dd, el) {
  if (!dd || !el || !S.g) return false;
  if (dd.t === 'i') {
    const tgt = el.closest('.vcard[data-uid],.tile[data-uid],.slot[data-card]'); if (!tgt) return false;
    const cu = +(tgt.dataset.uid || tgt.dataset.card); if (giveItem(dd.u, cu)) UI.renderBoard();
    return true;
  }
  const slot = el.closest('[data-zone="line"]'), bench = el.closest('[data-zone="bench"]'), lend = el.closest('[data-zone="line-end"]');
  if (slot) toLine(dd.u, +slot.dataset.pos);
  else if (bench) toBench(dd.u);
  else if (lend) toLine(dd.u);
  else return false;
  UI.renderBoard(); return true;
}
document.addEventListener('dragstart', e => {
  const d = dragFrom(e.target); if (!d) return;
  dragData = { t: d.t, u: d.u };
  e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', JSON.stringify(dragData)); } catch (_) { }
  document.body.classList.add('dragging');
});
document.addEventListener('dragend', endDrag);
document.addEventListener('dragover', e => {
  if (!dragData) return;
  const z = e.target.closest(DROP_ZONES); if (!z) return;
  e.preventDefault(); markOver(z);
});
document.addEventListener('drop', e => {
  if (!dragData) return;
  const dd = dragData; endDrag();
  if (dropOn(dd, e.target)) e.preventDefault();
});

// touch: hold ~250ms to pick a card/item up (a quick swipe still scrolls), drag a ghost, lift to drop.
// On phones, hovering the tab bar while dragging switches tabs so items can reach the lineup.
// Move/end listeners go on the touched node itself: touch events keep targeting it even after a board re-render
// (bot turns re-render often) detaches it, and a detached node's events never bubble to document.
const touchDrag = { timer: 0, src: null, x: 0, y: 0, active: false, ghost: null, tabTimer: 0, tabKey: null, node: null, raf: 0 };
function touchReset() {
  clearInterval(touchDrag.raf);
  clearTimeout(touchDrag.timer); clearTimeout(touchDrag.tabTimer);
  if (touchDrag.ghost) touchDrag.ghost.remove();
  if (touchDrag.active) endDrag();
  const n = touchDrag.node;
  if (n) { n.removeEventListener('touchmove', onTouchMove); n.removeEventListener('touchend', onTouchEnd); n.removeEventListener('touchcancel', touchReset); }
  Object.assign(touchDrag, { timer: 0, src: null, active: false, ghost: null, tabTimer: 0, tabKey: null, node: null, raf: 0 });
}
document.addEventListener('touchstart', e => {
  touchReset();
  if (e.touches.length !== 1 || document.body.classList.contains('in-duel')) return;
  const d = dragFrom(e.target); if (!d) return;
  const t = e.touches[0], n = e.target; Object.assign(touchDrag, { src: d, x: t.clientX, y: t.clientY, node: n });
  n.addEventListener('touchmove', onTouchMove, { passive: false }); n.addEventListener('touchend', onTouchEnd, { passive: false }); n.addEventListener('touchcancel', touchReset);
  touchDrag.timer = setTimeout(() => {
    touchDrag.active = true; dragData = { t: d.t, u: d.u }; document.body.classList.add('dragging');
    const r = d.el.getBoundingClientRect(), gh = d.el.cloneNode(true);
    gh.classList.add('drag-ghost'); gh.removeAttribute('data-act'); gh.style.width = r.width + 'px';
    touchDrag.ghost = gh; document.body.appendChild(gh); moveGhost(touchDrag.x, touchDrag.y);
    if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) { }
    touchDrag.raf = setInterval(edgeScroll, 16);
  }, 250);
}, { passive: true });
// the page can't scroll mid-drag, so holding near the top edge or just above the tab bar scrolls it
function edgeScroll() {
  if (!touchDrag.active) return;
  const bar = document.querySelector('.mtabs'), bottom = bar && getComputedStyle(bar).display !== 'none' ? bar.getBoundingClientRect().top : innerHeight, y = touchDrag.y, EDGE = 70;
  const v = y < EDGE ? -(EDGE - y) / 5 : (y > bottom - EDGE && y < bottom) ? (y - (bottom - EDGE)) / 5 : 0;
  if (v) { const before = scrollY; window.scrollBy(0, v); if (scrollY !== before) { const el = document.elementFromPoint(touchDrag.x, y); markOver(el && el.closest(DROP_ZONES)); } }
}
function moveGhost(x, y) { const gh = touchDrag.ghost; if (gh) gh.style.transform = `translate(${x - gh.offsetWidth / 2}px, ${y - gh.offsetHeight * 0.6}px) scale(.85)`; }
function onTouchMove(e) {
  if (!touchDrag.src) return;
  const t = e.touches[0];
  if (!touchDrag.active) {
    // moved before the hold finished: it's a scroll, let the browser have it
    if (Math.hypot(t.clientX - touchDrag.x, t.clientY - touchDrag.y) > 10) touchReset();
    return;
  }
  e.preventDefault(); touchDrag.x = t.clientX; touchDrag.y = t.clientY; moveGhost(t.clientX, t.clientY);
  const el = document.elementFromPoint(t.clientX, t.clientY);
  const tab = el && el.closest('.mtab');
  if (tab) {
    markOver(tab);
    if (touchDrag.tabKey !== tab.dataset.tab) {
      clearTimeout(touchDrag.tabTimer); touchDrag.tabKey = tab.dataset.tab;
      touchDrag.tabTimer = setTimeout(() => { if (S.mtab !== touchDrag.tabKey) { S.mtab = touchDrag.tabKey; window.scrollTo(0, 0); UI.renderBoard(); } }, 350);
    }
    return;
  }
  clearTimeout(touchDrag.tabTimer); touchDrag.tabKey = null;
  markOver(el && el.closest(DROP_ZONES));
}
function onTouchEnd(e) {
  if (!touchDrag.active) { touchReset(); return; }
  e.preventDefault(); // no click after a drag
  const dd = dragData, el = document.elementFromPoint(touchDrag.x, touchDrag.y);
  touchReset();
  if (el && !el.closest('.mtab')) dropOn(dd, el);
}

// ---------- boot ----------
UI.initTip();
if (document.readyState === 'loading') window.addEventListener('DOMContentLoaded', showTitle); else showTitle();
// shared with js/net.js (online rooms) and the tests
UI.api = { newGame, startLocal, pump, sync, act, afterAct, showTitle, openShopCard, openOwned, toLine, toBench, giveItem, saveGame, loadSaved, me, showResults };
})();
