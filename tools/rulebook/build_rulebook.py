#!/usr/bin/env python3
"""Builds the Draft Rulebook PDF from the live data (cards, items, synergies) plus rules.py text.

Counts, prices, thresholds, synergy levels and the item list come straight from the same files the
website and the print run use, so they cannot drift. Edit the RULES TEXT below for rule changes."""
import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import json, html, collections, asyncio, datetime
import openpyxl
HERE = _os.path.dirname(_os.path.abspath(__file__))
E = html.escape
data = json.load(open(f'{ROOT}/pac-digital/build/data.json'))
items = json.load(open(f'{ROOT}/items_core.json'))['core']      # [tier, price, copies, name, cat, eff, stats, lift, note]
wb = openpyxl.load_workbook(f'{ROOT}/pac-core-cards-draft.xlsx')
SYN = [r for r in wb['Synergies'].iter_rows(min_row=2, values_only=True) if r[0]]
KW = {r[0]: r[1] for r in wb['Rules & Keywords'].iter_rows(min_row=2, values_only=True) if r[0]}
TRADE = {'I': 0, 'II': 2, 'III': 4, 'IV': 7, 'V': 14}
cnt = collections.Counter((c['pool'], c['tier']) for c in data['cards'])
def n(pool, tier=None): return sum(v for (p, t), v in cnt.items() if p == pool and (tier is None or t == tier))
ncard = {k: n(k) for k in ('core', 'add', 'unique', 'legendary', 'hatch')}
nitems = sum(r[2] for r in items); nkinds = len(items)
today = datetime.date(2026, 10, 9).strftime('%b %-d, %Y')

