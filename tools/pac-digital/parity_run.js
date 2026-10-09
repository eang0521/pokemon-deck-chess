const path = require('path'), fs = require('fs'), os = require('os');
const TOOLS = process.env.PAC_ROOT || path.resolve(__dirname, '..');
global.window = { PAC_DATA: JSON.parse(fs.readFileSync(path.join(TOOLS, 'pac-digital/build/data.json'))) };
const E = require(path.join(TOOLS, '..', 'js', 'engine.js'));
const data = E.DATA; const cards = data.cards;
const tests = JSON.parse(fs.readFileSync(path.join(os.tmpdir(), 'parity.json')));
const R = +process.argv[2] || 200;
let bad = 0; const rows = [];
tests.forEach((t, m) => {
  const wins = [0, 0, 0]; let left = 0, rounds = 0;
  for (let r = 0; r < R; r++) {
    const rng = E.makeRng(1000 * m + r + 5);
    const a = t.la.map((i, k) => new E.BCard(cards[i], t.ia[k])), b = t.lb.map((i, k) => new E.BCard(cards[i], t.ib[k]));
    const res = new E.Duel(a, b, rng).run();
    wins[res.winner === null ? 2 : res.winner]++; left += res.left; rounds += res.rounds;
  }
  const pw = t.py.wins, pa = pw[0] / R, ja = wins[0] / R;
  const d = Math.abs(pa - ja), dl = Math.abs(t.py.left - left / R), dr = Math.abs(t.py.rounds - rounds / R);
  rows.push({ m, py: pa.toFixed(2), js: ja.toFixed(2), d, dl, dr, lv: t.la.length });
  if (d > 0.12) { bad++; console.log('MISMATCH', m, 'lv', t.la.length, 'py', pa.toFixed(2), 'js', ja.toFixed(2), 'left', t.py.left.toFixed(2), (left / R).toFixed(2), 'rounds', t.py.rounds.toFixed(1), (rounds / R).toFixed(1)); }
});
const md = rows.reduce((a, r) => a + r.d, 0) / rows.length;
console.log('matchups', rows.length, 'bad', bad, 'mean |dwin|', md.toFixed(3));
const md2 = rows.reduce((a, r) => a + r.dl, 0) / rows.length, md3 = rows.reduce((a, r) => a + r.dr, 0) / rows.length;
console.log('mean dleft', md2.toFixed(3), 'mean dround', md3.toFixed(3), 'fractional wins', rows.filter(r => r.py !== '0.00' && r.py !== '1.00').length);
console.log(rows.slice(0, 8).map(r => `${r.py}/${r.js}`).join(' '));
