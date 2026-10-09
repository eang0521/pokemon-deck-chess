/* PAC digital — main board rendering (shop, lineup, bench, items, standings). */
(function () {
'use strict';
const UI = window.UI, D = window.PAC_DATA, G = window.PACGame, ITEMS = D.items;
const { GATE, TIERS, XP_CUM, MAX_LEVEL, TRADE } = G;

UI.state = { g: null, me: null, busy: false, botDelay: 420, selItem: null, autoPass: true, sel: null, mtab: 'shop' };
const S = UI.state;

UI.findInst = function (uid) {
  const g = S.g; if (!g) return null;
  for (const p of g.players) { for (const c of p.cards) if (c.uid === uid) return c; if (p.deal) for (const c of p.deal) if (c.uid === uid) return c; }
  for (const t of TIERS) for (const c of g.row[t]) if (c && c.uid === uid) return c;
  return null;
};
const me = () => S.g.players[S.g.human];

// ---------- derived info ----------
UI.synergies = function (p) {
  const g = S.g; const cards = g.lineupCards(p); const cnt = {}, seen = new Set();
  for (const c of cards) {
    const ts = new Set(c.spec.types); for (const i of c.items) { const t = ITEMS[i.key].flags.type; if (t) ts.add(t); }
    for (const t of ts) { const k = t + '|' + c.spec.family; if (!seen.has(k)) { seen.add(k); cnt[t] = (cnt[t] || 0) + 1; } }
  }
  for (const k of g.gemKeys(p)) { const t = ITEMS[k].flags.gem; cnt[t] = (cnt[t] || 0) + 1; }
  // dragon level I: second synergies of dragons count twice (shown approximately in the count)
  const out = [];
  for (const t in cnt) {
    const th = D.syn_th[t] || [2, 3, 4]; const lv = th.filter(x => cnt[t] >= x).length; const next = th.find(x => x > cnt[t]);
    out.push({ t, n: cnt[t], lv, next, th });
  }
  return out.sort((a, b) => (b.lv - a.lv) || (b.n - a.n) || a.t.localeCompare(b.t));
};
UI.nextXp = function (p) { return p.level >= MAX_LEVEL ? null : XP_CUM[p.level + 1]; };
function evolveBadge(p, h) { return g().evolveTargets(p, h).length ? 'evo' : ''; }
const g = () => S.g;

// ---------- pieces ----------
function topBar() {
  const G_ = g(), p = me();
  const nx = UI.nextXp(p), prev = XP_CUM[p.level];
  const pct = nx ? Math.min(100, Math.round((p.xp - prev) / (nx - prev) * 100)) : 100;
  const inc = 5 + G_.interest(p) + G_.streakGold(p);
  const st = p.streak > 0 ? `<span class="streak win" title="Win streak">▲ ${p.streak}</span>` : p.streak < 0 ? `<span class="streak loss" title="Losing streak (pays gold too)">▼ ${-p.streak}</span>` : `<span class="streak">–</span>`;
  const bonus = G.bonusOf(G_.round || 1);
  return `<header class="topbar">
    <div class="tb-round"><b>Round ${G_.round}</b><span> / 12</span><small>duel bonus +${bonus}${(() => { const o = G_.opponentOf(G_.human, G_.round); return o ? ' · vs ' + UI.esc(o.name) + ' (' + o.points + ')' : ''; })()}</small></div>
    <div class="tb-phase" id="phase-label">${phaseLabel()}</div>
    <div class="tb-stats">
      <div class="tb-stat gold" title="Gold. Interest: +1 per 5 gold banked (max +3)">${UI.coin(p.gold)}<small>next income +${inc}</small></div>
      <div class="tb-stat lvl" title="Level = lineup size. XP: ${p.xp}${nx ? ' / ' + nx : ''}"><b>Lv ${p.level}</b><div class="xpbar"><i style="width:${pct}%"></i></div><small>${nx ? `${p.xp}/${nx} XP` : 'max'}</small></div>
      <button class="btn xp" data-act="buy-xp" ${p.gold < 4 || p.level >= MAX_LEVEL ? 'disabled' : ''} title="Buy 4 XP for 4 gold (free action)">+4 XP · 4g</button>
      <div class="tb-stat" title="Streak (winning and losing streaks both pay gold: 2 = +1, 3 = +2, 4+ = +3)">${st}<small>+${G_.streakGold(p)}g</small></div>
      <div class="tb-stat pts" title="Points. Everyone starts at 20.">${p.points}<small>points</small></div>
    </div>
    <div class="tb-btns"><button class="btn ghost" data-act="show-rules" title="Rules">?</button><button class="btn ghost" data-act="show-settings" title="Settings">⚙</button></div>
  </header>`;
}
function phaseLabel() {
  const G_ = g();
  if (G_.phase === 'shop') {
    const sh = G_.shop; const cur = sh && sh.order[sh.pos];
    if (S.humanTurn) return `<span class="turn you">Your turn</span> buy, evolve, churn or pass`;
    if (cur && cur.bot) return `<span class="turn">${UI.esc(cur.name)}'s turn…</span>`;
    return 'Shop';
  }
  return { duel: 'Battle', results: 'Round results', pick: 'Pick a card', end: 'Game over' }[G_.phase] || '';
}
function shopRows() {
  const G_ = g(), p = me();
  const mine = S.humanTurn;
  const rows = TIERS.map(t => {
    const locked = GATE[t] > p.level;
    const tiles = G_.row[t].map((c, i) => {
      if (!c) return `<div class="tile empty">sold out</div>`;
      const ev = !locked && G_.evolveTargets(p, c).length;
      return UI.tile(c, { act: 'shop-card', extra: `data-tier="${t}" data-slot="${i}"`, disabled: locked, cls: 'shop' + (ev ? ' canevo' : ''), badge: ev ? 'Evolve ▲' : '' });
    }).join('');
    return `<div class="trow ${locked ? 'locked' : ''}" style="--tcol:${UI.TIERCOL[t]}"><div class="tlabel"><b>${t}</b><small>${locked ? 'Lv ' + GATE[t] : 'open'}</small></div><div class="tiles">${tiles}</div></div>`;
  }).join('');
  const irow = G_.irow.map((it, i) => it ? UI.itemTile(it, { act: 'shop-item', extra: `data-slot="${i}"`, disabled: GATE[it.tier] > p.level }) : '<div class="itile empty">—</div>').join('');
  const sh = G_.shop; const ord = sh ? sh.order.map((q, i) => `<span class="${i < sh.pos ? 'done' : i === sh.pos ? 'cur' : ''} ${q.idx === G_.human ? 'you' : ''}">${UI.esc(q.name)}</span>`).join('') : '';
  const actionHint = (mine ? `<div class="turnbar you"><span>Your action: click a card or item <small>(Shift+click = quick buy)</small></span><span><button class="btn ghost" data-act="hint" title="Ask what a simple bot would do now">Hint</button> <button class="btn" data-act="pass">Pass</button></span></div>`
    : `<div class="turnbar">${G_.phase === 'shop' ? 'Waiting for the other players…' : ''}</div>`) + `<div class="hintbox" id="hintbox">${S.hint ? UI.esc(S.hint) : ''}</div>` + (ord ? `<div class="turnorder">Order this sweep: ${ord}</div>` : '');
  return `<section class="shop"><h3>Shop <small>shared · worst score buys first</small></h3>${actionHint}${rows}<h3 class="ih">Items <small>separate row</small></h3><div class="irow">${irow}</div></section>`;
}
function synStrip() {
  const syn = UI.synergies(me());
  if (!syn.length) return `<div class="synstrip empty">Field Pokémon that share a type to activate synergies.</div>`;
  return `<div class="synstrip">${syn.map(s => {
    const sy = D.syn[s.t]; const txt = s.lv ? (sy ? sy.lv[Math.min(s.lv, sy.lv.length) - 1] : '') : (sy ? 'Next: ' + sy.lv[0] : '');
    const pips = s.th.map((x, i) => `<i class="${i < s.lv ? 'on' : ''}"></i>`).join('');
    return `<div class="syn ${s.lv ? 'act' : ''}" style="--tc:${UI.TYPECOL[s.t]}" data-tip="txt:${encodeURIComponent(UI.cap(s.t) + ' ' + s.n + '/' + s.th.join('/') + ' — ' + (sy ? sy.theme : '') + '. ' + txt)}">${UI.typeIcon(s.t, 16)}<b>${s.n}</b><span class="pips">${pips}</span>${s.next ? `<small>→${s.next}</small>` : ''}</div>`;
  }).join('')}</div>`;
}
function lineupPanel() {
  const G_ = g(), p = me();
  const cards = G_.lineupCards(p);
  const slots = G_.lineupCap(p);
  let html = '';
  for (let i = 0; i < Math.max(slots, cards.length); i++) {
    const c = cards[i];
    if (c) {
      html += `<div class="lslot" data-zone="line" data-pos="${i}"><span class="lnum">${i + 1}</span>${UI.vcard(c, { act: 'card-open', selected: S.sel === c.uid })}
        <div class="lctl"><button data-act="mv-left" data-uid="${c.uid}" title="Earlier in the order">◀</button><button data-act="to-bench" data-uid="${c.uid}" title="Send to bench">⤓</button><button data-act="mv-right" data-uid="${c.uid}" title="Later in the order">▶</button></div></div>`;
    } else html += `<div class="lslot emptyslot" data-zone="line" data-pos="${i}"><span class="lnum">${i + 1}</span><div class="ph">empty</div></div>`;
  }
  return `<div class="panel lineup"><h3>Lineup <small>order = who fights first · ${cards.filter(c => !G_.hasBow(c)).length}/${p.level}</small><span class="lineup-btns"><button class="btn ghost" data-act="auto-lineup" title="Pick the best lineup and hand out loose items automatically">Auto lineup</button></span></h3>${synStrip()}<div class="lrow" data-zone="line-end">${html}</div></div>`;
}
function benchPanel() {
  const G_ = g(), p = me(); const b = G_.benchCards(p);
  return `<div class="panel bench" data-zone="bench"><h3>Bench <small>${b.length} · cards here do nothing in battle</small></h3><div class="brow">${b.map(c => `<div class="bwrap">${UI.tile(c, { act: 'card-open', items: true, drag: true })}<button class="tolineup" data-act="to-line" data-uid="${c.uid}" title="Add to lineup">▲</button></div>`).join('') || '<div class="ph">Bench is empty. Bought cards join your lineup while there is room.</div>'}</div></div>`;
}
function invPanel() {
  const G_ = g(), p = me();
  const loose = p.inv.filter(i => !G.isUnholdable(i.key)), beside = p.inv.filter(i => G.isUnholdable(i.key));
  const t = i => UI.itemTile(i, { act: 'sel-item', noPrice: false, selected: S.selItem === i.uid, drag: true, cls: 'mini' });
  return `<div class="panel inv" data-zone="inv"><h3>Items <small>click an item, then a Pokémon (or drag). Max 3 per Pokémon.</small></h3>
    <div class="irow2">${loose.map(t).join('') || '<div class="ph">No loose items.</div>'}</div>
    ${beside.length ? `<h4>Beside your lineup <small>always active, no slot</small></h4><div class="irow2">${beside.map(i => UI.itemTile(i, { cls: 'mini', noPrice: false })).join('')}</div>` : ''}</div>`;
}
function standings() {
  const G_ = g();
  const rank = G_.players.slice().sort((a, b) => (b.points - a.points) || (b.wins - a.wins));
  return `<div class="panel stand"><h3>Standings</h3><table><tbody>${rank.map((p, i) => `<tr class="${p.idx === G_.human ? 'you' : ''}"><td class="rk">${i + 1}</td><td class="nm" title="${UI.esc(p.persona ? p.persona.title + ': ' + p.persona.blurb : 'You')}">${UI.esc(p.name)}${p.persona ? `<small>${UI.esc(p.persona.title)}</small>` : '<small>you</small>'}</td><td class="lv">L${p.level}</td><td class="st">${p.streak > 1 ? '<span class="win">▲' + p.streak + '</span>' : p.streak < -1 ? '<span class="loss">▼' + -p.streak + '</span>' : ''}</td><td class="pt">${p.points}</td></tr>`).join('')}</tbody></table></div>`;
}
// phone-only tab bar (hidden on wider screens by CSS); S.mtab picks which column shows
function mobileTabs() {
  const G_ = g(), p = me();
  const n = G_.lineupCards(p).filter(c => !G_.hasBow(c)).length, loose = p.inv.filter(i => !G.isUnholdable(i.key)).length;
  const tab = (k, label, extra, cls) => `<button class="mtab ${S.mtab === k ? 'on' : ''} ${cls || ''}" data-act="mtab" data-tab="${k}">${label}${extra ? `<small>${extra}</small>` : ''}</button>`;
  return `<nav class="mtabs">${tab('shop', 'Shop', S.humanTurn ? 'your turn' : '', S.humanTurn ? 'turn' : '')}${tab('lineup', 'Lineup', `${n}/${p.level}`)}${tab('items', 'Items', loose ? String(loose) : '', loose ? 'has' : '')}${tab('table', 'Table', '')}</nav>`;
}
function logPanel() {
  const G_ = g();
  const lines = G_.log.slice(-40).reverse();
  return `<div class="panel logp"><h3>Table talk</h3><div class="log">${lines.map(l => `<div class="ll ${l.kind}"><b>R${l.r}</b> ${UI.esc(l.msg)}</div>`).join('') || '<div class="ph">Nothing yet.</div>'}</div></div>`;
}

UI.renderBoard = function () {
  const app = document.getElementById('app');
  const G_ = g();
  if (!G_) return;
  const scroll = { shop: (app.querySelector('.colshop') || {}).scrollTop, mine: (app.querySelector('.mine') || {}).scrollTop, side: (app.querySelector('.side') || {}).scrollTop };
  app.innerHTML = `<div class="game">${topBar()}<div class="cols" data-mtab="${S.mtab}"><div class="colshop">${shopRows()}</div><div class="mine">${lineupPanel()}${benchPanel()}${invPanel()}</div><aside class="side">${standings()}${logPanel()}</aside></div>${mobileTabs()}</div>`;
  const m = app.querySelector('.mine'); if (m && scroll.mine) m.scrollTop = scroll.mine;
  const sh = app.querySelector('.colshop'); if (sh && scroll.shop) sh.scrollTop = scroll.shop;
  const sd = app.querySelector('.side'); if (sd && scroll.side) sd.scrollTop = scroll.side;
};
})();
