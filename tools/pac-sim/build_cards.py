import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import csv, json, re, sys, collections, types
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

D0 = f'{ROOT}/pac-data/'
OUT = sys.argv[1]
tr = json.load(open(f'{ROOT}/keldaancommunity/pokemonautochess/app/public/dist/client/locales/en/translation.json'))
allp = list(csv.DictReader(open(D0 + 'pokemons-data.csv')))
core = list(csv.DictReader(open(D0 + 'core-value-tiers.csv')))

# ---------- scale (provisional) ----------
def hp_c(x): return max(3, round(x / 10))
def atk_c(x): return max(1, round(x / 5))
def df_c(x): return max(0, round(x / 7))
def spd_c(x): return max(1, round(x / 7))
def pp_c(x): return max(2, round(x / 35))
def D(x): return max(1, int(x / 10 + 0.5))          # flat PAC damage / shield -> game
def PA(p, base): return max(1, int(p / 100 * base / 6 + 0.5))  # percent of a PAC stat
def S(x): return min(3, max(1, int(x / 3 + 0.5)))   # seconds -> rounds
def AT(x): return max(1, int(x / 5 + 0.5))
def SP(x): return max(1, int(x / 7 + 0.5))

# ---------- charge powers ----------
# template(v, c) ; v = star-resolved numbers in order of the PAC arrays ; c = PAC stats
SPL = " SPLASH."
P = {
'ACCELEROCK': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL. Gain +1 SPEED and -1 DEF (max 3 times)."),
'ACID_ARMOR': ('Tank', lambda v, c: f"Gain +{AT(v[0])} DEF. The next 2 attackers that hit you lose 1 DEF each."),
'AGILITY': ('Speedster', lambda v, c: f"Gain +{SP(v[0])} SPEED for the rest of the duel."),
'AIR_SLASH': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and FLINCH the target (1 turn)."),
'AQUA_STEP': ('Speedster', lambda v, c: f"Gain +{SP(v[1])} SPEED, then deal {D(v[0])} SPECIAL."),
'AQUA_TAIL': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and gain {D(v[1])} SHIELD."),
'BITE': ('Drain', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL, heal half the damage dealt, and FLINCH the target (1 turn)."),
'BLAST_BURN': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'BLAZE_KICK': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and BURN the target. +30% damage (round up) if it was already burning."),
'BLOOD_MOON': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL and WOUND the target (2 turns)."),
'BUG_BUZZ': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, doubled if the target is PARALYZED."),
'BULLDOZE': ('Control', lambda v, c: f"Deal {D(v[0]*1.4)} SPECIAL and give the target -1 SPEED." + SPL),
'COLUMN_CRUSH': ('Striker', lambda v, c: f"Gain {D(v[0])} SHIELD, then deal SPECIAL equal to your total SHIELD."),
'CRABHAMMER': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL. KO the target if it is at 30% HP or less."),
'CRUNCH': ('Drain', lambda v, c: f"Deal {D(v[0])} SPECIAL. If it KOs the target, heal half the target's max HP."),
'DARKEST_LARIAT': ('MultiHit', lambda v, c: f"Hit {max(2, round(c.spd/25))} times for {PA(v[0], c.atk)} SPECIAL each (more hits with high SPEED) and FLINCH the target."),
'DARK_HARVEST': ('Drain', lambda v, c: f"Deal {D(v[0]*3)} SPECIAL and heal {max(1, round(D(v[0]*3)*0.3))}. You are FLINCHED on your next turn."),
'DOUBLE_SHOCK': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL. You are PARALYZED for 1 turn."),
'DRAGON_BREATH': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'DRAGON_TAIL': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and gain +{AT(v[1])} DEF and SP.DEF."),
'DRUM_BEATING': ('Support', lambda v, c: f"Cycles each cast: (1) gain {D(v[0]*.8)} SHIELD; (2) deal {D(v[1]*.8)} SPECIAL; (3) your next Pokemon enters with +{SP(v[2])} SPEED."),
'ENTANGLING_THREAD': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and PARALYZE the target (2 turns)." + SPL),
'FAIRY_WIND': ('Support', lambda v, c: f"Your next Pokemon enters with +{1 + (1 if v[0] >= 10 else 0)} charge."),
'FIRESTARTER': ('Speedster', lambda v, c: f"Gain +{SP(v[0])} SPEED, then deal {D(v[1]*.8)} SPECIAL."),
'FLAMETHROWER': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and BURN the target." + SPL),
'FLOWER_TRICK': ('Striker', lambda v, c: f"Plant a bouquet: after your next turn the target takes {D(v[0])} SPECIAL (+1 per crit it suffers meanwhile)."),
'FURY_SWIPES': ('MultiHit', lambda v, c: f"Make {max(1, round(v[0]/5))} extra basic attack(s) (ATK minus DEF each). If one KOs the target, gain +1 charge."),
'FUTURE_SIGHT': ('Striker', lambda v, c: f"After your 2nd turn from now, the opposing Pokemon takes {D(v[1]*3)} SPECIAL."),
'GEAR_GRIND': ('MultiHit', lambda v, c: f"Fire two gears: 2 x {PA(v[0], c.spd)} SPECIAL (scales with SPEED)."),
'GIGATON_HAMMER': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL. You are FATIGUED (no charge gain) for 2 turns."),
'GLAIVE_RUSH': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL. You and the target both get ARMOR BREAK (2 turns)."),
'GROWL': ('Control', lambda v, c: f"FLINCH the target (1 turn) and give it -{AT(v[0])} ATK (2 turns)."),
'GUILLOTINE': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL. If it KOs the target, gain +1 charge."),
'HEADBUTT': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and FLINCH the target (1 turn). Doubled if the target has SHIELD."),
'HEAVY_SLAM': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, +1 for every 3 max HP you have above the target's." + SPL),
'HEX': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, doubled if the target has a negative status."),
'HORN_ATTACK': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL and ARMOR BREAK the target (1 turn)."),
'HORN_DRILL': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL, +50% (round up) if your ATK is higher than the target's."),
'HYDRO_PUMP': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'ICE_BALL': ('Tank', lambda v, c: f"Gain +2 SP.DEF, then deal {D(v[0]) + PA(v[1], c.sdef)} SPECIAL (scales with your SP.DEF)."),
'ICICLE_CRASH': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'ICICLE_MISSILE': ('Control', lambda v, c: f"Launch {int(v[0])} icicle(s) for {D(v[1]*1.5)} SPECIAL each." + (" The last one FREEZES the target (1 turn)." if v[0] >= 3 else "")),
'ICY_WIND': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and give the target -{SP(v[1])} SPEED." + SPL),
'KING_SHIELD': ('Tank', lambda v, c: f"PROTECT (ignore all damage until your next turn) and gain {D(v[0]*2)} SHIELD."),
'KOWTOW_CLEAVE': ('Striker', lambda v, c: f"Deal {int(PA(150, c.atk)*1.5+0.5)} SPECIAL (always crit), +{max(1, round(PA(150, c.atk)*v[0]/100))} TRUE per fallen Pokemon of yours."),
'LEAF_BLADE': ('Striker', lambda v, c: f"Deal {int(PA(v[0], c.atk)*1.5+0.5)} TRUE (always crit, ignores all blocking)."),
'LEECH_LIFE': ('Drain', lambda v, c: f"Deal {D(v[0])} SPECIAL and heal the same amount."),
'LICK': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and PARALYZE + CONFUSE the target (1 turn)."),
'MAGICAL_LEAF': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and ARMOR BREAK the target (1 turn)."),
'MAGIC_POWDER': ('Tank', lambda v, c: f"Gain {D(v[0])} SHIELD and FLINCH the target ({S(v[1])} turn(s))."),
'MAGNET_BOMB': ('Control', lambda v, c: f"Deal {D(v[0]*1.5)} SPECIAL and give the target -1 SPEED (LOCKED: it cannot FLY AWAY or dodge until its next turn)." + f" SPLASH {D(v[1])}."),
'MANTIS_BLADES': ('MultiHit', lambda v, c: f"Three hits of {D(v[0])}: one PHYSICAL, one SPECIAL, one TRUE."),
'METEOR_MASH': ('MultiHit', lambda v, c: f"Hit 3 times (4 with a PSYCHIC synergy) for {PA(v[0], c.atk)} SPECIAL each, then gain +1 ATK."),
'MYSTICAL_FIRE': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and give the target -1 AP."),
'NIGHTMARE': ('Control', lambda v, c: f"FATIGUE the target ({S(v[0])} turn(s)). If it has a negative status, also deal {D(v[1])} SPECIAL."),
'NUZZLE': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and PARALYZE the target ({S(v[1])} turn)."),
'PECK': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL."),
'PETAL_DANCE': ('MultiHit', lambda v, c: f"Release {max(2, round(v[0]/2))} petals for {D(v[1])} SPECIAL each."),
'PLAY_ROUGH': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and CHARM the target (-2 ATK, 2 turns)."),
'PSYCHIC': ('Control', lambda v, c: f"Deal {D(v[0]*1.5)} SPECIAL; the target loses 1 charge." + SPL),
'PSYCHO_CUT': ('MultiHit', lambda v, c: f"Three blades for {int(D(v[0])*1.5+0.5)} SPECIAL each (crit)."),
'RAPID_SPIN': ('Tank', lambda v, c: f"Deal {D(v[0])} SPECIAL and gain +{max(1, round(PA(v[1], c.atk)))} DEF and SP.DEF."),
'REFLECT': ('Tank', lambda v, c: f"For {S(v[0])} turn(s), all PHYSICAL damage you take is blocked and {int(v[1])}% of it is reflected as SPECIAL."),
'RETALIATE': ('Striker', lambda v, c: f"Deal {PA(v[0], c.atk)} SPECIAL, plus one more equal hit for each fallen Pokemon of yours."),
'ROCK_ARTILLERY': ('MultiHit', lambda v, c: f"Throw {max(2, round(v[0]/5))} rocks for {D(v[1]*1.5)} SPECIAL each."),
'ROCK_SLIDE': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, doubled if the target is FLYING."),
'SALT_CURE': ('Support', lambda v, c: f"Gain {D(v[0])} SHIELD and cure your statuses. If the target is WATER, STEEL or GHOST, BURN it."),
'SHADOW_BALL': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL and give the target -1 SP.DEF (stacks)."),
'SHOCKWAVE': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'SILVER_WIND': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL. Gain +1 ATK and +1 SPEED."),
'SING': ('Control', lambda v, c: f"Put the target to SLEEP ({S(v[1])} turn(s)): it skips its turns."),
'SLASH': ('Striker', lambda v, c: f"Deal {int(D(v[0])*1.5+0.5)} SPECIAL (always crit)."),
'SNIPE_SHOT': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, ignoring SP.DEF."),
'SOAK': ('Support', lambda v, c: f"Deal {D(v[0])} SPECIAL. Your next Pokemon enters with +1 charge."),
'SOFT_BOILED': ('Support', lambda v, c: f"Cure your statuses and gain {D(v[0])} SHIELD. Your next Pokemon enters with half that SHIELD (round up)."),
'SPIKY_SHIELD': ('Tank', lambda v, c: f"For {S(v[0])} turn(s), whoever hits you with a PHYSICAL attack is WOUNDED and takes {PA(v[1], c.defn)} SPECIAL."),
'STEAMROLLER': ('Striker', lambda v, c: f"Deal {PA(v[0]*.75, c.spd)} SPECIAL (scales with SPEED)."),
'STORED_POWER': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL, +1 for each stat boost you have (ATK, SPEED, DEF, SP.DEF, AP)."),
'STRING_SHOT': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and PARALYZE the target (2 turns)."),
'TELEPORT': ('Striker', lambda v, c: f"Your next attack this duel deals +{D(v[0])} extra SPECIAL."),
'TERRAIN_PULSE': ('Support', lambda v, c: f"Heal {max(1, round(v[0]/100*c.hpc))}. With GRASS gain +1 DEF; with ELECTRIC gain +1 SPEED; with PSYCHIC gain +1 AP."),
'THRASH': ('Striker', lambda v, c: f"Gain +{max(1, round(v[0]/100*c.atkc))} ATK for the duel, then CONFUSE yourself (your next attack is halved)."),
'THUNDER_SHOCK': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL."),
'TICKLE': ('Control', lambda v, c: f"Give the target -1 ATK and -1 DEF (2 turns)."),
'TORCH_SONG': ('MultiHit', lambda v, c: f"Four flames for {PA(50, c.atk)} SPECIAL each; the last BURNs the target. Gain +{int(v[2])} AP."),
'TRANSE': ('Support', lambda v, c: f"Heal 50% of max HP (min 1) and return to normal form."),
'TRI_ATTACK': ('Control', lambda v, c: f"Deal {D(v[0]*.8)} SPECIAL and choose: BURN (2 turns), PARALYZE (1 turn) or FREEZE (1 turn)."),
'TROP_KICK': ('Control', lambda v, c: f"Deal {D(v[0])} SPECIAL and give the target -{AT(v[1])} ATK (2 turns)."),
'TWISTER': ('Striker', lambda v, c: f"Deal {D(v[0])} SPECIAL." + SPL),
'UPROAR': ('Striker', lambda v, c: f"Deal {D(v[0]*3)} SPECIAL. You cannot be put to SLEEP until your next turn."),
'VOLT_SWITCH': ('Speedster', lambda v, c: f"Deal {D(v[0])} SPECIAL, ignoring SP.DEF."),
'WAVE_SPLASH': ('Tank', lambda v, c: f"Gain SHIELD equal to {int(v[0])}% of max HP ({max(1, round(v[0]/100*c.hpc))}), then deal that much SPECIAL."),
'WHEEL_OF_FIRE': ('MultiHit', lambda v, c: f"Deal {D(v[0])} SPECIAL twice."),
'WHIRLPOOL': ('MultiHit', lambda v, c: f"Four whirlpools: 4 x {PA(v[0], c.atk)} SPECIAL."),
'WISH': ('Tank', lambda v, c: f"Gain {D(v[0])} SHIELD and PROTECT (ignore all damage) for 1 turn."),
}

def parse_arrays(desc):
    out = []
    for m in re.findall(r'\[([^\]]*)\]', desc):
        nums = []
        for t in m.split(','):
            t = t.strip()
            try: nums.append(float(t))
            except ValueError: pass
        if nums: out.append(nums)
    return out

def resolve(ab, stars):
    arrs = parse_arrays(tr['ability_description'].get(ab, ''))
    return [a[min(stars - 1, len(a) - 1)] for a in arrs]

# ---------- synergies (draft): thresholds 2 / 3 / 4+ unique cards fielded this duel ----------
SYN = {
'NORMAL': ("Enter with SHIELD", "3 SHIELD", "5 SHIELD", "7 SHIELD and +1 DEF"),
'GRASS': ("Heal every turn; overheal grows max HP (max +3)", "Heal 1 at end of each of its turns", "Heal 2 at end of each of its turns", "Heal 2 per turn; overheal gives +1 max HP"),
'FIRE': ("Attacks BURN; ATK grows", "Attacks BURN the target", "Attacks BURN; +1 ATK after each charge power", "Attacks BURN; +1 ATK at the end of every one of its turns (max +4)"),
'WATER': ("Charge faster", "Enter with +1 charge", "Enter with +1 charge; +1 charge each time you cast", "Attacks give +2 charge instead of +1"),
'ELECTRIC': ("Basic attacks trigger extra hits", "Extra hit of 1 SPECIAL after each attack", "Extra hit of 2 SPECIAL after each attack", "Two extra hits of 2 SPECIAL after each attack"),
'FIGHTING': ("Block more; counter-strike", "+1 DEF", "+2 DEF", "+2 DEF; every 3rd hit you take destroys the attacker's SHIELD and deals 1 TRUE"),
'PSYCHIC': ("Gain AP (+1 damage to each charge power per AP)", "+1 AP, +1 SP.DEF", "+2 AP, +1 SP.DEF, enter with +1 charge", "+3 AP, +2 SP.DEF, enter with +1 charge"),
'DARK': ("Critical hits (x1.5)", "Every 3rd attack is a crit", "Every 2nd attack is a crit", "Every 2nd attack is a crit and crits are x2"),
'STEEL': ("Part of your damage is TRUE; helps next ally", "1 of your attack damage is TRUE", "2 of your attack damage is TRUE", "3 TRUE; your next Pokemon enters with +1 DEF"),
'GROUND': ("Dig in: gain stats the longer you stay", "+1 DEF at end of every 2nd turn (max 3)", "+1 DEF and +1 ATK at end of every 2nd turn (max 3)", "+1 DEF and +1 ATK at end of every turn (max 4)"),
'POISON': ("Attacks POISON the target", "Attacks POISON (1 stack: 1 true dmg per turn)", "Each attack adds a stack (max 3)", "Max 5 stacks"),
'DRAGON': ("Amplify other synergies", "+2 HP", "+2 HP and +1 ATK", "+2 HP, +1 ATK; every other synergy on this card counts +1 level (max 3)"),
'FIELD': ("Enter faster and healthier", "2 SHIELD on entry", "+1 SPEED and 2 SHIELD on entry", "+1 SPEED and 3 SHIELD on entry"),
'MONSTER': ("Flinch and grow on KO", "Your first attack after entry FLINCHES the target", "Also: on a KO gain +1 ATK and heal 2", "Also: FLINCH every first attack and +1 max HP on KO"),
'HUMAN': ("Heal when you deal damage", "Heal 1 per attack", "Heal 1 per attack, 2 per charge power", "Heal 2 per attack and per charge power"),
'AQUATIC': ("Resist status; tidal wave", "Ignore the first negative status you receive", "Also: on its 3rd turn on the field, tidal wave: cure yourself, deal 2 to the foe", "Tidal wave deals 4 and heals you 2"),
'BUG': ("Swarm tokens block attacks", "1 SWARM token (blocks the next attack completely)", "2 SWARM tokens", "3 SWARM tokens; a spent token deals 1 TRUE back"),
'FLYING': ("Fly away at low HP", "Once, at or below 50% HP: PROTECT for 1 turn", "Same, and gain +1 SP.DEF", "Can trigger twice"),
'FLORA': ("Bloom when KO'd", "When KO'd, your next Pokemon enters with 2 SHIELD", "3 SHIELD and +1 DEF", "4 SHIELD, +1 DEF, +1 ATK"),
'ROCK': ("Gain DEF and resist crits", "+1 DEF and +1 SP.DEF", "+2 DEF and +1 SP.DEF; crits against you are normal hits", "+3 DEF and +2 SP.DEF; crits against you are normal hits"),
'GHOST': ("Evasion; curse on attack", "Every 3rd attack against you misses", "Every 3rd attack misses; your attacks FLINCH the target (once per Pokemon)", "Every 2nd attack misses; your attacks FLINCH the target"),
'FAIRY': ("Wand bonus damage on attacks", "+1 TRUE on each attack", "+2 TRUE on each attack", "+2 TRUE on attacks and +2 on charge powers"),
'ICE': ("Freeze chance; SP.DEF", "+1 SP.DEF", "+2 SP.DEF; every 5th attack FREEZES (1 turn)", "+2 SP.DEF; every 4th attack FREEZES (1 turn)"),
'FOSSIL': ("Awaken at low HP", "Once, at or below 50% HP: +2 SHIELD, +1 ATK", "+4 SHIELD, +1 ATK", "+6 SHIELD, +2 ATK"),
'SOUND': ("Cries empower you and the next ally", "+1 ATK on your first cast", "+1 ATK on each of your first 2 casts", "+1 ATK on each of your first 3 casts, +1 SPEED once, and every cast gives your next Pokemon +1 charge"),
'ARTIFICIAL': ("Stronger when holding items", "+1 ATK per held item", "+1 ATK and +1 SHIELD per held item", "+1 ATK, +1 SHIELD and +1 AP per held item"),
'BABY': ("Comfort after losses", "+1 HP per current losing streak (max +3)", "Also heal 1 each turn", "Also: if you lose this duel, gain 1 gold"),
'LIGHT': ("Spotlight bonuses on entry", "1 SHIELD on entry", "Enter with +1 charge", "+1 charge, +1 ATK, 2 SHIELD on entry"),
'WILD': ("Attacks WOUND", "Attacks WOUND the target (1 turn); +1 ATK", "+2 ATK", "WOUND lasts 2 turns; +3 ATK"),
'AMORPHOUS': ("Stat from variety of synergies", "+1 HP per other active synergy on this card", "+2 HP per other active synergy, and +1 SPEED", "Same as level II"),
'GOURMET': ("Cook a dish on entry", "2 SHIELD on entry", "3 SHIELD and +1 ATK on entry", "4 SHIELD, +1 ATK, +1 DEF on entry"),
}

KEYWORDS = [
("Initiative bar", "At the start of a duel the bar is at 0 (even); the faster Pokemon moves first (equal speed: lower points, then random). Whenever a Pokemon moves it pushes the bar toward the OTHER side by the opponent's SPEED. The side the bar is on moves next. If the bar lands exactly on 0 it switches to the side that did NOT just move. Equal speeds alternate; speed 2 vs 1 gives the fast one 2 turns per slow turn. The bar carries over when a Pokemon is KO'd; the replacement takes over its side."),
("Turn", "A Pokemon's turn: (1) attack, (2) +1 charge, (3) if charge is full, cast its charge power and reset to 0, (4) resolve its synergy powers. All durations ('2 turns', 'each turn') count the affected Pokemon's OWN turns and tick at the end of its turn."),
("Speed", "PAC speed divided by 7 (cards range about 3-11, most 6-8). A small gap is a small edge: 7 vs 8 gives the faster card about 1 extra turn in 8."),
("Attack", "Deal ATK as PHYSICAL damage. Minimum 1."),
("DEF / SP.DEF", "Flat amount blocked from each PHYSICAL / SPECIAL hit (min 1 damage gets through). TRUE ignores both."),
("SHIELD", "Absorbs damage before HP. Not reduced by DEF. Lost when the card is KO'd."),
("Charge", "Cards cast their charge power when charge reaches Max PP."),
("AP", "Ability power: +1 damage to a charge power's damage per AP."),
("BURN", "1 TRUE damage at the end of each of its turns, for 3 turns (reapplying resets the timer)."),
("POISON", "1 TRUE damage at the end of each of its turns; reapplying adds +1 per turn (stacks) for the rest of that card's time on the field."),
("PARALYZE", "-1 SPEED and its attack gains no charge."),
("FLINCH", "Cannot cast its charge power on its next turn (charge stays full). SILENCE works the same."),
("SLEEP", "Skips its next turn(s) entirely."),
("FREEZE", "Skips its next turn and counts as DEF 0 / SP.DEF 0 until then."),
("CONFUSE", "Its next attack is halved."),
("CHARM", "-2 ATK for 2 turns."),
("WOUND", "Cannot heal or gain SHIELD."),
("ARMOR BREAK", "DEF and SP.DEF count as 0."),
("FATIGUE", "Gains no charge."),
("PROTECT", "Ignores all damage until its next turn begins."),
("SPLASH", "Half of the ability's damage (round down) is also dealt to the opponent's NEXT Pokemon when it enters."),
("Carry-over", "Powers that affect 'your next Pokemon' apply when it enters."),
("Crit", "x1.5 damage (round up)."),
("Reveal and order", "At the start of a battle every Pokemon and item on both sides is revealed. Each player sets their lineup order beforehand; Pokemon enter in that order (no choosing replacements). Open question: set before or after seeing the opponent's roster."),
("Synergy level", "Count the unique cards in the whole lineup with a type (fainted or not); 2 = level I, 3 = level II, 4+ = level III. Levels are fixed for the whole battle and apply only to cards that have that type."),
("Scale (provisional)", "HP /10 (min 3), ATK /5 (min 1), DEF and SP.DEF /7, SPEED /7, Max PP /35 (min 2; PAC 50-80 gives 2, 100-120 gives 3), flat powers /10 (percent-of-stat powers: percent x PAC stat /6). Simulated; see duel simulator report."),
]

class C: pass

wb = Workbook()
hdr = PatternFill('solid', fgColor='1F2937'); hf = Font(bold=True, color='FFFFFF')
def sheet(ws, head, rows, widths):
    ws.append(head)
    for c in ws[1]:
        c.fill = hdr; c.font = hf; c.alignment = Alignment(vertical='center')
    for r in rows: ws.append(r)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'; ws.auto_filter.ref = ws.dimensions

# cards
rows = []
missing = set()
for c0 in core:
    p = [x for x in allp if x['Index'] == c0['Index'] and x['Name'] == c0['Name']][0]
    stars = int(c0['Stars'])
    c = C()
    c.hp, c.atk, c.defn, c.sdef, c.spd, c.pp = [int(p[k]) for k in ('HP', 'Attack', 'Defense', 'Special Defense', 'Speed', 'Max PP')]
    c.hpc, c.atkc = hp_c(c.hp), atk_c(c.atk)
    ab = p['Ability']
    if ab not in P:
        missing.add(ab); role, txt = '?', ab
    else:
        role, f = P[ab]
        txt = f(resolve(ab, stars), c)
    types_ = [p[f'Type {i}'] for i in range(1, 5) if p[f'Type {i}']]
    nm = c0['Name'].title().replace('_', ' ')
    rows.append([c0['TierGroup'], c0['Index'], nm, stars, float(c0['Value']), int(c0['Cost']),
                 ' / '.join(t.title() for t in types_),
                 c.hpc, c.atkc, df_c(c.defn), df_c(c.sdef), spd_c(c.spd), pp_c(c.pp),
                 tr['ability'].get(ab, ab), role, txt, 'alt form' if c0['AltForm'] == 'true' else ''])
assert not missing, missing
order = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4}
rows.sort(key=lambda r: (order[r[0]], r[4], r[2]))
ws = wb.active; ws.title = 'Cards'
sheet(ws, ['Tier', 'Dex', 'Card', 'Stars', 'Value', 'PAC cost', 'Synergies', 'HP', 'ATK', 'DEF', 'SP.DEF', 'SPEED', 'Max PP',
           'Charge power', 'Role', 'Charge power text (draft)', 'Note'], rows,
      [6, 7, 18, 6, 7, 8, 24, 5, 5, 5, 7, 7, 7, 18, 10, 70, 10])

