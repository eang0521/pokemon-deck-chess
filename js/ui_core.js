/* PAC digital — UI helpers: icons, text, card rendering, tooltips. */
(function () {
'use strict';
const D = window.PAC_DATA, E = window.PACEngine, ITEMS = D.items;
const UI = window.UI = { sel: null, selItem: null };

const TIERCOL = { UNIQUE: '#1f9d9a', LEGENDARY: '#c2392b', I: '#848b89', II: '#4f9d5d', III: '#3f79c6', IV: '#8a5bc8', V: '#d9a61e' };
const TYPECOL = { NORMAL: '#c9c3a8', GRASS: '#8ed06a', FIRE: '#f6a35b', WATER: '#78b8f0', ELECTRIC: '#f7d85a', FIGHTING: '#d9805a', PSYCHIC: '#f58fb8',
  DARK: '#8b7f78', STEEL: '#b8c2cc', GROUND: '#d8c07a', POISON: '#c28ad8', DRAGON: '#8f8af2', FIELD: '#d8b878', MONSTER: '#a0b86a',
  HUMAN: '#e8b9a0', AQUATIC: '#6fc9d8', BUG: '#b8d65a', FLYING: '#b8c6f5', FLORA: '#a0dc88', ROCK: '#cfc09a', GHOST: '#a591d0',
  FAIRY: '#f7b6d8', ICE: '#bfeaf7', FOSSIL: '#d8b98a', SOUND: '#c8d8a0', ARTIFICIAL: '#b8c8d8', BABY: '#fbe3b8', LIGHT: '#fff2a8',
  WILD: '#e8a870', AMORPHOUS: '#c8a8d8', GOURMET: '#f0c070' };
UI.TIERCOL = TIERCOL; UI.TYPECOL = TYPECOL;
const esc = UI.esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s.charAt(0) + s.slice(1).toLowerCase();
UI.cap = cap;
const tierOf = spec => spec.pool === 'unique' ? 'UNIQUE' : spec.pool === 'legendary' ? 'LEGENDARY' : spec.tier;
UI.tierOf = tierOf;
const tierLabel = spec => spec.pool === 'unique' ? 'UNIQUE' : spec.pool === 'legendary' ? 'LEGENDARY' : spec.pool === 'hatch' ? `HATCH · ${spec.tier}` : spec.pool === 'add' ? `ADD · ${spec.tier}` : `TIER ${spec.tier}`;
UI.tierLabel = tierLabel;

// ---------- crit tokens wording ----------
function qh(p) { const v = Math.round(p / 10) / 2; return v < 1 ? 0.5 : Math.floor(v); }
UI.critText = function (t) {
  return t.replace(/\+?(\d+)% crit( chance)?( \(every \d+\w* attack crits\))?/g, (m, p) => { const n = qh(+p); return n < 1 ? 'a crit token every 2nd attack' : `+${n} crit token${n > 1 ? 's' : ''} per attack`; });
};

// ---------- keywords ----------
const KW = [
  [/\b(PARALYZED?|PARALYZES|PARALYSIS)\b/g, 'para'], [/\b(BURN(?:ED|S)?)\b/g, 'burn'], [/\b(POISON(?:ED|S)?)\b/g, 'pois'], [/\b(FREEZE|FROZEN|FREEZES)\b/g, 'ice'],
  [/\b(SLEEP|ASLEEP)\b/g, 'sleep'], [/\b(CONFUSE|CONFUSED|CONFUSES|CONFUSION)\b/g, 'conf'], [/\b(CHARM|CHARMED|CHARMS)\b/g, 'charm'], [/\b(WOUND|WOUNDED)\b/g, 'wound'],
  [/\b(FLINCH|FLINCHED|FLINCHES)\b/g, 'flinch'], [/\b(FATIGUE|FATIGUED)\b/g, 'fat'], [/\b(ARMOR BROKEN|ARMOR BREAK)\b/g, 'arm'],
  [/\b(SHIELD|SHIELDS)\b/g, 'shield'], [/\b(PROTECT|PROTECTED)\b/g, 'prot'], [/\b(SPLASH)\b/g, 'splash'], [/\b(TRUE)\b/g, 'true'], [/\b(SPECIAL)\b/g, 'spec'],
  [/\b(PHYSICAL)\b/g, 'phys'], [/\b(SWARM)\b/g, 'swarm'], [/\b(UNHOLDABLE)\b/g, 'unh'],
];
UI.rich = function (text) {
  let s = esc(UI.critText(text || ''));
  s = s.replace(/✦(\d+)/g, '<span class="ap" title="Grows with this Pokémon\'s AP">$1✦</span>');
  for (const [re, cls] of KW) s = s.replace(re, m => `<b class="kw ${cls}">${m}</b>`);
  return s;
};

// ---------- icons ----------
UI.stat = (k, v) => `<span class="stat" title="${{ HP: 'Health', ATK: 'Attack', DEF: 'Defense', SPE_DEF: 'Special Defense', SPEED: 'Speed', PP: 'Charge needed (PP)', AP: 'Ability Power' }[k]}"><img class="ic" src="assets/s/${k}.png" alt="${k}">${v}</span>`;
UI.coin = n => `<span class="coin"><img class="ic" src="assets/s/COIN.svg" alt="">${n}</span>`;
UI.typeIcon = (t, sz) => `<img class="ty" ${sz ? `style="width:${sz}px;height:${sz}px"` : ''} src="assets/t/${t}.svg" alt="${t}" title="${cap(t)}">`;
UI.typeChip = (t, extra) => `<span class="tchip" style="--tc:${TYPECOL[t] || '#999'}">${UI.typeIcon(t, 14)}${cap(t)}${extra ? ' ' + extra : ''}</span>`;
UI.portrait = (spec, cls) => `<img class="por ${cls || ''}" src="assets/p/${spec.dex}.png" alt="${esc(spec.name)}" loading="lazy">`;
UI.itemImg = (key, cls) => `<img class="itm ${cls || ''}" src="assets/i/${key}.png" alt="" onerror="this.style.visibility='hidden'">`;

// ---------- cards ----------
function costBadge(spec) {
  if (spec.pool === 'hatch') return `<span class="cost" title="Hatch cards cannot be bought; trade-in value ${spec.trade}">— (${spec.trade})</span>`;
  if (spec.pool === 'unique' || spec.pool === 'legendary') return `<span class="cost" title="Picked, not bought. Trade-in value ${spec.trade}">— (${spec.trade})</span>`;
  return `<span class="cost" title="Price (trade-in value)">${UI.coin(spec.price)} <i>(${spec.trade})</i></span>`;
}
UI.costBadge = costBadge;
const statLine = s => UI.stat('HP', s.hp) + UI.stat('ATK', s.atk) + UI.stat('DEF', s.df) + UI.stat('SPE_DEF', s.sdf) + UI.stat('SPEED', s.spd) + UI.stat('PP', s.pp);
UI.statLine = statLine;
function itemDots(inst) {
  if (!inst || !inst.items) return '';
  const out = [];
  for (let i = 0; i < 3; i++) {
    const it = inst.items[i];
    out.push(it ? `<span class="slot full" data-act="item-card" data-item="${it.uid}" data-tip="item:${it.key}">${UI.itemImg(it.key)}</span>` : `<span class="slot" data-drop="slot" data-card="${inst.uid}"></span>`);
  }
  return `<div class="islots">${out.join('')}</div>`;
}
UI.itemDots = itemDots;

// compact horizontal tile (shop / bench / pick lists)
UI.tile = function (inst, o) {
  o = o || {}; const s = inst.spec;
  const cls = ['tile', 'tier-' + tierOf(s), o.cls || '', o.disabled ? 'dim' : '', o.selected ? 'sel' : ''].join(' ');
  const attrs = `data-uid="${inst.uid}" data-sid="${s.id}" ${o.act ? `data-act="${o.act}"` : ''} ${o.extra || ''} data-tip="card:${inst.uid}:${s.id}"`;
  return `<div class="${cls}" style="--tcol:${TIERCOL[tierOf(s)]}" ${attrs} ${o.drag ? 'draggable="true"' : ''}>
    <div class="t-por">${UI.portrait(s)}</div>
    <div class="t-main">
      <div class="t-name">${esc(s.name)}<span class="t-types">${s.types.map(t => UI.typeIcon(t, 14)).join('')}</span></div>
      <div class="t-stats">${statLine(s)}</div>
      <div class="t-pow"><b>${esc(s.abname)}</b> ${esc(UI.shortText(s.text))}</div>
    </div>
    <div class="t-foot"><span class="t-tier">${tierLabel(s)}</span>${o.price === false ? '' : costBadge(s)}</div>
    ${o.items ? itemDots(inst) : ''}
    ${o.badge ? `<div class="badge">${o.badge}</div>` : ''}
  </div>`;
};
UI.shortText = t => (t || '').replace(/\s+/g, ' ').slice(0, 74) + ((t || '').length > 74 ? '…' : '');

// vertical board card (lineup)
UI.vcard = function (inst, o) {
  o = o || {}; const s = inst.spec;
  const cls = ['vcard', 'tier-' + tierOf(s), o.cls || '', o.selected ? 'sel' : ''].join(' ');
  return `<div class="${cls}" style="--tcol:${TIERCOL[tierOf(s)]}" data-uid="${inst.uid}" data-sid="${s.id}" ${o.act ? `data-act="${o.act}"` : ''} draggable="true" data-tip="card:${inst.uid}:${s.id}">
    <div class="v-head"><span class="v-name">${esc(s.name)}</span><span class="t-types">${s.types.map(t => UI.typeIcon(t, 14)).join('')}</span></div>
    <div class="v-por">${UI.portrait(s, 'big')}</div>
    <div class="v-stats">${statLine(s)}</div>
    <div class="v-pow"><b>${esc(s.abname)}</b> ${UI.rich(UI.shortText(s.text))}</div>
    ${o.noItems ? '' : itemDots(inst)}
    <div class="v-foot"><span class="t-tier">${tierLabel(s)}</span>${costBadge(s)}</div>
  </div>`;
};

UI.itemTile = function (it, o) {
  o = o || {}; const def = ITEMS[it.key];
  const tier = it.tier;
  return `<div class="itile tier-${tier} ${o.cls || ''} ${o.disabled ? 'dim' : ''} ${o.selected ? 'sel' : ''}" style="--tcol:${TIERCOL[tier]}" data-item="${it.uid}" ${o.act ? `data-act="${o.act}"` : ''} ${o.extra || ''} data-tip="itm:${it.uid}:${it.key}:${it.tier}:${it.price}" ${o.drag ? 'draggable="true"' : ''}>
    <div class="i-img">${UI.itemImg(it.key)}</div>
    <div class="i-main"><div class="i-name">${esc(def.name)}</div><div class="i-txt">${UI.rich(itemShort(it))}</div></div>
    ${o.noPrice ? '' : `<div class="i-foot"><span class="t-tier">ITEM · ${tier}</span><span class="cost">${UI.coin(it.price)} <i>(${E.DATA && 0 || window.PACGame.TRADE[tier]})</i></span></div>`}
  </div>`;
};
function itemText(it) { return it.text || ITEMS[it.key].text; }
function itemShort(it) { const t = UI.critText(ITEMS[it.key].text || ''); return t.length > 80 ? t.slice(0, 79) + '…' : t; }
UI.itemText = itemText;

// ---------- detail HTML (tooltip + dialog) ----------
UI.synBlock = function (spec) {
  return spec.types.map(t => {
    const th = D.syn_th[t] || [2, 3, 4]; const sy = D.syn[t];
    return `<div class="syn-row"><span style="--tc:${TYPECOL[t]}" class="tchip">${UI.typeIcon(t, 14)}${cap(t)}</span> <span class="th">${th.join(' / ')}</span>${sy ? `<span class="theme">${esc(sy.theme)}</span>` : ''}</div>`;
  }).join('');
};
UI.dishFor = function (spec) {
  if (!spec.types.includes('GOURMET')) return '';
  const d = D.dishes.find(x => (x.cards || '').split(', ').some(n => n.replace(/[^a-z0-9]/gi, '').toLowerCase() === spec.name.replace(/[^a-z0-9]/gi, '').toLowerCase()));
  if (!d) return '';
  return `<div class="dishbox"><b>${esc(d.dish)}</b> served to the next card: I ${UI.rich(d.lv[0])} · II ${UI.rich(d.lv[1])} · III ${UI.rich(d.lv[2])}</div>`;
};
UI.cardDetail = function (spec, inst, o) {
  o = o || {};
  const its = inst && inst.items && inst.items.length ? `<div class="d-items">${inst.items.map(i => `<div class="d-item">${UI.itemImg(i.key)}<div><b>${esc(ITEMS[i.key].name)}</b><br>${UI.rich(ITEMS[i.key].text)}</div></div>`).join('')}</div>` : '';
  return `<div class="detail tier-${tierOf(spec)}" style="--tcol:${TIERCOL[tierOf(spec)]}">
    <div class="d-head">${UI.portrait(spec, 'huge')}<div><div class="d-name">${esc(spec.name)}</div><div class="d-tier">${tierLabel(spec)} · ${'★'.repeat(spec.stars)} · ${costBadge(spec)}</div>
    <div class="d-stats">${statLine(spec)}</div></div></div>
    <div class="d-pow"><b>${esc(spec.abname)}</b> <span class="pp">needs ${spec.pp} charge</span><br>${UI.rich(spec.text)}</div>
    ${UI.dishFor(spec)}
    <div class="d-syn">${UI.synBlock(spec)}</div>${its}</div>`;
};
UI.itemDetail = function (key, tier, price) {
  const def = ITEMS[key];
  return `<div class="detail tier-${tier}" style="--tcol:${TIERCOL[tier] || '#888'}"><div class="d-head">${UI.itemImg(key, 'huge')}<div><div class="d-name">${esc(def.name)}</div><div class="d-tier">${def.cat}${tier ? ' · ITEM ' + tier : ''}${price != null ? ' · ' + UI.coin(price) + ' <i>(' + window.PACGame.TRADE[tier] + ')</i>' : ''}</div></div></div><div class="d-pow">${UI.rich(def.text)}</div></div>`;
};

// ---------- tooltip ----------
const tip = () => document.getElementById('tip');
UI.tipHtml = function (code) {
  const [k, a, b, c, d] = code.split(':');
  if (k === 'card') { const spec = D.cards[+b]; const inst = UI.findInst && UI.findInst(+a); return UI.cardDetail(spec, inst); }
  if (k === 'item') return UI.itemDetail(a, null, null);
  if (k === 'itm') return UI.itemDetail(b, c, +d);
  if (k === 'txt') return `<div class="detail"><div class="d-pow">${UI.rich(decodeURIComponent(a))}</div></div>`;
  return '';
};
UI.initTip = function () {
  let cur = null, touchedAt = 0;
  // taps fire mouseover too, and on a phone the tooltip would then stick over the board: skip it for touch
  document.addEventListener('touchstart', () => { touchedAt = Date.now(); cur = null; tip().hidden = true; }, { passive: true });
  document.addEventListener('mouseover', e => {
    if (Date.now() - touchedAt < 1000) return;
    const el = e.target.closest && e.target.closest('[data-tip]');
    if (!el || el === cur) { if (!el) { cur = null; tip().hidden = true; } return; }
    cur = el; const html = UI.tipHtml(el.dataset.tip); if (!html) { tip().hidden = true; return; }
    tip().innerHTML = html; tip().hidden = false; place(e);
  });
  document.addEventListener('mousemove', e => { if (!tip().hidden) place(e); });
  document.addEventListener('mouseout', e => { if (!e.relatedTarget || !(e.relatedTarget.closest && e.relatedTarget.closest('[data-tip]'))) { cur = null; tip().hidden = true; } });
  function place(e) {
    const t = tip(); const w = t.offsetWidth, h = t.offsetHeight; let x = e.clientX + 18, y = e.clientY + 14;
    if (x + w > innerWidth - 8) x = e.clientX - w - 18; if (y + h > innerHeight - 8) y = innerHeight - h - 8; if (y < 8) y = 8; if (x < 8) x = 8;
    t.style.left = x + 'px'; t.style.top = y + 'px';
  }
};

// ---------- toasts & modals ----------
UI.toast = function (msg, kind) {
  const r = document.getElementById('toast-root'); const el = document.createElement('div');
  el.className = 'toast ' + (kind || ''); el.innerHTML = msg; r.appendChild(el);
  setTimeout(() => el.classList.add('out'), 2600); setTimeout(() => el.remove(), 3100);
};
UI.modal = function (html, o) {
  o = o || {}; const root = document.getElementById('modal-root');
  const el = document.createElement('div'); el.className = 'modal ' + (o.cls || '');
  el.innerHTML = `<div class="m-back" ${o.locked ? '' : 'data-act="close-modal"'}></div><div class="m-box" role="dialog">${o.closable === false ? '' : '<button class="m-x" data-act="close-modal" aria-label="Close">×</button>'}${html}</div>`;
  root.appendChild(el); document.body.classList.add('has-modal');
  el.close = () => { el.remove(); if (!root.children.length) document.body.classList.remove('has-modal'); if (o.onClose) o.onClose(); };
  return el;
};
UI.closeModals = function () { const root = document.getElementById('modal-root'); root.innerHTML = ''; document.body.classList.remove('has-modal'); };
UI.topModal = function () { const r = document.getElementById('modal-root'); return r.lastElementChild; };
})();
