import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, html, re
sys.path.insert(0, f'{ROOT}/pac-print')
from build import *

def hdr(icon, title, tc):
    return f'<div class="strip" style="background:{tc}"></div><div class="rh">{icon}<span>{title}</span></div>'

def row(icon, title, body):
    return f'<div class="rw">{icon}<div><b>{title}</b> {rich(body)}</div></div>'

def refcard(tc, icon, title, rows, foot=''):
    return (f'<div class="card" style="--tc:{tc}">{hdr(icon, title, tc)}<div class="rows">' + ''.join(row(*r) for r in rows) + f'</div>{foot}</div>')

I_ = lambda n: ic(n)
REF = []
G = '#4a5a58'
REF.append(refcard('#2e9e57', ic('HP'), 'STATS', [
    (I_('HP'), 'HP', 'Health. At 0 the Pokémon is KO’d.'),
    (I_('ATK'), 'ATK', 'Damage of each basic attack.'),
    (I_('DEF'), 'DEF', 'Blocked from each PHYSICAL hit (min 1 gets through).'),
    (I_('SPE_DEF'), 'SP.DEF', 'Blocked from each SPECIAL hit (min 1 gets through).'),
    (I_('SPEED'), 'SPEED', 'Who moves first, and how often.'),
    (I_('PP'), 'PP', 'Charge: +1 per turn. At this number, cast the charge power.'),
    (I_('AP'), 'AP', 'Ability power (see Damage card).'),
]))
REF.append(refcard('#d63a3a', ic('ATK'), 'DAMAGE', [
    (I_('ATK'), 'PHYSICAL', 'Reduced by DEF.'),
    (I_('SPECIAL'), 'SPECIAL', 'Reduced by SP.DEF.'),
    (I_('TRUE'), 'TRUE', 'Ignores DEF and SP.DEF.'),
    (I_('SHIELD'), 'SHIELD', 'Absorbs damage before HP; each hit still deals ≥1 to HP. Lost when KO’d.'),
    (I_('CRIT'), 'CRIT', 'Crit: ×2 damage. Each attack adds the crit tokens you generate; at 5 tokens, spend 5: that attack crits.'),
    (ic('AP'), 'AP number', 'AP+N: add your AP to N. AP/2+N: add half your AP (round down) to N. Plain numbers never change.'),
]))
REF.append(refcard('#e0742c', ic('BURN'), 'STATUS I', [
    (I_('BURN'), 'BURN', 'TRUE damage at the end of each of its own turns (1; 2 at Fire III) for 3 turns (4 at Fire IV). Re-burning resets the timer.'),
    (I_('POISONED'), 'POISON', '1 TRUE damage at the end of each turn. Re-applying adds +1 per turn (stacks) while on the field.'),
    (I_('PARALYSIS'), 'PARALYZE', '-1 SPEED and its attacks give no charge.'),
    (I_('FLINCH'), 'FLINCH', 'Cannot cast on its next turn (charge stays full).'),
]))
REF.append(refcard('#8a5bc8', ic('SLEEP'), 'STATUS II', [
    (I_('SLEEP'), 'SLEEP', 'Skips its next turn(s) entirely.'),
    (I_('FREEZE'), 'FREEZE', 'Skips its next turn; counts as DEF 0 / SP.DEF 0 until then.'),
    (I_('CONFUSION'), 'CONFUSE', 'Its next attack deals half damage.'),
    (I_('CHARM'), 'CHARM', '-2 ATK for 2 of its turns.'),
]))
REF.append(refcard('#3f79c6', ic('WOUND'), 'STATUS III', [
    (I_('WOUND'), 'WOUND', 'Cannot heal or gain SHIELD.'),
    (I_('ARMOR_BREAK'), 'ARMOR BREAK', 'DEF and SP.DEF count as 0.'),
    (I_('FATIGUE'), 'FATIGUE', 'Gains no charge.'),
    (I_('SILENCE'), 'SILENCE', 'Cannot cast (same as FLINCH).'),
    (I_('PROTECT'), 'PROTECT', 'Ignores all damage until its next turn begins.'),
]))
REF.append(refcard('#1d8f8f', ic('CURSE'), 'STATUS IV', [
    (I_('CURSE'), 'CURSE', 'Ghost mark: the foe loses the DEF / SP.DEF / ATK shown on the Ghost card.'),
    (I_('LOCKED'), 'LOCKED', 'Its next hit ignores FLY AWAY, dodge and evade; then the lock ends.'),
    (I_('fly_away'), 'FLY AWAY', 'Flying: at low HP, PROTECT 1 turn and +1 SPEED.'),
    (I_('SWARM'), 'SWARM token', 'Bug: blocks the next attack completely.'),
    ('<span style="width:.15in"></span>', 'Durations', 'All “N turns” count the affected Pokémon’s OWN turns and tick at the end of its turn.'),
]))
REF.append(refcard('#1d8f8f', ic('SPLASH'), 'SPLASH · BATON', [
    (I_('SPLASH'), 'SPLASH', 'Damage only, to the OPPONENT’S next entering Pokémon. “SPLASH 4” = 4; plain = half the ability’s damage. Ignores DEF and SHIELD. No statuses or other effects.'),
    (I_('BATON'), 'BATON', 'A bonus for YOUR OWN next Pokémon, applied when it enters. Triggers when this Pokémon is KO’d.'),
    (I_('DISH'), 'DISH', 'A Gourmet chef serves its dish to the next card in lineup order (previous if last). Not a KO trigger.'),
]))
REF.append(refcard('#4a5a58', ic('TURN'), 'THE BATTLE', [
    ('', 'Reveal', 'All revealed. Order was set blind.'),
    ('', 'Order', 'Higher front-card SPEED moves first. Tie: lower score, then less gold.'),
    ('', 'A turn', 'Attack · +1 charge · cast if charge = PP · synergy powers.'),
    ('', 'KO', 'The next Pokémon in order enters. No choosing replacements.'),
    ('', 'Length', 'Battles run until one lineup is KO’d. Overtime: after round 25 of a battle, each Pokémon takes 1 true damage after its own turn (+1 per 5 more rounds).'),
    ('', 'Win', 'Last side standing wins. Winner gains survivors + round bonus; loser loses the same.'),
]))
REF.append(refcard('#d9a61e', ic('COIN'), 'ECONOMY', [
    (I_('COIN'), 'Income', '+5 per round, +1 interest per 5 gold banked (max +3).'),
    (I_('COIN'), 'Streak', 'Win OR loss streaks: 2 = +1, 3 = +2, 4+ = +3.'),
    (ic('XP'), 'XP', '+2 XP each round. Buy XP: 4 gold = 4 XP (an action).'),
    ('', 'Level', 'Level = lineup size. Start 2. Total XP: L3 2 · L4 6 · L5 14 · L6 30 · L7 56.'),
    ('', 'Tiers', 'I 1–2 · II 3–5 · III 5–7 · IV 8–13 · V 15–32. Unlock: II L3 · III L4 · IV L5 · V L6.'),
    ('', 'Turn', 'Worst score acts first. One action: buy, trade, evolve, item, XP, or pass. Passing = no more buying that round.'),
]))
REF.append(refcard('#8a5bc8', ic('evolution'), 'TRADE & EVOLVE', [
    (I_('COIN'), 'Cost (trade-in)', 'Every card and item shows its price, then its trade-in value in brackets, e.g. 5 (4). Pay the price; trade-in value is credited when you return a card.'),
    ('', 'Trade-in', 'Return a card for its value: I 0 · II 2 · III 4 · IV 7 · V 14 · Unique 12 · Legendary 25 (their price shows —).'),
    ('', 'Evolve', 'Swap a lower stage for a higher one of the same family; the old card is credited at its FULL COST. Pay the difference. Only if the evolved card is in the shop row (Core lines only). Skipping stages OK. Items stay. Costs your action.'),
    ('', 'Family', 'Same-family Pokémon count once per synergy type.'),
]))
REF.append(refcard('#d9a61e', ic('addpicks'), 'PICKS', [
    ('', 'Start', 'Deal 3 from Additional I, each with a Tier I item. Keep 1.'),
    ('', 'II / III / IV', 'Before rounds 2 / 5 / 8: deal 3, each with a random same-tier item (any item, gems too). Keep 1.'),
    ('', 'Unique · Legendary', 'Before rounds 6 / 9: deal 5, no items. Keep 1.'),
    ('', 'Unchosen', 'Pokémon are shuffled into that tier’s market deck. Starter items are discarded; other items go to the bottom of the item deck.'),
]))
REF.append(refcard('#d9a61e', ic('addpicks'), 'MARKET & ITEMS', [
    ('', 'Market', 'Each tier’s deck starts with 32 random Core Pokémon; 4 face up per tier. Empty deck: refill from Additional cards.'),
    ('', 'Items', 'From the ITEM ROW (2 face up per item tier). Max 3 per Pokémon, never two of the same. UNHOLDABLE (Gems, Red Scale): kept beside your lineup, no slot.'),
    ('', 'Bench', 'Cards beyond your level wait.'),
    ('', 'Hatch', 'Own decks, never in the shop. Baby gives one per loss. Not buyable; sells for 2 / 4 / 7. Not Baby.'),
]))
REF.append(refcard('#2e9e57', ic('PP'), 'SCORING', [
    ('', 'Start', 'Everyone starts at 20 points. 12 rounds.'),
    ('', 'Round bonus', 'R1–3: 0 · R4–6: +1 · R7–9: +2 · R10–12: +3.'),
    ('', 'Pairings', 'Rotating round robin: one seat fixed, the others rotate clockwise. Rounds 8–12 repeat 1–5. Bots fill empty seats.'),
    ('', 'End', 'Most points after round 12 wins.'),
]))
REF.append(refcard('#3f79c6', ic('AP'), 'SYNERGIES', [
    ('', 'Counting', 'Count cards in the whole lineup (fainted or not) that have a type; each evolution family counts once per type.'),
    ('', 'Level', 'Reach the thresholds on the synergy card for Level I, II, III (IV). Levels are fixed for the battle and apply only to cards with that type.'),
    ('', 'Lineup', 'Level = lineup size; excess cards stay on your bench.'),
]))
REF.append(refcard('#4a5a58', ic('PP'), 'POWER WORDS', [
    ('', 'Basic attack', 'The normal attack every turn: PHYSICAL damage equal to ATK, reduced by DEF.'),
    ('', 'Hit', 'Each hit is reduced separately by DEF / SP.DEF (min 1 gets through).'),
    ('', 'Gain +N stat', 'Lasts for the rest of the duel. -N lowers it (not below 0). “Gain +1 PP” = +1 charge.'),
    ('', 'Enters with', 'A bonus for your NEXT Pokémon in lineup order, applied when it enters (like BATON).'),
    ('', 'Heal · Cure', 'Heal restores HP up to max. Cure removes your own negative statuses.'),
]))
REF.append(refcard('#4a5a58', ic('PP'), 'POWER WORDS II', [
    ('', 'Negative status', 'Any status on these cards except PROTECT.'),
    ('', 'KO · Fallen', 'KO = HP reaches 0. “Fallen” = your Pokémon KO’d so far this duel.'),
    ('', 'Stat gained', 'Stored Power counts each time you gained a stat this duel.'),
    ('', 'Synergy', '“With a PSYCHIC synergy” = that type’s Level I or higher is active for you.'),
    ('', 'Cycles', 'Drum Beating does effect (1), then (2), then (3) on successive casts, then repeats.'),
    ('', 'Notes', '(stacks) adds up · (round up) · (min 1) · (max 3 times) = stops after 3.'),
]))