def table(head, rows, cls='', widths=None):
    cg = ''.join(f'<col style="width:{w}">' for w in widths) if widths else ''
    return (f'<table class="{cls}"><colgroup>{cg}</colgroup><thead><tr>' + ''.join(f'<th>{h}</th>' for h in head) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>')
def ul(xs): return '<ul>' + ''.join(f'<li>{x}</li>' for x in xs) + '</ul>'
def ol(xs): return '<ol>' + ''.join(f'<li>{x}</li>' for x in xs) + '</ol>'

S = []   # sections
def sec(title, body): S.append(f'<h1>{title}</h1>{body}')
def sub(title, body): return f'<h2>{title}</h2>{body}'

# ---------------------------------------------------------------- 1 Overview
sec('Overview', f'''
<p>Eight players build a lineup of Pokémon over <b>12 rounds</b>, fight one head-to-head duel per round, and the player with the most points after round 12 wins. A full game takes 60 minutes or less. Empty seats are filled by bots (see Bots).</p>
<p>The game is a prototype built from the open-source Pokémon Auto Chess (PAC) data. There is no life total and no elimination: every duel moves points from the loser to the winner.</p>
{ul(['Players: 8, paired head-to-head each round.', 'Rounds: 12.', 'Length: 60 minutes or less.', 'Win condition: most points after round 12.',
     'Each round: collect income, make any pick, buy cards and items from the shared markets, set your lineup order, then fight one duel.'])}''')

# ---------------------------------------------------------------- 2 Components
sec('Components', f'''
<p>The game uses a market deck per tier, three pick pools, an item deck and trackers for points, gold, XP and level. Counts are for the current draft roster (Special Pokémon are left out for now).</p>
{table(['Component', 'Count', 'Notes'], [
 ['Core cards', ncard['core'], 'One copy of each Pokémon. Tiers I–V: ' + ' · '.join(f"{t} {n('core', t)}" for t in ('I', 'II', 'III', 'IV', 'V')) + '. A random 32 per tier are used each game (see Setup).'],
 ['Additional cards (incl. Regional)', ncard['add'], 'Enter play through the starter and Additional picks. Tiers I–IV: ' + ' · '.join(f"{t} {n('add', t)}" for t in ('I', 'II', 'III', 'IV')) + f" (Tier V {n('add', 'V')}: only to refill an empty market deck)."],
 ['Unique cards', ncard['unique'], 'Only enter play through the Unique pick.'],
 ['Legendary cards', ncard['legendary'], 'Only enter play through the Legendary pick.'],
 ['Hatch cards', ncard['hatch'], 'Tier II / III / IV decks of 13. Given by the Baby synergy; never in the market.'],
 ['Items', f'{nitems} cards ({nkinds} kinds)', 'Several copies of each; tiers I–IV: ' + ' · '.join(f"{t} {sum(r[2] for r in items if r[0] == t)}" for t in ('I', 'II', 'III', 'IV')) + '. There are no Tier V items.'],
 ['Trackers', '1 per player', 'Points (start 20), gold, XP, level.'],
], widths=['26%', '16%', '58%'])}
<p>Every card shows a tier (I to V), a price, one or two types (its synergies), HP, ATK, DEF, SP.DEF, SPEED, Max PP, and a charge power. Each stage of an evolution line is its own card.</p>''')

# ---------------------------------------------------------------- 3 Setup
sec('Setup', f'''
{ol(['Give each player a tracker set to <b>20 points, 5 gold, level 2, 0 XP</b>.',
 '<b>Market decks.</b> For each tier I–V, shuffle the Core cards of that tier and keep <b>32 random ones</b> as that tier’s market deck. The rest of that tier’s Core cards stay in the box.',
 '<b>Item deck.</b> Shuffle the item deck by tier (I–IV).',
 'Keep the Additional, Unique and Legendary pools set apart (Additional sorted by tier).',
 'Seat the players in a circle and number the seats 1 to 8. Seat 1 never moves; the other seats rotate clockwise each round (see Battle).',
 '<b>Starter pick</b> (before round 1, see Picks): each player is dealt 3 Tier I Additional cards, each with a Tier I item, and keeps one.',
 'Reveal the markets: <b>4 Pokémon face up per tier</b> and <b>2 items face up per item tier</b> (tiers unlock as you level, see Shop phase).'])}''')

# ---------------------------------------------------------------- 4 Round structure
sec('Round structure', f'''
<p>Each of the 12 rounds has the same phases; some rounds add a pick before the shop.</p>
{ol(['<b>Income:</b> collect gold and XP (round 1 has no income; you start with 5 gold).', '<b>Pick event:</b> only in the rounds marked below.',
 '<b>Shop phase:</b> buy cards, items and XP; arrange your lineup.', '<b>Lineup lock:</b> every player fixes their lineup order.', '<b>Duel and scoring:</b> fight your opponent for the round, then move points.'])}
{table(['Round', 'Pick before the shop', 'Duel bonus points'], [
 ['Before round 1', 'Starter pick (Tier I Additional + Tier I item)', '—'], ['1', 'none', '0'], ['2', 'Additional pick, Tier II (+ item)', '0'], ['3', 'none', '0'], ['4', 'none', '+1'],
 ['5', 'Additional pick, Tier III (+ item)', '+1'], ['6', 'Unique pick (5 cards)', '+1'], ['7', 'none', '+2'], ['8', 'Additional pick, Tier IV (+ item)', '+2'],
 ['9', 'Legendary pick (5 cards)', '+2'], ['10', 'none', '+3'], ['11', 'none', '+3'], ['12', 'none', '+3']], widths=['20%', '55%', '25%'], cls='keep')}
<p>There are no PvE rounds and no item carousels. Items come from the item market and from picks.</p>''')

# ---------------------------------------------------------------- 5 Shop
lv = [['2', '0', 'Tier I', '1 to 2'], ['3', '2', 'Tier II', '3 to 5'], ['4', '6', 'Tier III', '5 to 7'], ['5', '14', 'Tier IV', '8 to 13'], ['6', '30', 'Tier V', '15 to 32'], ['7', '56', '—', '—']]
sec('Shop phase', f'''
<p>Gold buys cards, items and XP from the shared markets. Players take turns buying, from the lowest-scoring player up.</p>
{sub('Income', ul(['Base income: <b>+5 gold</b>.', 'Interest: <b>+1 gold for every 5 gold banked</b>, up to +3.',
 'Streak: a win or loss streak pays extra gold: streak of 2 = +1, 3 = +2, 4 or more = +3. A streak of 1 pays nothing.', 'XP: <b>+2 XP</b> (free).']) + '<p>You may also buy XP at any time: <b>4 gold gives 4 XP</b>.</p>')}
{sub('Levels and tiers', '<p>Your level is your lineup size. It rises when your total XP reaches the next threshold, and it unlocks tiers in the market.</p>' + table(['Level', 'Total XP needed', 'Newly unlocked tier', 'Card price range'], lv)
 + '<p>A card’s price is its value rounded up, where value = PAC cost × 2.5 for each extra star × 1.5 if its line evolves only once. Additional cards cost at least 3 (Tier II), 5 (Tier III) or 8 (Tier IV).</p>'
 + '<p><b>Cost and trade-in on the cards.</b> Every Pokémon and item shows a coin symbol, its price, and its trade-in value in brackets, e.g. 5 (4). You pay the price to buy; the bracketed number is what the card counts for when you trade it in. <b>Unique and Legendary cards cannot be bought</b>, so their price box shows “—” and only the trade-in value, e.g. — (12).</p>')}
{sub('The markets', ul([
 '<b>Pokémon market.</b> Each unlocked tier shows <b>4 Pokémon face up</b>, drawn from that tier’s market deck (32 Core Pokémon, plus any unchosen pick cards shuffled in, see Picks). A bought card leaves the market and is refilled from the deck. If a tier’s deck runs out, refill it from the Additional cards of that tier.',
 '<b>Item market.</b> <b>2 items face up of each item tier</b> (I–IV) unlocked at your level, drawn from that tier of the item deck and refilled after every purchase. Tiers unlock at the same levels as cards.']))}
{sub('Buying turns', ol(['Players act from the fewest points to the most. Ties go to the lower level, then to chance.',
 'On your turn you take <b>one action</b>: buy one card or item, <b>evolve</b>, <b>churn</b> (pay 1 gold to discard one face-up Pokémon to the bottom of its deck and draw a replacement), or <b>pass</b>.',
 'After every purchase the market is refilled before the next player acts.',
 '<b>Passing:</b> once you pass, you may <b>not buy anything for the rest of the round</b> (no cards, items, evolves or churns). The shop ends when every player has passed.']) + '<p>Buying XP, moving cards in or out of your lineup, reordering, and giving items are free: they do not use your turn and can happen at any time.</p>')}
{sub('Trade-in, no selling', '<p>Cards and items can never be sold for gold. Instead you may trade a card or item in as payment toward a new card or item. A card’s trade-in value is 1 less than the lowest price in its tier: <b>Tier I = 0, II = 2, III = 4, IV = 7, V = 14</b>. Items use the trade-in value of their tier. Picked cards use the same values, plus <b>Unique = 12 and Legendary = 25</b>. Traded-in cards go to the bottom of their deck; traded-in items go to the bottom of the item deck.</p>')}''')

# ---------------------------------------------------------------- 6 Picks
sec('Picks', f'''
<p>The Additional, Unique and Legendary pools never appear in the market directly. They are handed out through picks at fixed points. Everyone picks at the same time from their own deal, so there is no waiting and no denial.</p>
{table(['When', 'Pool', 'Deal', 'Items'], [
 ['Before round 1 (starter)', 'Additional, Tier I', '3 cards, keep 1', 'Each card comes with a random Tier I item'],
 ['Before round 2', 'Additional, Tier II', '3 cards, keep 1', 'Each card comes with a random Tier II item'],
 ['Before round 5', 'Additional, Tier III', '3 cards, keep 1', 'Each card comes with a random Tier III item'],
 ['Before round 8', 'Additional, Tier IV', '3 cards, keep 1', 'Each card comes with a random Tier IV item'],
 ['Before round 6', 'Unique', '<b>5 cards</b>, keep 1', 'none'],
 ['Before round 9', 'Legendary', '<b>5 cards</b>, keep 1', 'none']], widths=['26%', '20%', '22%', '32%'], cls='keep')}
{sub('Bundled items', '<p>The item bundled with each Additional card is a random item of the same tier from the item deck. It can be <b>any</b> item, including gems and other unholdable items. If you keep the card, you keep its item.</p>')}
{sub('Unchosen cards', ul([
 'Unchosen <b>Pokémon</b> from the starter pick and from Additional picks are <b>shuffled into the market deck of their tier</b>. (So Tier I Pokémon you pass on can appear in the Tier I market.)',
 'Unchosen <b>starter items</b> are discarded. Unchosen items from Additional picks go to the <b>bottom of the item deck</b>.',
 'Unchosen Unique and Legendary cards go to the bottom of their pool; they never enter a market deck.']))}
<p>Picked cards go to your bench like any other card. Each card exists once in the game. Picks have no price but can be traded in as payment (Unique 12, Legendary 25). A traded-in pick goes to the bottom of its pool. Regional cards are part of the Additional pool and are dealt like any other Additional card.</p>''')

# ---------------------------------------------------------------- 7 Lineup and items
sec('Lineup and items', f'''
<p><b>Bench and lineup.</b> Your lineup size equals your level (3 at level 3, up to 7 at level 7 as levels rise). Cards on the bench do nothing. Before each battle, place your lineup cards in a row. Order matters: it decides who fights first and who steps in when a card is knocked out. Rearranging is free and not an action; lineup order is revealed at the same time as everything else.</p>
<p><b>Items.</b> Items come from the item market and from picks. An item is held by one card at a time. Rules:</p>
{ul(['Each card holds up to <b>3 items</b>. Components and stones are items too.', '<b>A card cannot hold two of the same item.</b>',
 'All items are bought finished. There is no combining.', 'Items can be moved between cards freely during the shop phase. Moving is free.',
 '<b>Unholdable items</b> (Gems and Red Scale) are not attached to any card: they sit beside your lineup and take no slot. Their effects work for your whole side.',
 'If a card leaves your lineup (traded in), its items return to your item pool.', 'Items are never sold for gold. They can be traded in as payment like cards.',
 '<b>Wonder Box.</b> At battle start, take the top Tier III and Tier II item of the item deck and attach them to the holder for this battle (max 3 items including the Wonder Box: the Tier III item first, the Tier II item only if there is room). A loan cannot duplicate an item the holder already has. After the battle both items go back to the bottom of their decks.'])}
<p><b>Synergy count.</b> Synergy levels are counted from your whole lineup, and each evolution family counts once per type. Two Pokémon from the same evolution line never give double synergy. Gems and stones that add a type count towards the total.</p>''')

# ---------------------------------------------------------------- 8 Battle
sec('Battle', f'''
{sub('Pairings (rotating round robin)', '<p>Seat the 8 players around the table. Round 1 pairs seat 1 with seat 8, 2 with 7, 3 with 6 and 4 with 5. After each round, seat 1 stays put and every other player moves one seat clockwise, then the new opposite seats fight. Over rounds 1 to 7 everyone meets every other player exactly once; the schedule then restarts, so rounds 8 to 12 repeat the pairings of rounds 1 to 5. Bots fill empty seats.</p>')}
<p>Lineup order is set before the battle, without knowing who you will face or what they fielded. All lineups, items and synergy levels are revealed at the start of the battle, and synergy levels are fixed for the whole battle.</p>
<p>Printed stats are already scaled down from the original game: HP, ATK, DEF, SP.DEF, SPEED, Max PP (charge needed to cast). Range is ignored. Each card also has one charge power.</p>
{sub('The initiative bar', '<p>A shared bar sits between the two lineups, with a marker on the middle (0).</p>' + ol([
 '<b>Who goes first.</b> The player whose front card has the higher SPEED moves first. On a tie, the lower current score moves first, then the player with less gold.',
 'When a card takes its turn, the marker moves toward the other side by the opponent front card’s current SPEED.',
 'The side the marker favours takes the next turn. If the marker lands exactly on 0, the side that did not just move goes next.',
 'If a front card is knocked out, the bar position carries over to the next card.']))}
{sub('A turn', '<p>The active front card does these steps in order:</p>' + ol([
 'Start-of-turn effects (poison, burn, heal over time, and so on).',
 'Attack the enemy front card. Damage is ATK minus the target’s DEF (physical) or SP.DEF (special), at least 1. Shield absorbs damage first, then HP, <b>but every hit deals at least 1 damage to HP</b>, so a big shield can never make a Pokémon immune.',
 'Gain +1 charge.', 'If charge has reached Max PP, cast the charge power and reset charge to 0.', 'Apply synergy powers that trigger on attack or cast.', 'End-of-turn effects; statuses tick down.']))}
<p><b>Knock out.</b> A card at 0 HP leaves the fight. The next card in lineup order enters, triggering its enter effects. Charge, shields and temporary stat changes on a knocked-out card are lost.</p>
<p><b>Winning the battle.</b> A battle ends when one lineup has no cards left. The other side wins.</p>
<p><b>Overtime.</b> There is no turn cap, but long battles wear down. After <b>round 25</b> of a battle (a round = both sides have taken a turn), every Pokémon takes <b>1 TRUE damage after its own turn</b>, which ignores shield, and <b>1 more for every 5 further rounds</b>. This stops stalling builds (huge shields or healing) from lasting forever. Safety net: if a battle somehow reaches round 60, the side with more total HP left wins (equal = draw).</p>''')

# ---------------------------------------------------------------- 9 Scoring
sec('Scoring and end of game', f'''
<p>Every player starts with 20 points. There is no elimination, so everyone plays all 12 rounds. After each battle the winner gains, and the loser loses, the same number of points:</p>
<p style="text-align:center"><b>points moved = surviving Pokémon on the winner’s side + round bonus</b></p>
{table(['Rounds', 'Round bonus'], [['1 to 3', '0'], ['4 to 6', '+1'], ['7 to 9', '+2'], ['10 to 12', '+3']], widths=['50%', '50%'])}
<p>A draw moves no points. Streak gold is updated after every battle. <b>End of game:</b> after round 12 the player with the most points wins. There are no tiebreaks for now; players on the same score share the win.</p>''')

# ---------------------------------------------------------------- 10 Synergies
def s(x): return E(x) if x else '–'
sec('Synergies', f'''
<p>Each card has one to three types. Count the distinct cards in your lineup that share a type (each evolution family once). When the count reaches a threshold, that type’s synergy is active at that level for all of your cards with the type (or, for some, your whole side) for the entire battle. Levels do not change mid-battle. Thresholds are the original game’s values multiplied by 0.75 and rounded up (Light is set by hand). Types with a fourth threshold have a Level IV.</p>
{table(['Synergy', 'Needs', 'Theme', 'Level I', 'Level II', 'Level III', 'Level IV'], [[f'<b>{E(r[0])}</b>', E(r[2]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), s(r[7])] for r in SYN], cls='syn small', widths=['10%', '7%', '15%', '17%', '17%', '18%', '16%'])}
<p>Where a level repeats the one before, the level still matters for the thresholds and for later levels. Dragon works like the original game: Level I makes each Dragon’s second type count twice for synergy totals; only cards with the Dragon type receive the shield, speed and AP bonuses.</p>''')

# ---------------------------------------------------------------- 11 Items
rows = [[r[0], r[1], f'({TRADE[r[0]]})', r[2], f'<b>{E(r[3])}</b>', r[4], E(r[5])] for r in sorted(items, key=lambda r: ('I II III IV V'.split().index(r[0]), r[1], r[3]))]
sec('Items', f'''
<p>There are {nkinds} kinds of item in {nitems} cards: Components (simple stat items), Stones (add a type to the holder, which counts toward synergy), Tools, Gems (unholdable, they boost a synergy for your whole side), Shiny items and Crafted items (specialised effects). Price is in gold, (trade-in) is the value when traded in, and Copies is how many exist in the game. Stat bonuses are in board-game scale. “Every Nth” effects count the holder’s own attacks or turns.</p>
{table(['Tier', 'Price', 'Trade', 'Copies', 'Item', 'Kind', 'Effect'], rows, cls='items small', widths=['4%', '6%', '6%', '6%', '16%', '12%', '50%'])}''')

# ---------------------------------------------------------------- 12 Keywords
EXTRA = [('SHIELD', 'Absorbs damage before HP. Not reduced by DEF. Every hit still deals at least 1 to HP. Lost when the card is knocked out.'),
         ('SWARM token', 'Bug: blocks the next basic attack against its holder completely.'), ('CURSE (Ghost)', 'A permanent stat penalty (DEF / SP.DEF / ATK, as shown on the Ghost card) placed on a foe card for this battle.'),
         ('LOCKED', 'The next hit the Pokémon takes ignores FLY AWAY, dodge and evade (Flying, Ghost, Smoliv dish, dodge items); then the lock ends. Counts as a negative status while it lasts.'), ('FLY AWAY', 'Flying: at low HP, PROTECT for 1 turn and +1 SPEED.'),
         ('DISH', 'A Gourmet chef serves its line’s signature dish to the next card in lineup order (the previous card if last). Not a knock-out trigger.'),
         ('TRUE damage', 'Ignores DEF and SP.DEF.')]
order = ['Attack', 'DEF / SP.DEF', 'Charge', 'AP', 'Crit', 'BURN', 'POISON', 'FLINCH', 'PARALYZE', 'SLEEP', 'FREEZE', 'CONFUSE', 'CHARM', 'WOUND', 'ARMOR BREAK', 'FATIGUE', 'PROTECT', 'SPLASH', 'BATON']
krows = [[f'<b>{k}</b>', E(KW[k])] for k in order if k in KW] + [[f'<b>{k}</b>', E(v)] for k, v in EXTRA]
sec('Keywords and statuses', f'<p>Durations such as “2 turns” always count the affected card’s own turns and tick at the end of its turn.</p>' + table(['Term', 'Rule'], krows, cls='kw', widths=['20%', '80%']))

# ---------------------------------------------------------------- 13 Bots / Evolution / Hatch
sec('Bots', f'''
<p>Bots fill empty seats (the game is built for 8). They use the same market, prices and rules as players and never look at another player’s lineup or gold. The digital version has seven bot styles:</p>
{ul(['<b>The Banker</b> banks gold for interest and buys only clear upgrades.', '<b>The Leveler</b> buys XP hard to reach the high tiers early.', '<b>Type Specialist</b> picks two favourite types and builds around them.',
 '<b>The Evolver</b> loves evolution lines and churns the market for them.', '<b>Item Hoarder</b> spends on items first and loads up its best Pokémon.', '<b>The Bruiser</b> buys straight value for gold, strongest Pokémon first.',
 '<b>The Gambler</b> banks when ahead and goes all in when behind.'])}
<p>For a physical game the rules for bots are still to be written; the styles above are the model.</p>''')
sec('Evolution', f'''
<p>There is no automatic evolution. During your turn in the shop phase you may <b>evolve</b> a Pokémon (it costs your turn action, like a purchase):</p>
{ul(['The evolved card must be <b>face up in the Pokémon market</b> (Core lines only) and its tier must be unlocked at your level.', 'Trade in a Pokémon you own for a higher-stage Pokémon of the same family. You may skip stages.',
 'The lower Pokémon counts for its <b>full price</b> toward the price of the evolved one. Pay the rest in gold.', 'The evolved Pokémon takes the old one’s place (bench or lineup) and keeps its items.',
 'The old Pokémon goes to the bottom of its deck.', 'Because each family counts once per type, holding both stages never gives double synergy.'])}''')
sec('Baby and Hatch', '<p>With the Baby synergy active at level I, II or III, a player who <b>loses a duel</b> hatches a Tier II, III or IV Hatch card (from the Hatch decks, never in the market). Hatch cards are not Baby, cannot be bought, and are traded in for 2 / 4 / 7.</p>')

# ---------------------------------------------------------------- 14 Open questions
sec('Open questions and settled rules', f'''
{sub('Open questions', ol([
 '<b>Wonder Box price.</b> After the loan rewrite its simulated strength roughly halved (lift 15 to 7.5), so 12 gold / Tier IV is too much. About 6 gold at Tier III would fit.',
 '<b>Market deck source.</b> The 32 cards per tier come from Core only. Should Additional-pick leftovers ever enter Unique/Legendary decks? (Currently no.)',
 '<b>Gourmet dish keyword.</b> Dishes go to the next card in lineup order at battle start. Do you want a keyword for it, such as SERVE?',
 '<b>Bots (physical game).</b> The digital bots are tuned; the physical rules are a sketch.',
 '<b>Balance.</b> Baby is still weak, Fairy is weak at two cards, and Ghost, Human and Ground are strongest at three.']))}
{sub('Settled', '<p>3 items per card, never two of the same · first mover by speed, then lower score, then less gold · trade-in is 1 below the tier’s lowest price; items by tier; Unique 12, Legendary 25 · no end-of-game tiebreaks · streak gold for win and loss streaks · all items bought finished · overtime after round 25 · every hit deals ≥1 to HP · points are zero-sum · rotating round robin · lineup order set before the battle · each evolution family counts once per type · evolve by trading in the old card at full price, skipping stages allowed · Fire burns on a schedule · AP is shown with the ✦ symbol · each Gourmet line has its own dish · market decks of 32 Core per tier with 4 face up · starter pick from Additional I with a Tier I item · unchosen Pokémon are shuffled into the market deck · passing locks you out of buying for the round · Unique/Legendary picks deal 5 and no items · item market has 2 per tier.</p>')}
{sub('Changes since the Oct 7 draft', ul([
 'Market decks of 32 Core per tier; 4 Pokémon face up per tier (was about 3).', 'Starter pick from Additional I with a bundled item; Additional picks bundle a same-tier item; unchosen Pokémon are shuffled into the market deck.',
 'Unique and Legendary picks deal 5 cards (was 3), no items; trade-in 12 and 25 (was 15 and 30); their price box shows “—”.', 'Item market: 2 per item tier; no duplicate items on a Pokémon; unholdable items sit beside the lineup.',
 'Passing locks you out of buying for the round. Churn and evolve now require the card to be in the market.', 'Shields never block the last point; overtime replaces the old exhaustion rule (after round 25 instead of after 24 turns).',
 'Efficient Bandanna min 2; Star Piece doubles the charge power’s numbers; Wonder Box is a loan of the top Tier III and Tier II items; Klink line Gear Grind scales with current SPEED.',
 'Power rework toward the original game (no dice, 50% is the only percentage): Tri Attack picks BURN / PARALYZE / FREEZE from your highest Fire / Electric / Ice synergy; Steamroller flinches slower foes; Icicle Missile always freezes; Fury Swipes makes 3 extra attacks; Volt Switch and Snipe Shot splash; Silver Wind also gives +1 DEF and +1 SP.DEF; Uproar hits over 3 turns; Horn Leech heals half the damage; Head Smash and Sheer Cold can KO sleeping or frozen foes; Venoshock only doubles on a POISONED target; Psyshock shields for the charge it burns; Zing Zap shields only against a PARALYZED target; Roar of Time revives your next Pokémon once at half HP.',
 'New LOCKED status (Vise Grip, Fairy Lock, Thousand Arrows, Jaw Lock, Octolock, Gravity, Coil, Power Hug, Magnet Bomb). Judgment deals AP + double the sum of your 3 highest synergy counts. Flame Orb really burns its holder.']))}''')

CSS = '''
@page { size: Letter; margin: .7in .75in .8in }
* { box-sizing: border-box }
body { font: 10.3pt/1.45 "Segoe UI", "Helvetica Neue", Helvetica, Arial, "DejaVu Sans", sans-serif; color: #1c2430; margin: 0 }
.title { margin: 0 0 .25in; padding-bottom: .12in; border-bottom: 3px solid #2e6bd6 }
.title h0 { display: block; font-size: 25pt; font-weight: 800; line-height: 1.1 }
.title p { margin: .06in 0 0; color: #5b6676; font-size: 9.5pt }
h1 { font-size: 16pt; margin: .3in 0 .08in; padding-bottom: .03in; border-bottom: 1.5px solid #cfd6e2; break-after: avoid; color: #14305e }
h2 { font-size: 11.5pt; margin: .17in 0 .04in; break-after: avoid; color: #1c2430 }
p { margin: .06in 0 }
ul, ol { margin: .05in 0 .08in; padding-left: .26in } li { margin: .025in 0 }
table { border-collapse: collapse; width: 100%; margin: .08in 0 .12in; table-layout: fixed }
thead { display: table-header-group }
th { background: #14305e; color: #fff; text-align: left; font-weight: 700; padding: .04in .06in; font-size: 9pt }
td { vertical-align: top; padding: .035in .06in; border-bottom: 1px solid #dde3ec; overflow-wrap: anywhere }
tr { break-inside: avoid }
tbody tr:nth-child(even) td { background: #f5f7fb }
table { break-inside: auto } table.keep { break-inside: avoid }
table.small { font-size: 8.3pt } table.small th { font-size: 8pt } table.small td { padding: .025in .045in }
table.items td:nth-child(-n+4) { text-align: center }
'''
body = ''.join(S)
page = f'''<!doctype html><html><head><meta charset="utf-8"><title>Pokémon Auto Chess Board Game — Draft Rulebook</title><style>{CSS}</style></head><body>
<div class="title"><h0>Pokémon Auto Chess Board Game — Draft Rulebook</h0><p>{today} · Elijah Ang · generated from the live game data (tools/sync.py rulebook)</p></div>{body}</body></html>'''
open(f'{HERE}/rulebook.html', 'w').write(page)

NAME = 'Pokémon Auto Chess Board Game — Draft Rulebook.pdf'
async def render():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        exe = '/opt/pw-browsers/chromium'
        b = await p.chromium.launch(executable_path=exe if _os.path.exists(exe) else None, args=['--allow-file-access-from-files'])
        pg = await b.new_page(); await pg.goto('file://' + f'{HERE}/rulebook.html'); await pg.wait_for_timeout(500)
        foot = '<div style="width:100%;font:8pt Helvetica,Arial,sans-serif;color:#667;padding:0 .75in;display:flex;justify-content:space-between"><span>Pokémon Auto Chess Board Game — Draft Rulebook</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'
        await pg.pdf(path=f'{HERE}/{NAME}', format='Letter', print_background=True, display_header_footer=True, header_template='<span></span>', footer_template=foot,
                     margin=dict(top='.7in', bottom='.8in', left='.75in', right='.75in'))
        await b.close()
asyncio.run(render())
print('rulebook:', NAME)
