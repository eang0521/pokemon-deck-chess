/* PAC digital — flow control: title, new game, shop loop, dialogs, picks, results, save/load. */
(function () {
'use strict';
const UI = window.UI, D = window.PAC_DATA, G = window.PACGame, B = window.PACBots, E = window.PACEngine, ITEMS = D.items;
const S = UI.state;
const { GATE, TIERS, TRADE } = G;
const SAVE_KEY = 'pac-digital-save-v1', PREF_KEY = 'pac-digital-prefs-v1';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const me = () => S.g.players[S.g.human];
const $app = () => document.getElementById('app');

// ---------- preferences ----------
function loadPrefs() { try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch (e) { return {}; } }
function savePrefs() { try { localStorage.setItem(PREF_KEY, JSON.stringify({ botDelay: S.botDelay, autoPass: S.autoPass, duelMode: S.duelMode, name: S.name })); } catch (e) { } }
Object.assign(S, { botDelay: 420, autoPass: true, duelMode: 'animated', name: 'You' }, loadPrefs());

// ---------- save / load ----------
function saveGame() {
  if (!S.g || S.g.phase === 'end') return;
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(S.g.serialize())); } catch (e) { /* storage unavailable */ }
}
function loadSaved() { try { const j = localStorage.getItem(SAVE_KEY); return j ? JSON.parse(j) : null; } catch (e) { return null; } }
function clearSave() { try { localStorage.removeItem(SAVE_KEY); } catch (e) { } }

// ---------- title ----------
function showTitle() {
  S.g = null; UI.closeModals();
  const saved = loadSaved();
  $app().innerHTML = `<div class="title">
    <div class="t-card">
      <div class="t-logo">Pokémon Auto Chess<small>the board game · digital prototype</small></div>
      <p class="t-sub">One human against seven bots. Twelve rounds of shopping, building and duels. Most points after round 12 wins.</p>
      <div class="t-form">
        <label>Your name <input id="in-name" maxlength="14" value="${UI.esc(S.name)}"></label>
        <label>Seed <small>(optional, same seed = same shop &amp; bots)</small> <input id="in-seed" placeholder="random" inputmode="numeric"></label>
      </div>
      <div class="t-btns">
        <button class="btn big" data-act="new-game">New game</button>
        ${saved ? `<button class="btn big alt" data-act="continue-game">Continue · round ${saved.round}</button>` : ''}
        <button class="btn ghost" data-act="show-rules">How to play</button>
      </div>
      <div class="t-bots"><h4>Your opponents <small>(personalities are shuffled between seats each game)</small></h4>
        ${B.PERSONAS.map(p => `<div class="bp"><b>${UI.esc(p.name)}</b> <i>${UI.esc(p.title)}</i><br><span>${UI.esc(p.blurb)}</span></div>`).join('')}</div>
      <p class="t-foot">Personal, non-commercial prototype. Works offline: just keep this folder together. Progress autosaves in this browser.</p>
    </div></div>`;
}

function newGame() {
  const name = (document.getElementById('in-name').value || 'You').trim().slice(0, 14) || 'You';
  const seedStr = document.getElementById('in-seed').value.trim();
  const seed = seedStr ? (parseInt(seedStr, 10) >>> 0) : (Math.floor(Math.random() * 4294967295) >>> 0);
  S.name = name; savePrefs();
  const tmp = E.makeRng(seed ^ 0x9e3779b9);
  const personas = tmp.shuffle(B.PERSONAS.slice());
  const defs = [{ name }];
  for (let i = 0; i < 7; i++) {
    const ps = Object.assign({}, personas[i]);
    if (ps.key === 'specialist') { const ts = Object.keys(D.syn_th).filter(t => t !== 'BABY' && t !== 'AMORPHOUS'); ps.fav = [ts[tmp.int(ts.length)], ts[tmp.int(ts.length)]]; }
    defs.push({ name: ps.name, persona: ps });
  }
  S.g = new G.Game(seed, { players: defs, human: 0 });
  S.g.say(`New game · seed ${seed}`, 'sys');
  UI.closeModals();
  startRound();
}
function continueGame() {
  const d = loadSaved(); if (!d) return;
  try { S.g = G.Game.deserialize(d); } catch (e) { console.error(e); UI.toast('Could not load that save.', 'bad'); clearSave(); return; }
  UI.closeModals();
  UI.renderBoard();
  resumeFlow();
}