# ---------------- synergy cards
def syn_card(r):
    name, orig, ours, theme, *lv = r[:8]
    if name == 'Gourmet': lv = ['Level I dish strength', 'Level II dish strength', 'Level III dish strength']; theme = 'A chef serves its signature dish to the next card in lineup order (previous if last). Dishes are on the Gourmet Dishes cards.'
    t = name.upper()
    tc = TYPECOL.get(t, '#aaa')
    lvl = ''.join(f'<div class="lv"><em>{["I","II","III","IV"][i]}</em><span>{rich(x)}</span></div>' for i, x in enumerate(lv) if x)
    th = ours.replace(' / ', ' · ')
    return (f'<div class="card" style="--tc:{tc}"><div class="strip" style="height:.07in"></div>'
            f'<div class="rh" style="padding:.06in .08in .03in;gap:.06in">{ic(t)}<div><div style="font-size:11pt;line-height:1">{html.escape(name)}</div>'
            f'<div style="font-size:6pt;font-weight:700;color:#7d8685;letter-spacing:.04em;margin-top:.01in">NEED {th}</div></div></div>'
            f'<div class="th" style="margin-top:.04in;font-weight:800;color:#33403f">{html.escape(theme)}</div><div style="padding:0 .08in">{lvl}</div></div>')

