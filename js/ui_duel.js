/* PAC digital — animated duel viewer. Plays the recorded snapshots turn by turn. */
(function () {
'use strict';
const UI = window.UI, D = window.PAC_DATA, ITEMS = D.items;
const ROMAN = ['', 'I', 'II', 'III', 'IV'];
const STCOL = { para: ['PARALYZED', '#e5c33b'], burn: ['BURNED', '#ef7b3a'], freeze: ['FROZEN', '#7fd3ee'], sleep: ['ASLEEP', '#9a8cd8'], confuse: ['CONFUSED', '#d97ed1'], charm: ['CHARMED', '#f08fb5'],
  wound: ['WOUNDED', '#c0392b'], flinch: ['FLINCHED', '#b0a9a0'], fatigue: ['FATIGUED', '#8c9aa6'], armor: ['ARMOR BROKEN', '#a58b6a'], poison: ['POISONED', '#a95bc7'] };

UI.playDuel = function (replay, opts) {
  opts = opts || {};
  return new Promise(resolve => {
    const meS = replay.me, opS = 1 - meS;
    const sides = [replay.sides[meS], replay.sides[opS]];
    const snapSide = (snap, k) => snap.sides[k === 0 ? meS : opS];
    const el = document.createElement('div'); el.className = 'duel';
    const synChips = sd => {
      const best = {};
      for (const c of sd.cards) for (const t in c.syn) best[t] = Math.max(best[t] || 0, c.syn[t]);
      if (sd.gems) { /* gems already folded into levels */ }
      const arr = Object.keys(best).sort((a, b) => best[b] - best[a]);
      return arr.map(t => `<span class="schip" style="--tc:${UI.TYPECOL[t]}" data-tip="txt:${encodeURIComponent(UI.cap(t) + ' level ' + ROMAN[best[t]] + ': ' + ((D.syn[t] && D.syn[t].lv[best[t] - 1]) || ''))}">${UI.typeIcon(t, 14)}${ROMAN[best[t]]}</span>`).join('') || '<span class="none">no synergies</span>';
    };
    const rosterHtml = (k) => sides[k].cards.map((c, i) => `<div class="rc" id="rc-${k}-${i}" data-tip="card:0:${c.spec.id}"><div class="rcp">${UI.portrait(c.spec)}</div><div class="rcb"><i style="width:100%"></i></div><span class="rcn">${i + 1}</span></div>`).join('');
    const fighter = k => `<div class="fighter ${k ? 'foe' : 'mine'}" id="f-${k}">
      <div class="f-name"><b id="f-name-${k}"></b><span id="f-types-${k}"></span></div>
      <div class="f-por" id="f-por-${k}"></div>
      <div class="f-hp"><div class="hpbar"><i id="f-hpb-${k}"></i><u id="f-shb-${k}"></u></div><span id="f-hpt-${k}"></span></div>
      <div class="f-pp" id="f-pp-${k}"></div>
      <div class="f-stats" id="f-stats-${k}"></div>
      <div class="f-st" id="f-st-${k}"></div>
      <div class="f-items" id="f-it-${k}"></div>
      <div class="f-gems" id="f-gem-${k}"></div>
      <div class="floaters" id="f-fl-${k}"></div>
      <div class="castbanner" id="f-cast-${k}"></div>
    </div>`;
    el.innerHTML = `
      <div class="d-top">
        <div class="d-title"><b>Round ${replay.r}</b> · ${UI.esc(sides[0].name)} <span>vs</span> ${UI.esc(sides[1].name)} <small>winner earns survivors + ${replay.bonus}</small></div>
        <div class="d-ctl">
          <button class="btn" id="d-play" title="Play / pause (space)">Pause</button>
          <button class="btn" id="d-step" title="Next turn (→)">Step</button>
          <span class="spd"><button data-spd="0.5">½×</button><button data-spd="1" class="on">1×</button><button data-spd="2">2×</button><button data-spd="4">4×</button></span>
          <button class="btn" id="d-skip" title="Skip to the end">Skip</button>
        </div>
      </div>
      <div class="arena">
        <div class="aside"><div class="a-name">${UI.esc(sides[0].name)}</div><div class="a-syn">${synChips(sides[0])}</div><div class="roster">${rosterHtml(0)}</div></div>
        <div class="center">
          ${fighter(0)}
          <div class="vs"><div class="ini" title="Initiative bar: the side it leans toward moves next"><i id="ini-mark"></i><span class="z"></span></div><div class="next" id="d-next"></div><div class="turnno" id="d-turn"></div></div>
          ${fighter(1)}
        </div>
        <div class="aside right"><div class="a-name">${UI.esc(sides[1].name)}</div><div class="a-syn">${synChips(sides[1])}</div><div class="roster">${rosterHtml(1)}</div></div>
      </div>
      <div class="d-log" id="d-log"></div>
      <div class="d-end" id="d-end" hidden></div>`;
    document.body.appendChild(el); document.body.classList.add('in-duel');
    const $ = id => el.querySelector('#' + id);
    const snaps = replay.snaps;
    // unholdable items (gems, Red Scale) are folded onto the opener by the engine; show them beside the lineup instead
    const isBeside = key => !!(ITEMS[key] && ITEMS[key].flags && ITEMS[key].flags.unholdable);
    const besideKeys = [0, 1].map(k => { const a0 = snaps.length ? snapSide(snaps[0], k).act : null; return a0 ? a0.items.filter(isBeside) : []; }); let idx = -1, playing = true, speed = opts.speed || 1, timer = null, done = false;
    const lastActive = [null, null];
    const prevState = [null, null];

    function setFighter(k, snap, animate) {
      const ss = snapSide(snap, k), a = ss.act; const sd = sides[k];
      if (!a) return;
      const card = sd.cards[a.i];
      const changed = lastActive[k] !== a.i;
      if (changed) {
        $('f-name-' + k).textContent = card.name;
        $('f-types-' + k).innerHTML = card.types.map(t => UI.typeIcon(t, 16)).join('');
        $('f-por-' + k).innerHTML = UI.portrait(card.spec, 'huge');
        $('f-gem-' + k).innerHTML = besideKeys[k].length ? '<small>Beside lineup</small>' + besideKeys[k].map(key => `<span data-tip="item:${key}">${UI.itemImg(key)}</span>`).join('') : '';
        $('f-it-' + k).innerHTML = a.items.filter(key => !isBeside(key)).map(key => `<span data-tip="item:${key}">${UI.itemImg(key)}</span>`).join('');
        if (animate) { const f = $('f-' + k); f.classList.remove('enter'); void f.offsetWidth; f.classList.add('enter'); }
        lastActive[k] = a.i; prevState[k] = null;
      }
      const hpPct = Math.max(0, Math.min(100, a.hp / Math.max(1, a.mx) * 100));
      $('f-hpb-' + k).style.width = hpPct + '%';
      $('f-hpb-' + k).style.background = hpPct > 50 ? 'var(--ok)' : hpPct > 25 ? 'var(--warn)' : 'var(--bad)';
      const shp = Math.min(100, a.sh / Math.max(1, a.mx) * 100);
      $('f-shb-' + k).style.width = shp + '%';
      $('f-hpt-' + k).innerHTML = `${a.hp}/${a.mx}${a.sh ? ` <b class="sh">+${a.sh}</b>` : ''}`;
      $('f-pp-' + k).innerHTML = Array.from({ length: a.pp }, (_, i) => `<i class="${i < a.ch ? 'on' : ''}"></i>`).join('') + `<span>${a.ch >= a.pp ? 'READY' : 'charge'}</span>`;
      $('f-stats-' + k).innerHTML = UI.stat('ATK', a.atk) + UI.stat('DEF', a.df) + UI.stat('SPE_DEF', a.sd) + UI.stat('SPEED', a.sp) + UI.stat('AP', a.ap);
      const chips = [];
      for (const s in a.st) if (STCOL[s]) chips.push(`<span class="stc" style="--c:${STCOL[s][1]}">${STCOL[s][0]} ${a.st[s]}</span>`);
      if (a.pois) chips.push(`<span class="stc" style="--c:${STCOL.poison[1]}">POISONED ${a.pois}</span>`);
      if (a.prot) chips.push(`<span class="stc" style="--c:#6aa8ff">PROTECTED</span>`);
      if (a.sw) chips.push(`<span class="stc" style="--c:#c9a03a">SWARM ${a.sw}</span>`);
      $('f-st-' + k).innerHTML = chips.join('');
      // roster
      snapSide(snap, k).cards.forEach((c, i) => {
        const rc = $(`rc-${k}-${i}`); if (!rc) return;
        rc.classList.toggle('active', i === a.i && !c.dead); rc.classList.toggle('dead', !!c.dead); rc.classList.toggle('wait', !c.ent);
        rc.querySelector('i').style.width = (c.ent ? Math.max(0, c.hp / Math.max(1, c.mx) * 100) : 100) + '%';
      });
    }
    function floater(k, text, cls) {
      const fl = $('f-fl-' + k); const s = document.createElement('span'); s.className = 'fl ' + cls; s.textContent = text;
      s.style.left = (30 + Math.random() * 40) + '%'; fl.appendChild(s); setTimeout(() => s.remove(), 1300);
    }
    function addLog(lines, snap) {
      const lg = $('d-log');
      for (const l of lines) {
        const d = document.createElement('div'); let cls = '';
        if (/faints|revived/.test(l)) cls = 'faint'; else if (/ casts /.test(l)) cls = 'cast'; else if (/ hits /.test(l)) cls = 'hit'; else if (/heals/.test(l)) cls = 'heal'; else if (/ is (PARALYZED|BURNED|FROZEN|ASLEEP|CONFUSED|CHARMED|WOUNDED|FLINCHED|FATIGUED|ARMOR)/.test(l)) cls = 'stat'; else if (/enters|stands/.test(l)) cls = 'enter';
        d.className = 'dl ' + cls; d.textContent = l; lg.appendChild(d);
      }
      lg.scrollTop = lg.scrollHeight;
    }
    function applySnap(i, animate) {
      const snap = snaps[i], prev = i > 0 ? snaps[i - 1] : null;
      for (let k = 0; k < 2; k++) setFighter(k, snap, animate);
      if (animate && prev) {
        for (let k = 0; k < 2; k++) {
          const a = snapSide(snap, k).act, b = snapSide(prev, k).act;
          if (a && b && a.i === b.i) {
            const loss = (b.hp + b.sh) - (a.hp + a.sh);
            const hpDown = b.hp - a.hp, shDown = b.sh - a.sh;
            if (hpDown > 0) floater(k, '-' + hpDown, 'dmg'); else if (hpDown < 0) floater(k, '+' + (-hpDown), 'heal');
            if (shDown > 0 && loss > 0 && hpDown <= 0) floater(k, '-' + shDown, 'shd');
            if (shDown < 0) floater(k, '+' + (-shDown) + ' shield', 'shd up');
          } else if (a && b && a.i !== b.i) {
            // previous fighter fainted; show the final blow on the old one is not tracked
          }
        }
        if (snap.mv !== null && snap.mv !== undefined) {
          const k = snap.mv === meS ? 0 : 1; const f = $('f-' + k);
          f.classList.remove('lunge'); void f.offsetWidth; f.classList.add('lunge');
        }
        const casting = snap.ev.find(l => / casts /.test(l));
        if (casting) {
          const k = snap.mv === meS ? 0 : 1; const b = $('f-cast-' + k);
          b.textContent = casting.replace(/^.* casts /, ''); b.classList.remove('go'); void b.offsetWidth; b.classList.add('go');
        }
      }
      // initiative
      if (snap.mv !== null && snap.mv !== undefined || i === 0) {
        const bar = snap.bar || 0; const lean = (meS === 0 ? bar : -bar);   // positive = my side moves next
        const pct = 50 + Math.max(-10, Math.min(10, lean)) * 4.5;
        $('ini-mark').style.left = pct + '%';
        $('d-next').textContent = lean > 0 ? '◀ you move next' : lean < 0 ? 'opponent moves next ▶' : 'even';
      }
      $('d-turn').textContent = `turn ${snap.t}`;
      addLog(snap.ev, snap);
    }
    function finish() {
      if (done) return; done = true; playing = false; clearTimeout(timer);
      $('d-play').textContent = 'Replay'; $('d-play').title = 'Replay';
      const res = replay.result; const myIdx = meS;
      let html, cls;
      if (res.winner === null) { html = `<h2>Draw</h2><p>Nobody scores. Both streaks reset.</p>`; cls = 'draw'; }
      else if (res.winner === myIdx) { html = `<h2>Victory!</h2><p>${res.left} Pokémon left + ${replay.bonus} round bonus = <b>+${res.left + replay.bonus}</b> points for you, −${res.left + replay.bonus} for ${UI.esc(sides[1].name)}.</p>`; cls = 'win'; }
      else { html = `<h2>Defeat</h2><p>${UI.esc(sides[1].name)} keeps ${res.left} Pokémon: <b>−${res.left + replay.bonus}</b> points for you.</p>`; cls = 'loss'; }
      const en = $('d-end'); en.className = 'd-end ' + cls; en.hidden = false;
      en.innerHTML = html + (opts.extraHtml || '') + `<div class="d-end-btns"><button class="btn big" id="d-cont">Continue</button><button class="btn ghost" id="d-again">Watch again</button></div>`;
      en.querySelector('#d-cont').onclick = close;
      en.querySelector('#d-again').onclick = restart;
    }
    function close() { clearTimeout(timer); document.removeEventListener('keydown', onKey); el.remove(); document.body.classList.remove('in-duel'); document.getElementById('tip').hidden = true; resolve(); }
    function restart() { clearTimeout(timer); done = false; idx = -1; $('d-log').innerHTML = ''; $('d-end').hidden = true; lastActive[0] = lastActive[1] = null; playing = true; $('d-play').textContent = 'Pause'; tick(true); }
    function stepOnce() {
      if (idx >= snaps.length - 1) { finish(); return false; }
      idx++; applySnap(idx, true);
      if (idx >= snaps.length - 1) { finish(); return false; }
      return true;
    }
    function tick(first) {
      clearTimeout(timer);
      if (!playing || done) return;
      const more = stepOnce();
      if (more) timer = setTimeout(tick, (idx === 0 ? 900 : 700) / speed);
    }
    function skip() {
      clearTimeout(timer);
      while (idx < snaps.length - 1) { idx++; applySnap(idx, false); }
      finish();
    }
    function onKey(e) {
      if (e.key === ' ') { e.preventDefault(); toggle(); } else if (e.key === 'ArrowRight') { playing = false; $('d-play').textContent = 'Play'; clearTimeout(timer); stepOnce(); }
      else if (e.key === 'Escape' || e.key === 'Enter') { if (done) close(); }
    }
    function toggle() {
      if (done) { restart(); return; }
      playing = !playing; $('d-play').textContent = playing ? 'Pause' : 'Play'; if (playing) tick(); else clearTimeout(timer);
    }
    $('d-play').onclick = toggle;
    $('d-step').onclick = () => { playing = false; $('d-play').textContent = 'Play'; clearTimeout(timer); if (done) restart(), (playing = false), clearTimeout(timer); else stepOnce(); };
    $('d-skip').onclick = skip;
    el.querySelectorAll('[data-spd]').forEach(b => b.onclick = () => { speed = +b.dataset.spd; el.querySelectorAll('[data-spd]').forEach(x => x.classList.toggle('on', x === b)); if (playing && !done) { clearTimeout(timer); timer = setTimeout(tick, 300 / speed); } });
    document.addEventListener('keydown', onKey);
    el.__api = { skip, close, step: stepOnce, state: () => ({ idx, n: snaps.length, done }) };
    UI._duelEl = el;
    if (opts.instant) { skip(); } else tick(true);
  });
};
})();