// ---------- round flow ----------
function startRound() {
  const g = S.g;
  g.beginRound();
  UI.renderBoard();
  saveGame();
  roundIntro();
  resumeFlow();
}
function roundIntro() {
  const p = me(), i = p.inc;
  if (!i || S.g.round === 1) { UI.toast(`<b>Round 1</b> — you start with 5 gold at level 2. Choose a starter Pokémon!`); return; }
  const parts = [`5 base`]; if (i.interest) parts.push(`${i.interest} interest`); if (i.streak) parts.push(`${i.streak} streak`); if (i.scale) parts.push(`${i.scale} Red Scale`);
  UI.toast(`<b>Round ${S.g.round}</b> — income <b>+${5 + i.interest + i.streak + i.scale}</b> gold (${parts.join(', ')}) and +2 XP`);
}
function resumeFlow() {
  const g = S.g;
  if (g.phase === 'pick') { showPick(); return; }
  if (g.phase === 'shop') { advanceShop(); return; }
  if (g.phase === 'end') { showEnd(); return; }
}
function showPick() {
  const g = S.g, deal = g.pendingPick || me().deal; const ev = g.pickEvent;
  const starter = ev.key === 'starter', bundle = starter || !!ev.bundle, gifts = me().dealItems || [];
  const cards = deal.map((c, i) => `<div class="pickc">${UI.cardDetail(c.spec, c)}${bundle && gifts[i] ? `<div class="pickgift"><small>Comes with (unattached)</small>${UI.itemTile(gifts[i], { noPrice: true })}</div>` : ''}<button class="btn big" data-act="do-pick" data-uid="${c.uid}">Take ${UI.esc(c.spec.name)}</button></div>`).join('');
  const n = deal.length, word = ['zero', 'one', 'two', 'three', 'four', 'five'][n] || n;
  const blurb = bundle && !starter ? `Pick one of ${word}. Each comes with a random item of the same tier that goes to your Items panel. The others return to the bottom of the pool and their items are discarded.`
    : !bundle ? `${word[0].toUpperCase() + word.slice(1)} cards were dealt to you. Keep one; the others go to the bottom of the pool. It joins your bench (or lineup if there is room).`
    : starter ? 'Choose your starting Pokémon. Each comes with a Tier I item that goes to your Items panel, ready to give to any Pokémon. The other two (and their items) go to the discard pile.'
    : '';
  UI.modal(`<h2>${starter ? 'Choose your starter' : UI.esc(ev.label) + ' pick'}</h2><p class="muted">${blurb}</p><div class="pickrow${n > 3 ? ' many' : ''}">${cards}</div>`, { locked: true, closable: false, cls: 'wide' });
}