def dish_cards():
    out = []
    for i in range(0, len(DISHES), 2):
        grp = DISHES[i:i + 2]
        rows = ''
        for r in grp:
            line, dish, cards, l1, l2, l3 = r[:6]
            rows += (f'<div style="margin-bottom:.04in"><div style="font-size:7pt;font-weight:800;display:flex;gap:.03in;align-items:center">{ic("DISH")}{html.escape(dish)}'
                     f'<span style="font-weight:600;font-size:5.4pt;color:#7d8685">({html.escape(line)} line)</span></div>'
                     f'<div class="lv"><em>I</em><span>{rich(l1)}</span></div><div class="lv"><em>II</em><span>{rich(l2)}</span></div><div class="lv"><em>III</em><span>{rich(l3)}</span></div></div>')
        out.append(f'<div class="card" style="--tc:#f0c070"><div class="strip" style="height:.07in"></div><div class="rh" style="padding:.05in .08in .02in">{ic("GOURMET")}<span>GOURMET DISHES {i//2+1}/{(len(DISHES)+1)//2}</span></div><div class="dishc" style="padding:.04in .08in">{rows}</div></div>')
    return out

def ref_back(label, tc=G):
    return (f'<div class="bk" style="--tc:{tc}"><div class="in"><div class="logo"><img src="file://{W}/assets/logo.png"><div class="num"><span>?</span></div></div>'
            f'<div class="lab" style="font-size:9pt">{label}</div></div></div>')

if __name__ == '__main__':
    write('PAC_reference', pages(REF))
    write('PAC_reference_BACKS', pages([ref_back('GUIDE') for _ in REF], back=True))
    SC = [syn_card(r) for r in SYNS]
    DC = dish_cards()
    write('PAC_synergies', pages(SC + DC))
    write('PAC_synergies_BACKS', pages([ref_back('SYNERGY', '#3f79c6') for _ in SC] + [ref_back('DISHES', '#d08a2a') for _ in DC], back=True))
    print(len(REF), len(SC), len(DC))