ws = wb.create_sheet('Synergies')
srows = []
for k, v in SYN.items():
    srows.append([k.title(), v[0], v[1], v[2], v[3]])
sheet(ws, ['Synergy', 'Theme', 'Level I (2 cards)', 'Level II (3 cards)', 'Level III (4+ cards)'], srows, [14, 36, 38, 44, 54])

ws = wb.create_sheet('Rules & Keywords')
sheet(ws, ['Term', 'Draft rule'], KEYWORDS, [22, 120])

# charge powers by star
ws = wb.create_sheet('Charge powers')
used = collections.defaultdict(list)
for r in rows: used[r[13]].append((r[2], r[3]))
prow = []
for ab, (role, f) in sorted(P.items(), key=lambda kv: tr['ability'].get(kv[0], kv[0])):
    cc = C(); cc.hp = 140; cc.atk = 12; cc.defn = 30; cc.sdef = 30; cc.spd = 50; cc.hpc = 14; cc.atkc = 2
    nm = tr['ability'].get(ab, ab)
    cards = ', '.join(sorted({n for n, s in used.get(nm, [])}))
    prow.append([nm, role, len(used.get(nm, [])), cards])
sheet(ws, ['Power', 'Role', '# cards', 'Used by'], prow, [22, 10, 8, 120])
wb.save(OUT)
print(len(rows), 'cards', len(prow), 'powers')