// ---------- shop loop ----------
function canDoAnything() {
  const g = S.g, p = me();
  const credit = p.cards.reduce((a, c) => a + c.spec.trade, 0) + p.inv.filter(i => !G.isUnholdable(i.key)).reduce((a, i) => a + TRADE[i.tier], 0) + p.inv.filter(i => G.isUnholdable(i.key)).reduce((a, i) => a + TRADE[i.tier], 0);
  if (p.gold >= 1) {
    // churn possible if any row card is visible and unlocked
    for (const t of TIERS) if (GATE[t] <= p.level && g.row[t].some(Boolean)) return true;
  }
  for (const t of TIERS) {
    if (GATE[t] > p.level) continue;
    for (const c of g.row[t]) {
      if (!c) continue;
      if (Math.max(0, c.spec.price - credit) <= p.gold) return true;
      for (const o of g.evolveTargets(p, c)) if (Math.max(0, c.spec.price - o.spec.price) <= p.gold) return true;
    }
  }
  for (const it of g.irow) if (it && GATE[it.tier] <= p.level && Math.max(0, it.price - credit) <= p.gold) return true;
  return false;
}
async function advanceShop() {
  const g = S.g; if (S.running) return; S.running = true;
  try {
    for (;;) {
      if (g.phase !== 'shop') break;
      const r = g.stepShop();
      if (r.done) { S.humanTurn = false; UI.renderBoard(); await sleep(200); S.running = false; await doBattles(); return; }
      if (r.human) {
        if (S.autoPass && !canDoAnything()) { g.humanPass(); UI.toast('Nothing you can afford: passing.', 'dim'); continue; }
        S.humanTurn = true; UI.renderBoard(); S.running = false; return;
      }
      S.humanTurn = false;
      if (r.desc) { UI.renderBoard(); if (S.botDelay) await sleep(S.botDelay); }
    }
  } finally { S.running = false; }
}
function afterHuman(acted) {
  S.hint = ''; S.humanTurn = false; S.g.humanDid(acted); saveGame(); UI.renderBoard(); advanceShop();
}

