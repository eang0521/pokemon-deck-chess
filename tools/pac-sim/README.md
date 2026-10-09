# Duel simulator (draft rules)

Files: `engine.py` (data load, scale knobs, 95 charge powers), `duel.py` (duel engine, 31 synergies, card-choice AI),
`lineups.py` (budgeted lineups with tier gates), `experiments.py` / `exp2.py` (experiment runners).

Run: `python3 experiments.py out.json` (needs the CSV/locale paths at the top of engine.py).
Scale knobs: `engine.setscale(hp=10, atk=3, df=6, spd=5, pp=33, flat=10, pa=6)` before `load_cards()`.
Duel: `Duel(lineup_a, lineup_b, rng, log=True).run()` -> winner, survivors, rounds.

Not modeled yet: items, economy, Special cards, native passives, alt-form swapping (Transe), TRI_ATTACK always BURNs.
Rules implemented: INITIATIVE BAR (mover pushes the bar toward the other side by the opponent's SPEED; bar side moves; exact 0 switches), speed 1-5 = 3+(x-50)/10, turn = attack then +1 charge, cast at full charge, durations in the affected Pokemon's own turns, synergy levels fixed at entry,
KO replacements enter immediately and take over their side of the bar, chosen after seeing the opponent's current card (greedy matchup score).

Rules update: all Pokemon revealed at start; synergy levels from the whole lineup, fixed for the battle. Default scale now ATK /4, Max PP /50.
Replay viewer: `gen_viewer.py` records battles (viewer_data.json), `build_viewer.py` assembles `duel-replay-bench.html` (template: viewer_template.html).