// ---------- battles ----------
async function doBattles() {
  const g = S.g, p = me();
  // top up an unfilled lineup silently
  const before = g.lineupCards(p).length; g.autoFill(p);
  if (g.lineupCards(p).length > before) UI.toast('Free lineup slots were filled from your bench.', 'dim');
  UI.closeModals();
  const results = g.runBattles();
  UI.renderBoard();
  const mine = results.pairs.find(x => x.a === g.human || x.b === g.human);
  if (results.replay) {
    const hatch = mine && mine.hatch.find(h => h.player === g.human);
    const extra = hatch ? `<p class="hatchnote">🥚 Baby synergy: you hatch <b>${UI.esc(hatch.card.spec.name)}</b> (Tier ${hatch.card.spec.tier})!</p>` : '';
    await UI.playDuel(results.replay, { speed: 1, instant: S.duelMode === 'instant', extraHtml: extra });
  } else if (mine && mine.forfeit !== undefined) { /* unused */ }
  showResults(results);
}
function showResults(res) {
  const g = S.g;
  const rows = res.pairs.map(x => {
    const a = g.players[x.a], b = g.players[x.b]; const w = x.winner;
    const cell = (pl) => `<span class="${w === pl.idx ? 'wn' : w === null ? '' : 'ls'}">${UI.esc(pl.name)}</span>`;
    return `<tr class="${(x.a === g.human || x.b === g.human) ? 'you' : ''}"><td>${cell(a)}</td><td class="vs">vs</td><td>${cell(b)}</td><td class="res">${w === null ? 'draw' : (UI.esc(g.players[w].name) + ' wins <b>±' + x.pts + '</b>')}</td></tr>`;
  }).join('');
  const rank = g.standings();
  const tbl = rank.map((p, i) => { const d = p.points - p.hist[p.hist.length - 2]; return `<tr class="${p.idx === g.human ? 'you' : ''}"><td>${i + 1}</td><td>${UI.esc(p.name)}</td><td>${p.points}</td><td class="${d > 0 ? 'up' : d < 0 ? 'dn' : ''}">${d > 0 ? '+' : ''}${d}</td><td>${p.wins}–${p.losses}</td></tr>`; }).join('');
  const hatches = res.pairs.flatMap(x => x.hatch).filter(h => h.player !== g.human).map(h => `${UI.esc(g.players[h.player].name)} hatched ${UI.esc(h.card.spec.name)}`);
  const last = g.round >= 12;
  UI.modal(`<h2>Round ${res.r} results</h2>
    <table class="rtab"><tbody>${rows}</tbody></table>
    ${hatches.length ? `<p class="muted">${hatches.join(' · ')}</p>` : ''}
    <h4>Standings</h4><table class="rtab st"><thead><tr><th></th><th>Player</th><th>Pts</th><th>Δ</th><th>W–L</th></tr></thead><tbody>${tbl}</tbody></table>
    <div class="mbtns"><button class="btn big" data-act="next-round">${last ? 'See final results' : 'Next round'}</button></div>`, { locked: true, closable: false, cls: 'results' });
}
function nextRound() {
  UI.closeModals();
  const g = S.g;
  g.endRound();
  if (g.phase === 'end') { clearSave(); showEnd(); return; }
  UI.renderBoard(); saveGame(); roundIntro(); resumeFlow();
}
function showEnd() {
  const g = S.g; clearSave();
  const rank = g.standings(); const my = rank.findIndex(p => p.idx === g.human) + 1;
  const ord = n => n + (['th', 'st', 'nd', 'rd'][(n % 100 > 10 && n % 100 < 14) ? 0 : Math.min(n % 10, 4) % 4 || 0] || 'th');
  const p = me();
  const roster = g.lineupCards(p).map(c => UI.tile(c, { price: false, items: false, cls: 'mini' })).join('');
  $app().innerHTML = `<div class="title"><div class="t-card end">
    <div class="t-logo">${my === 1 ? 'You won!' : 'Game over'}<small>you finished ${ord(my)} of 8 with ${p.points} points</small></div>
    <table class="rtab st big"><thead><tr><th></th><th>Player</th><th>Points</th><th>Wins</th><th>Level</th><th>Kind</th></tr></thead><tbody>${rank.map((q, i) => `<tr class="${q.idx === g.human ? 'you' : ''}"><td>${i + 1}</td><td>${UI.esc(q.name)}</td><td>${q.points}</td><td>${q.wins}</td><td>${q.level}</td><td>${q.persona ? UI.esc(q.persona.title) : 'You'}</td></tr>`).join('')}</tbody></table>
    <div class="endstats"><span>Evolutions <b>${p.stats.evolve}</b></span><span>KOs <b>${p.stats.kos}</b></span><span>Interest earned <b>${p.stats.interest}</b></span><span>Streak gold <b>${p.stats.streakGold}</b></span><span>Cards bought <b>${p.stats.bought}</b></span><span>Items bought <b>${p.stats.items}</b></span></div>
    <h4>Your final lineup</h4><div class="endroster">${roster || '—'}</div>
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
      ${!S.humanTurn ? `<div class="warn">It is not your turn yet. You can look, but only act on your turn.</div>` : ''}
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
  wireTrade(m, c.spec.price, () => !!(S.humanTurn && !locked));
}
function openShopItem(slot) {
  const g = S.g, p = me(); const it = g.irow[slot]; if (!it) return;
  const locked = GATE[it.tier] > p.level;
  const html = `<div class="dlg"><div class="dl-left">${UI.itemDetail(it.key, it.tier, it.price)}</div><div class="dl-right">
    ${locked ? `<div class="warn">Tier ${it.tier} items open at level ${GATE[it.tier]}.</div>` : ''}
    ${!S.humanTurn ? `<div class="warn">It is not your turn yet.</div>` : ''}
    <h4>Buy <span class="muted">· ${UI.coin(it.price)} (trade-in ${TRADE[it.tier]})</span></h4>${tradeList(p)}
    <div class="mbtns"><button class="btn big" id="dlg-buy">Buy for <span id="dlg-cost">${it.price}</span> gold</button></div></div></div>`;
  const m = UI.modal(html, { cls: 'wide' }); m.dataset.slot = slot; m.dataset.kind = 'item';
  wireTrade(m, it.price, () => !!(S.humanTurn && !locked));
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
    const uids = Array.from(m.querySelectorAll('[data-tr]:checked')).map(i => +i.dataset.tr);
    const r = m.dataset.kind === 'card' ? S.g.buyCard(p, m.dataset.tier, +m.dataset.slot, uids) : S.g.buyItem(p, +m.dataset.slot, uids);
    if (!r.ok) { UI.toast(r.err, 'bad'); return; }
    UI.closeModals();
    UI.toast(m.dataset.kind === 'card' ? `Bought <b>${UI.esc(r.card.spec.name)}</b>${r.card.spec.pool === 'core' ? '' : ''}` : `Bought <b>${UI.esc(ITEMS[r.item.key].name)}</b>`);
    S.g.say(`${p.name} buys ${m.dataset.kind === 'card' ? r.card.spec.name : ITEMS[r.item.key].name}`, 'me');
    afterHuman(true);
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
    ${loose.length && c.items.length < 3 ? `<h4>Give an item</h4><div class="held">${loose.map(i => `<div class="held-row">${UI.itemImg(i.key)} <div><b>${UI.esc(ITEMS[i.key].name)}</b><br>${UI.rich(ITEMS[i.key].text)}</div><button class="btn" data-act="give" data-item="${i.uid}" data-uid="${uid}">Give</button></div>`).join('')}</div>` : ''}
    <p class="muted sm">To sell or swap a Pokémon, trade it in as payment when you buy something.</p>
  </div></div>`;
  UI.closeModals(); const m = UI.modal(html, { cls: 'wide' }); m.dataset.kind = 'owned'; m.dataset.uid = uid;
}
function reopenIfOwned(uid) { const m = UI.topModal(); if (m && m.dataset.kind === 'owned') openOwned(uid); }

function quickBuy(tier, slot) {
  const r = S.g.buyCard(me(), tier, slot, []);
  if (!r.ok) { UI.toast(r.err, 'bad'); return; }
  UI.toast(`Bought <b>${UI.esc(r.card.spec.name)}</b>`); S.g.say(`${me().name} buys ${r.card.spec.name}`, 'me'); afterHuman(true);
}
function quickBuyItem(slot) {
  const r = S.g.buyItem(me(), slot, []);
  if (!r.ok) { UI.toast(r.err, 'bad'); return; }
  UI.toast(`Bought <b>${UI.esc(ITEMS[r.item.key].name)}</b>`); S.g.say(`${me().name} buys ${ITEMS[r.item.key].name}`, 'me'); afterHuman(true);
}
function showHint() {
  // ask a simple greedy bot what it would do with your gold and cards (on a copy, nothing happens to your game)
  try {
    const copy = G.Game.deserialize(JSON.parse(JSON.stringify(S.g.serialize())));
    const p = copy.players[copy.human]; p.persona = Object.assign({}, B.PERSONAS[5]);
    B.free(copy, p);
    const d = B.turn(copy, p);
    S.hint = d ? 'A simple bot would: ' + d.replace(p.name, 'you').replace(/^you (\w+)s /, (m, v) => 'you ' + v + ' ') : 'A simple bot would pass here.';
  } catch (e) { S.hint = 'No hint available.'; }
  UI.renderBoard();
}

// ---------- lineup operations ----------
function toLine(uid, pos) {
  const g = S.g, p = me(); const c = g.cardOf(p, uid); if (!c) return false;
  let order = p.order.filter(u => u !== uid);
  if (pos === undefined || pos > order.length) pos = order.length;
  const free = order.map(u => g.cardOf(p, u)).filter(x => !g.hasBow(x)).length < p.level || g.hasBow(c);
  if (free) order.splice(pos, 0, uid);
  else { const occ = p.order[pos]; if (occ && occ !== uid) { order = p.order.slice(); order[pos] = uid; if (p.order.includes(uid)) { order = p.order.filter(u => u !== uid); order.splice(pos, 0, uid); } } else { UI.toast('Your lineup is full: drop onto a Pokémon to swap, or send one to the bench first.', 'bad'); return false; } }
  const r = g.setLineup(p, order); if (!r.ok) { UI.toast(r.err, 'bad'); return false; }
  return true;
}
function toBench(uid) { const p = me(); S.g.setLineup(p, p.order.filter(u => u !== uid)); }
function move(uid, d) { const p = me(); const i = p.order.indexOf(uid), j = i + d; if (i < 0 || j < 0 || j >= p.order.length) return; const o = p.order.slice(); [o[i], o[j]] = [o[j], o[i]]; p.order = o; }

const isPhone = () => window.matchMedia('(max-width:480px)').matches;
function giveItem(itemUid, cardUid) {
  const r = S.g.attachItem(me(), itemUid, cardUid);
  if (!r.ok) UI.toast(r.err, 'bad'); S.selItem = null; return r.ok;
}

// ---------- rules / settings ----------
function showRules() {
  UI.modal(`<h2>How to play</h2><div class="rules">
    <p><b>Goal.</b> Everyone starts with 20 points. After each duel the winner gains, and the loser loses, <i>surviving Pokémon + round bonus</i> (R1–3 +0, R4–6 +1, R7–9 +2, R10–12 +3). Most points after round 12 wins. Nobody is eliminated.</p>
    <p><b>A round.</b> Income → (pick event) → shop → duel. Income is 5 + interest (1 per 5 gold banked, max 3) + streak gold (2 in a row +1, 3 → +2, 4+ → +3, wins or losses) and +2 XP. Round 1 has no income.</p>
    <p><b>The shop.</b> Players take turns, worst score first, one action each: buy a card or item, evolve, churn (1 gold) or pass. It repeats until everybody passes. Tier II opens at level 3, III at 4, IV at 5, V at 6. Buying XP (4 gold = 4 XP), moving cards and giving items are free and don't use your turn.</p>
    <p><b>Level and lineup.</b> Level 3 needs 2 XP total, then 6, 14, 30, 56 (levels 4–7). Your lineup holds as many Pokémon as your level. Order matters: your first Pokémon starts the fight and the next one enters when one is knocked out.</p>
    <p><b>Trade-in.</b> You never sell for gold. Instead trade cards or items in as payment: trade-in value I 0, II 2, III 4, IV 7, V 14, Unique 15, Legendary 30. <b>Evolve</b> only if the evolved card is face up in the shop: your old card counts at its full price.</p>
    <p><b>Picks.</b> Before round 1 everyone chooses 1 of 3 Tier I starters, each with a free Tier I item (never a gem: gems can't be held); the ones nobody takes are discarded. Before rounds 2, 5 and 8 you pick 1 of 3 Additional cards (Tier II/III/IV), each bundled with a random item of the same tier; before round 6 a Unique and before round 9 a Legendary, each chosen from 5 cards (no items).</p>
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
  const act = t.dataset.act; const uid = t.dataset.uid ? +t.dataset.uid : null;
  const g = S.g;
  switch (act) {
    case 'new-game': newGame(); break;
    case 'continue-game': continueGame(); break;
    case 'to-title': clearSave && 0; UI.closeModals(); showTitle(); break;
    case 'show-rules': showRules(); break;
    case 'show-settings': showSettings(); break;
    case 'save-settings': S.botDelay = +document.getElementById('set-speed').value; S.duelMode = document.getElementById('set-duel').value; S.autoPass = document.getElementById('set-ap').checked; savePrefs(); UI.closeModals(); break;
    case 'close-modal': { const m = t.closest('.modal'); if (m && m.close) m.close(); else UI.closeModals(); break; }
    case 'buy-xp': { const r = g.buyXp(me()); if (!r.ok) UI.toast(r.err, 'bad'); else { UI.toast(r.levelUp ? `Level up! Lineup size is now ${me().level}.` : '+4 XP', r.levelUp ? 'good' : ''); } UI.renderBoard(); saveGame(); break; }
    case 'pass': if (S.humanTurn) { S.hint = ''; S.humanTurn = false; g.humanPass(); UI.renderBoard(); saveGame(); advanceShop(); } break;
    case 'shop-card': if (e.shiftKey && S.humanTurn) { quickBuy(t.dataset.tier, +t.dataset.slot); break; } openShopCard(t.dataset.tier, +t.dataset.slot); break;
    case 'shop-item': if (e.shiftKey && S.humanTurn) { quickBuyItem(+t.dataset.slot); break; } openShopItem(+t.dataset.slot); break;
    case 'hint': showHint(); break;
    case 'auto-lineup': { const p = me(); B.arrange(g, p); B.attach(g, p); UI.renderBoard(); saveGame(); UI.toast('Lineup and items arranged.', 'dim'); break; }
    case 'do-evolve': {
      const m = t.closest('.modal'); const r = g.evolveCard(me(), m.dataset.tier, +m.dataset.slot, +t.dataset.own);
      if (!r.ok) { UI.toast(r.err, 'bad'); break; }
      UI.closeModals(); UI.toast(`<b>${UI.esc(r.from.spec.name)}</b> evolves into <b>${UI.esc(r.card.spec.name)}</b>!`, 'good'); g.say(`${me().name} evolves ${r.from.spec.name} into ${r.card.spec.name}`, 'me'); afterHuman(true); break;
    }
    case 'do-churn': { const m = t.closest('.modal'); const r = g.churn(me(), m.dataset.tier, +m.dataset.slot); if (!r.ok) { UI.toast(r.err, 'bad'); break; } UI.closeModals(); UI.toast('Churned a card (1 gold).'); afterHuman(true); break; }
    case 'do-pick': { const r = g.humanPick(uid); if (r.ok) { UI.closeModals(); UI.toast(`You picked <b>${UI.esc(r.card.spec.name)}</b>`, 'good'); UI.renderBoard(); saveGame(); advanceShop(); } break; }
    case 'next-round': nextRound(); break;
    case 'card-open': {
      if (S.selItem) { if (giveItem(S.selItem, uid)) { UI.renderBoard(); saveGame(); } else UI.renderBoard(); break; }
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
    case 'item-card': { e.stopPropagation(); const r = g.detachItem(me(), +t.dataset.item); if (r.ok) { UI.renderBoard(); saveGame(); } break; }
    case 'to-bench': e.stopPropagation(); toBench(uid); UI.renderBoard(); reopenIfOwned(uid); saveGame(); break;
    case 'to-line': e.stopPropagation(); toLine(uid); UI.renderBoard(); reopenIfOwned(uid); saveGame(); break;
    case 'mv-left': e.stopPropagation(); move(uid, -1); UI.renderBoard(); reopenIfOwned(uid); saveGame(); break;
    case 'mv-right': e.stopPropagation(); move(uid, 1); UI.renderBoard(); reopenIfOwned(uid); saveGame(); break;
    case 'detach': g.detachItem(me(), +t.dataset.item); UI.renderBoard(); openOwned(uid); saveGame(); break;
    case 'give': if (giveItem(+t.dataset.item, uid)) { UI.renderBoard(); openOwned(uid); saveGame(); } break;
  }
});
document.addEventListener('keydown', e => {
  if (!S.g || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (document.body.classList.contains('in-duel')) return;
  if (e.key === 'Escape') { const m = UI.topModal(); if (m && m.close && !m.querySelector('.m-x') === false) m.close(); }
  if (e.key === 'p' && S.humanTurn && !document.body.classList.contains('has-modal')) document.querySelector('[data-act="pass"]') && document.querySelector('[data-act="pass"]').click();
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
    const cu = +(tgt.dataset.uid || tgt.dataset.card); if (giveItem(dd.u, cu)) { UI.renderBoard(); saveGame(); }
    return true;
  }
  const slot = el.closest('[data-zone="line"]'), bench = el.closest('[data-zone="bench"]'), lend = el.closest('[data-zone="line-end"]');
  if (slot) toLine(dd.u, +slot.dataset.pos);
  else if (bench) toBench(dd.u);
  else if (lend) toLine(dd.u);
  else return false;
  UI.renderBoard(); saveGame(); return true;
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
// exposed for tests
UI.api = { newGame, startRound, advanceShop, doBattles, nextRound, showTitle, openShopCard, openOwned, toLine, toBench, giveItem, afterHuman, saveGame, loadSaved, me };
})();
