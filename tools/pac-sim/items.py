"""Item table for the PAC board game duel. Stats are already in card scale.
Conversions from PAC: ATK/5, DEF & SP.DEF/7, HP/10, speed/12, AP/25, shield/20, start charge 1 per 15 PP.
Flags are read by duel.py (see Duel.item_* hooks)."""
STAT_KEYS = ('hp', 'atk', 'df', 'sdf', 'spd', 'ap', 'ch', 'sh', 'crit')
ITEMS = {}
ORDER = []

def I(key, name, cat, text, stats=None, **flags):
    ITEMS[key] = dict(key=key, name=name, cat=cat, text=text, stats=stats or {}, flags=flags)
    ORDER.append(key)

# ---------------- components (the 8 base items + Fossil Stone + Silk Scarf) ----------------
I('TWISTED_SPOON', 'Twisted Spoon', 'Component', '+1 AP.', dict(ap=1))
I('MAGNET', 'Magnet', 'Component', '+1 speed.', dict(spd=1))
I('BLACK_GLASSES', 'Black Glasses', 'Component', '+10% crit (every 10th attack crits).', dict(crit=10))
I('MIRACLE_SEED', 'Miracle Seed', 'Component', '+2 HP.', dict(hp=2))
I('CHARCOAL', 'Charcoal', 'Component', '+1 ATK.', dict(atk=1))
I('NEVER_MELT_ICE', 'Never-Melt Ice', 'Component', '+1 SP.DEF.', dict(sdf=1))
I('HEART_SCALE', 'Heart Scale', 'Component', '+1 DEF.', dict(df=1))
I('MYSTIC_WATER', 'Mystic Water', 'Component', 'Enters with 1 charge.', dict(ch=1))
I('FOSSIL_STONE', 'Fossil Stone', 'Component', '+1 shield on entry.', dict(sh=1))
I('SILK_SCARF', 'Silk Scarf', 'Component', '+2 shield on entry.', dict(sh=2))

# ---------------- stones: holder gains a type ----------------
for k, n, t, extra in [
    ('OLD_AMBER', 'Old Amber', 'FOSSIL', {}), ('DAWN_STONE', 'Dawn Stone', 'PSYCHIC', dict(ap=1)),
    ('WATER_STONE', 'Water Stone', 'WATER', dict(ch=1)), ('THUNDER_STONE', 'Thunder Stone', 'ELECTRIC', dict(spd=1)),
    ('FIRE_STONE', 'Fire Stone', 'FIRE', dict(atk=1)), ('MOON_STONE', 'Moon Stone', 'FAIRY', dict(df=1)),
    ('DUSK_STONE', 'Dusk Stone', 'DARK', dict(crit=20)), ('LEAF_STONE', 'Leaf Stone', 'GRASS', dict(hp=3)),
    ('ICE_STONE', 'Ice Stone', 'ICE', dict(sdf=1))]:
    I(k, n, 'Stone', f'Holder gains the {t.title()} type' + (' and ' + ', '.join((f'+{v}% crit' if a == 'crit' else f'+{v} ' + dict(sdf='SP.DEF', spd='speed', ch='starting charge', df='DEF', atk='ATK', hp='HP', ap='AP')[a]) for a, v in extra.items()) if extra else '') + '.', extra, type=t)

# ---------------- crafted items (PAC two-component recipes, bought directly here) ----------------
I('CHOICE_SPECS', 'Choice Specs', 'Crafted', '+4 AP (extra damage on the first damage of a charge power).', dict(ap=4))
I('SOUL_DEW', 'Soul Dew', 'Crafted', 'Each of its own turns the holder gains +1 AP (max +4) and 1 charge every 3rd turn.', soul=1)
I('UPGRADE', 'Upgrade', 'Crafted', 'Every 2nd attack: +1 speed (max +4). Starts with +1 speed.', dict(spd=1), upgrade=1)
I('REAPER_CLOTH', 'Reaper Cloth', 'Crafted', '+1 AP, +20% crit; crits also add +1 to charge power damage.', dict(ap=1, crit=20), reaper=1)
I('ABILITY_SHIELD', 'Ability Shield', 'Crafted', 'On entry: shield worth 3 and immune to negative statuses for 3 of its turns.', dict(ap=1), abshield=1)
I('POWER_LENS', 'Power Lens', 'Crafted', 'Special damage blocked by SP.DEF is dealt back to the attacker as true damage. +1 SP.DEF, +1 AP.', dict(sdf=1, ap=1), lens=1)
I('POKEMONOMICON', 'Pokemonomicon', 'Crafted', 'When the holder deals special damage it burns the target (3 turns) and lowers its SP.DEF by 1 (max -2). +1 ATK, +1 AP.', dict(atk=1, ap=1), nomicon=1)
I('HEAVY_DUTY_BOOTS', 'Heavy-Duty Boots', 'Crafted', 'Immune to flinch and to splash damage. +2 AP, +2 DEF.', dict(ap=2, df=2), boots=1)
I('AQUA_EGG', 'Aqua Egg', 'Crafted', 'Starts with 1 charge; regains 1 charge after casting.', dict(ch=1), aqua=1)
I('BLUE_ORB', 'Blue Orb', 'Crafted', 'Every 3rd attack: chain lightning, 1 special damage and the foe loses 1 charge. Starts with 1 charge, +1 speed.', dict(ch=1, spd=1), blueorb=1)
I('SCOPE_LENS', 'Scope Lens', 'Crafted', '+25% crit. Crits steal 1 charge from the target. Starts with 1 charge.', dict(ch=1, crit=25), scope=1)
I('STAR_DUST', 'Star Dust', 'Crafted', 'After casting: gain 2 shield. +1 SP.DEF, starts with 1 charge.', dict(sdf=1, ch=1), stardust=2)
I('GREEN_ORB', 'Green Orb', 'Crafted', 'Heals 1 HP every 2nd own turn; healing that would overflow becomes 1 charge. +2 HP.', dict(hp=2), greenorb=1)
I('DEEP_SEA_TOOTH', 'Deep Sea Tooth', 'Crafted', '+1 ATK. Every 2nd attack gains an extra charge; a KO gains 1 more. Starts with 1 charge.', dict(atk=1, ch=1), dst=1)
I('SHINY_CHARM', 'Shiny Charm', 'Crafted', 'First time the holder drops to half HP or less: protected from the next hit and gains 1 charge. +1 DEF.', dict(df=1), charm30=1)
I('XRAY_VISION', 'XRay Vision', 'Crafted', '+3 speed. Immune to sleep.', dict(spd=3), immune_sleep=1)
I('RAZOR_FANG', 'Razor Fang', 'Crafted', 'Attacks break armor (DEF/SP.DEF 0) for 1 of the foe\'s turns. +1 speed, +10% crit.', dict(spd=1, crit=10), armorbreak=1)
I('GRACIDEA_FLOWER', 'Gracidea Flower', 'Crafted', '+2 speed, and the next Pokemon you send in also gains +1 speed.', dict(spd=2), gracidea=1)
I('LOADED_DICE', 'Loaded Dice', 'Crafted', 'Every 2nd attack also splashes half its damage onto the foe\'s next Pokemon. +1 speed, +1 SP.DEF.', dict(spd=1, sdf=1), loaded=1)
I('PUNCHING_GLOVE', 'Punching Glove', 'Crafted', 'Attacks deal +1 true damage. +1 speed, +1 ATK.', dict(spd=1, atk=1), glove=1)
I('MUSCLE_BAND', 'Muscle Band', 'Crafted', 'Every 3rd hit taken: +1 DEF, +1 ATK, +1 speed (max 3 times). +1 speed, +1 DEF.', dict(spd=1, df=1), muscle=1)
I('WONDER_BOX', 'Wonder Box', 'Crafted', 'At battle start, take the top Tier III and Tier II item of their decks and attach them to the holder for this battle (max 3 items: Tier III first, Tier II only if there is room). They go back to the bottom of their decks after the battle.', wonder=1)
I('SMOKE_BALL', 'Smoke Ball', 'Crafted', 'First time at half HP or less: gain 4 shield and paralyze the foe (2 turns). +10% crit.', dict(crit=10), smoke=1)
I('WIDE_LENS', 'Wide Lens', 'Crafted', 'Every 2nd attack also has SPLASH 1. +1 SP.DEF.', dict(sdf=1), wide=1)
I('RAZOR_CLAW', 'Razor Claw', 'Crafted', '+50% crit (every 2nd attack crits), +1 ATK.', dict(crit=50, atk=1))
I('SAFETY_GOGGLES', 'Safety Goggles', 'Crafted', 'Immune to all negative statuses. +10% crit, +1 DEF.', dict(crit=10, df=1), immune_neg=1)
I('KINGS_ROCK', "King's Rock", 'Crafted', '+8 HP and 3 shield on entry.', dict(hp=8, sh=3))
I('STICKY_BARB', 'Sticky Barb', 'Crafted', 'When hit by an attack: 1 true damage back and the attacker is wounded for 1 turn. +1 DEF, +2 HP.', dict(df=1, hp=2), barb=1)
I('PROTECTIVE_PADS', 'Protective Pads', 'Crafted', 'Double damage against a foe that has shield. +1 ATK, +3 shield.', dict(atk=1, sh=3), pads=1)
I('MAX_REVIVE', 'Max Revive', 'Crafted', 'The first time the holder would be KO\'d it returns to full HP instead.', revive=1)
I('ASSAULT_VEST', 'Assault Vest', 'Crafted', '+6 SP.DEF. Poison damage halved, burn does nothing.', dict(sdf=6), vest=1)
I('SHELL_BELL', 'Shell Bell', 'Crafted', 'Heals 1 each time it attacks. +1 ATK, +1 SP.DEF.', dict(atk=1, sdf=1), shellbell=1)
I('POKE_DOLL', 'Poke Doll', 'Crafted', 'Incoming physical and special damage -1 (before DEF and SP.DEF). +1 DEF, +1 SP.DEF.', dict(df=1, sdf=1), doll=1)
I('RED_ORB', 'Red Orb', 'Crafted', '+2 ATK. 1 damage of each attack is TRUE damage (ignores DEF).', dict(atk=2), redorb=1)
I('FLAME_ORB', 'Flame Orb', 'Crafted', '+50% base ATK, immune to freeze. The holder is BURNED for the whole battle (counts as a negative status) and takes 1 damage every 2nd own turn. +1 DEF.', dict(df=1), flameorb=1)
I('ROCKY_HELMET', 'Rocky Helmet', 'Crafted', '+3 DEF. Foe crits do no bonus damage against the holder.', dict(df=3), helmet=1)
I('FRIEND_BOW', 'Friend Bow', 'Crafted', 'Holder gains the Normal type. +2 shield.', dict(sh=2), type='NORMAL')
I('BLACK_BELT', 'Black Belt', 'Crafted', '+30% crit. Crits give shield equal to half the damage dealt. +1 shield.', dict(crit=30, sh=1), blackbelt=1)
I('MACH_RIBBON', 'Mach Ribbon', 'Crafted', '+1 speed, and +1 more every 4th own turn (max +3). +1 shield.', dict(spd=1, sh=1), mach=1)
I('EXPLOSIVE_BAND', 'Explosive Band', 'Crafted', '3 shield, +1 ATK. The first time its shield breaks it explodes for half the shield gained so far as special damage.', dict(sh=3, atk=1), explosive=1)
I('TWIST_BAND', 'Twist Band', 'Crafted', 'Negative statuses on the holder become +1 ATK each instead. +3 SP.DEF, 3 shield.', dict(sdf=3, sh=3), twist=1)
I('LUCKY_RIBBON', 'Lucky Ribbon', 'Crafted', 'Dodges every 7th incoming attack. +2 AP, +1 shield.', dict(ap=2, sh=1), dodge=7)
I('BIG_EATER_BELT', 'Big Eater Belt', 'Crafted', '+6 HP. +2 shield on entry.', dict(hp=6, sh=2))
I('COVER_BAND', 'Cover Band', 'Crafted', 'While on the bench: the first hit that would KO your active Pokemon leaves it at 1 HP instead, and the holder then enters with that much less HP. Enters with +2 DEF.', dict(df=2), cover=1)
I('EFFICIENT_BANDANNA', 'Efficient Bandanna', 'Crafted', 'Holder needs 1 less charge to cast (min 2). 1 shield.', dict(sh=1), cheap=1)
I('NULLIFY_BANDANNA', 'Nullify Bandanna', 'Crafted', 'Cannot cast its charge power. Each time it would gain charge, it gains +1 ATK for the rest of the battle instead. +2 shield.', dict(sh=2), nullify=1)
I('LIGHT_BALL_PAC', 'placeholder', 'x', '', None)
del ITEMS['LIGHT_BALL_PAC']; ORDER.remove('LIGHT_BALL_PAC')

# ---------------- tools ----------------
I('LIGHT_BALL', 'Light Ball', 'Tool', 'Holder gains the Light type. +2 AP.', dict(ap=2), type='LIGHT')
I('PROTECTOR', 'Protector', 'Tool', 'Holder gains the Rock type. +4 shield.', dict(sh=4), type='ROCK')
I('DRAGON_SCALE', 'Dragon Scale', 'Tool', 'Holder gains the Dragon type. +1 DEF, +1 SP.DEF.', dict(df=1, sdf=1), type='DRAGON')
I('METAL_COAT', 'Metal Coat', 'Tool', 'Holder gains the Steel type. +1 DEF, +1 SP.DEF.', dict(df=1, sdf=1), type='STEEL')
I('AIR_BALLOON', 'Air Balloon', 'Tool', 'Holder gains the Flying type. +2 speed; dodges every 10th incoming attack.', dict(spd=2), type='FLYING', dodge=10)
I('MACHO_BRACE', 'Macho Brace', 'Tool', 'Holder gains the Fighting type. +3 ATK, -1 speed.', dict(atk=3, spd=-1), type='FIGHTING')
I('METRONOME', 'Metronome', 'Tool', 'Holder gains the Sound type. Gains 1 charge every 5th own turn.', None, type='SOUND', metronome=5)
I('EXPLORER_KIT', 'Explorer Kit', 'Tool', 'Holder gains the Ground type. +1 DEF, +1 SP.DEF, +1 ATK.', dict(df=1, sdf=1, atk=1), type='GROUND')
I('SPELL_TAG', 'Spell Tag', 'Tool', 'Holder gains the Ghost type. When it is KO\'d, the foe\'s active Pokemon takes 2 TRUE damage.', None, type='GHOST', spelltag=1)
I('SHED_SHELL', 'Shed Shell', 'Tool', 'Holder gains the Bug type. -2 max HP.', dict(hp=-2), type='BUG')
I('BERSERK_GENE', 'Berserk Gene', 'Tool', 'Holder gains the Monster type. +2 ATK.', dict(atk=2), type='MONSTER')
I('SURFBOARD', 'Surf Board', 'Tool', 'Holder gains the Aquatic type. First cast also splashes 3 special damage on the foe\'s next Pokemon.', None, type='AQUATIC', surf=1)
I('COOKING_POT', 'Cooking Pot', 'Tool', 'Holder gains the Gourmet type. +1 DEF; while burned gains +2 speed.', dict(df=1), type='GOURMET')
I('RUNNING_SHOES', 'Running Shoes', 'Tool', 'Holder gains the Field type. +1 speed, +1 more every 5th own turn (max +3).', dict(spd=1), type='FIELD', mach=5)
I('INCENSE', 'Incense', 'Tool', 'Holder gains the Flora type. +1 SP.DEF.', dict(sdf=1), type='FLORA')
I('ELECTIRIZER', 'Electirizer', 'Tool', 'Holder gains the Electric type. Every 3rd attack PARALYZES the foe for 1 turn. +1 speed.', dict(spd=1), type='ELECTRIC', parat=3)
I('MAGMARIZER', 'Magmarizer', 'Tool', 'Holder gains the Fire type. Immune to burn damage; +2 speed while burning. +1 ATK.', dict(atk=1), type='FIRE', vestburn=1)
I('POKERUS_VIAL', 'Pokerus Vial', 'Tool', 'Holder gains the Poison type. Every 3rd own turn: +1 ATK and +1 AP (max 3 times).', None, type='POISON', pokerus=1)
I('MAX_ELIXIR', 'Max Elixir', 'Tool', 'After its first cast the holder refills its charge to full.', None, elixir=1)
I('EXP_SHARE', 'Exp. Share', 'Tool', 'On entry its ATK, DEF and SP.DEF rise to the best base values among your Pokemon still waiting to enter.', None, expshare=1)
I('TERRAIN_EXTENDER', 'Terrain Extender', 'Tool', '3 shield and 1 charge on entry; its cast also gives the next Pokemon 2 shield.', dict(sh=3, ch=1), terrain=1)
I('ARTIFICIAL_GEM_PLACEHOLDER', 'placeholder', 'x', '', None)
del ITEMS['ARTIFICIAL_GEM_PLACEHOLDER']; ORDER.remove('ARTIFICIAL_GEM_PLACEHOLDER')

# ---------------- shiny / rare items ----------------
I('DYNAMAX_BAND', 'Dynamax Band', 'Rare', 'Doubles the holder\'s max HP at the start of the battle.', hpmult=1.0)
I('SHINY_STONE', 'Shiny Stone', 'Rare', 'Holder gains the Light type. +2 AP, +2 shield.', dict(ap=2, sh=2), type='LIGHT')
I('EVIOLITE', 'Eviolite', 'Rare', 'Only a Pokemon that can still evolve can hold this. +6 HP, +1 ATK, +1 AP, +1 DEF, +1 SP.DEF.', dict(hp=6, atk=1, ap=1, df=1, sdf=1), evo_only=1)
I('GOLD_MASK', 'Gold Mask', 'Rare', 'Starts the battle with 3 swarm tokens (each blocks one basic attack).', swarm=3)
I('GOLD_BOTTLE_CAP', 'Gold Bottle Cap', 'Rare', '+30% crit. Its owner gains 1 gold for each KO the holder makes.', dict(crit=30), econ_ko=1)
I('ABSORB_BULB', 'Absorb Bulb', 'Rare', '+2 DEF, +2 SP.DEF. Damage it blocks is stored; the first time it falls to half HP it explodes for the stored amount as special damage.', dict(df=2, sdf=2), bulb=1)
I('SACRED_ASH', 'Sacred Ash', 'Rare', 'The first time the holder would be KO\'d it returns to full HP instead (like Max Revive). Your next Pokemon to enter also gets 4 shield.', revive=2)
I('STAR_PIECE', 'Star Piece', 'Rare', 'Double every damage, SHIELD and healing number of the holder\'s charge power (AP is added afterwards).', starpiece=1)
I('GOLD_BOW', 'Gold Bow', 'Rare', 'The holder does not count toward your lineup size (an extra lineup slot).', slot=1)
I('RED_SCALE', 'Red Scale', 'Rare', 'Its owner earns +1 gold at the start of each round.', econ_income=1)
I('RARE_CANDY', 'Rare Candy', 'Rare', 'Used up when given: the holder permanently gains +2 HP and +1 to every other stat.', dict(hp=2, atk=1, df=1, sdf=1, spd=1, ap=1), perm=1)
I('AMULET_COIN', 'Amulet Coin', 'Rare', 'Its owner gains 1 gold per KO the holder makes; interest cap -1. Not simulated.', econ_ko=1)
I('RUSTED_SWORD', 'Rusted Sword', 'Rare', '+50% base ATK. When the holder faints the sword passes to the next Pokemon.', rusted=1)
I('CELL_BATTERY', 'Cell Battery', 'Rare', 'Each Cell Battery in your lineup gives all your Electric Pokemon +1 speed (max +2). Holder is also supercharged: +2 shield.', dict(sh=2), battery=1)
I('FIRE_SHARD', 'Fire Shard', 'Rare', 'Only for Fire Pokemon. Consumed on use: lose 2 points, the Pokemon permanently gains +1 ATK and +1 speed. Not simulated.', perm_fire=1)
I('CHEF_HAT', "Chef's Hat", 'Rare', 'Holder gets one random Food effect at the start of every battle (not used up).', chef=1)
I('BALL', 'Ball', 'Rare', 'When the holder casts, the next Pokemon enters with 3 extra shield.', ball=1)

# ---------------- berries (reusable: refresh after the battle) ----------------
def B(key, name, text, heal=5, **flags): I(key, name, 'Berry', f'Once per battle, when the holder first drops to half HP or lower: heal {heal}, ' + text, None, berry=heal, **flags)
B('ORAN_BERRY', 'Oran Berry', 'gain 4 shield.', 5, b_shield=4)
B('SITRUS_BERRY', 'Sitrus Berry', 'and healing is 30% stronger after.', 10, b_heal=1)
B('APICOT_BERRY', 'Apicot Berry', 'gain +3 SP.DEF.', 5, b_sdf=3)
B('GANLON_BERRY', 'Ganlon Berry', 'gain +3 DEF.', 5, b_df=3)
B('LIECHI_BERRY', 'Liechi Berry', 'gain +3 ATK.', 5, b_atk=3)
B('SALAC_BERRY', 'Salac Berry', 'gain +4 speed.', 5, b_spd=4)
B('PETAYA_BERRY', 'Petaya Berry', 'gain +3 AP.', 5, b_ap=3)
B('LANSAT_BERRY', 'Lansat Berry', 'gain 50% crit.', 5, b_crit=50)
B('LUM_BERRY', 'Lum Berry', 'clear negative statuses and ignore new ones for 3 turns.', 5, b_cure=1)
B('BABIRI_BERRY', 'Babiri Berry', 'also triggers on being crit; gain protection from the next hit.', 5, b_protect=1)
B('AGUAV_BERRY', 'Aguav Berry', 'heal is 50% of max HP instead, then confused for 1 attack.', 5, b_aguav=1)
B('LEPPA_BERRY', 'Leppa Berry', 'also triggers after the first cast; gain 2 charge.', 5, b_charge=2)
B('JABOCA_BERRY', 'Jaboca Berry', 'gain spiky shield (1 damage back per hit) for 5 turns.', 5, b_spiky=5)
B('ROWAP_BERRY', 'Rowap Berry', 'reflect special damage: 50% of the next hits for 5 turns.', 5, b_reflect=5)
B('CHERI_BERRY', 'Cheri Berry', 'or when paralyzed; gain +2 ATK and immunity to paralysis.', 5, b_atk=2, b_immune='para')
B('CHESTO_BERRY', 'Chesto Berry', 'or when asleep; gain +2 AP and immunity to sleep.', 5, b_ap=2, b_immune='sleep')
B('PECHA_BERRY', 'Pecha Berry', 'or when poisoned; heal is 10 and gain poison immunity.', 10, b_immune='poison')
B('PERSIM_BERRY', 'Persim Berry', 'or when confused; gain +1 SP.DEF and confusion immunity.', 5, b_sdf=1, b_immune='confuse')
B('RAWST_BERRY', 'Rawst Berry', 'or when burned; gain +1 DEF and burn immunity.', 5, b_df=1, b_immune='burn')
B('ASPEAR_BERRY', 'Aspear Berry', 'or when frozen; gain +2 speed and freeze immunity.', 5, b_spd=2, b_immune='freeze')
B('NANAB_BERRY', 'Nanab Berry', 'and its owner gains 1 gold.', 5, econ_gold=1)
B('GOLDEN_RAZZ_BERRY', 'Golden Razz Berry', 'heal 50% of max HP instead; its owner gets a free churn.', 5, b_aguav=2, econ_churn=1)
B('GOLDEN_NANAB_BERRY', 'Golden Nanab Berry', 'heal 50% of max HP instead; its owner gains 2 gold.', 5, b_aguav=2, econ_gold=2)
B('GOLDEN_PINAP_BERRY', 'Golden Pinap Berry', 'heal 50% of max HP instead and gain +1 ATK.', 5, b_aguav=2, b_atk=1)

# ---------------- wands (every attack deals +1 special; one rider each) ----------------
def W(key, name, text, **flags): I(key, name, 'Wand', 'Attacks deal +1 special damage. ' + text, None, wand=1, **flags)
W('BLAST_WAND', 'Blast Wand', 'On a crit the extra damage is +3.', w_crit=2)
W('HP_SWAP_WAND', 'HP Swap Wand', 'Every 4th attack steals 1 max HP from the target.', w_steal=4)
W('SPIRIT_WAND', 'Spirit Wand', 'Extra damage grows by +1 for every 2 casts; every 3rd attack gives +1 charge.', w_spirit=3)
W('LONG_WAND', 'Long Wand', '+20% crit.', w_longcrit=20)
W('CONFUSE_WAND', 'Confuse Wand', 'Every 4th attack confuses the target (halves its next attack) and lowers its SP.DEF by 1.', w_conf=4)
W('PETRIFY_WAND', 'Petrify Wand', 'Every 4th attack flinches the target and lowers its DEF by 1.', w_petrify=4)
W('SLOW_WAND', 'Slow Wand', 'Every 4th attack paralyzes the target for 2 turns.', w_slow=4)
W('SLUMBER_WAND', 'Slumber Wand', 'Every 4th attack puts the target to sleep for 1 turn and lowers its ATK by 1.', w_sleep=4)
W('GUIDING_WAND', 'Guiding Wand', 'Half of the extra damage also splashes on the foe\'s next Pokemon.', w_guide=1)
W('SURROUND_WAND', 'Surround Wand', 'Extra damage is +2 instead.', w_surround=1)
W('POUNCE_WAND', 'Pounce Wand', 'Every 3rd hit taken retaliates for 2 special damage.', w_pounce=3)
W('TWO_EDGED_WAND', 'Two-Edged Wand', 'Extra damage is +3 but the holder takes 1 true damage every 2nd attack.', w_twoedge=1)
W('WARP_WAND', 'Warp Wand', 'Every 4th attack makes the target skip its next turn (flinch).', w_warp=4)
W('SWITCHER_WAND', 'Switcher Wand', 'Every 4th attack removes 1 charge from the target.', w_switch=4)
W('WHIRLWIND_WAND', 'Whirlwind Wand', 'Every 4th attack flinches the target and deals 1 true damage.', w_whirl=4)
W('TUNNEL_WAND', 'Tunnel Wand', 'Every 3rd attack also splashes 2 damage on the foe\'s next Pokemon.', w_tunnel=3)

# ---------------- TMs (replace the holder's charge power) ----------------
I('TM_RAGE', 'TM01 Rage', 'TM', 'Charge power becomes Rage: +1 ATK for each 12% of max HP missing, plus 2 (6 turns), min +4.', tm='RAGE')
I('TM_RETURN', 'TM02 Return', 'TM', 'Charge power becomes Return: strong special damage (2.5x Return), then +3 AP permanently.', tm='RETURN')
I('TM_COUNTER', 'TM03 Counter', 'TM', 'Charge power becomes Counter: special damage equal to 1.5x the holder\'s missing HP (min 4).', tm='COUNTER')
I('TM_DISABLE', 'TM04 Disable', 'TM', 'Charge power becomes Disable: strong special damage (2.5x) and the foe flinches for 2 turns.', tm='DISABLE')
I('TM_BULK_UP', 'TM05 Bulk Up', 'TM', 'Charge power becomes Bulk Up: +100% ATK and +100% DEF (permanent, min +3 ATK and +2 DEF).', tm='BULK_UP')
I('TM_CHARGE', 'TM06 Charge', 'TM', 'Charge power becomes Charge: 1.5x Return damage now, and every later attack deals +2 true damage (stacks).', tm='CHARGE')
I('TM_REFLECT', 'TM07 Reflect', 'TM', 'Charge power becomes Reflect: 5 turns of reflecting 150% of damage taken as special damage.', tm='REFLECT')
I('TM_PAYDAY', 'TM08 Payday', 'TM', 'Charge power becomes Payday: two strong special hits (2.5x); a KO gives its owner 2 gold.', tm='PAYDAY')
I('TM_FOCUS_PUNCH', 'TM09 Focus Punch', 'TM', 'Charge power becomes Focus Punch: a huge special hit that lands after the holder\'s next turn.', tm='FOCUS_PUNCH')
I('TM_HYPER_BEAM', 'TM10 Hyper Beam', 'TM', 'Charge power becomes Hyper Beam: a huge special hit, then the holder is fatigued for 1 turn.', tm='HYPER_BEAM')
I('TM_SUBSTITUTE', 'TM11 Substitute', 'TM', 'Charge power becomes Substitute: gain shield equal to a third of max HP (min 4) and protect from the next hit.', tm='SUBSTITUTE')
I('TM_SKILL_SWAP', 'TM12 Skill Swap', 'TM', 'Charge power becomes a copy of the opponent\'s current charge power, cast immediately, plus 3 shield.', tm='SKILL_SWAP')

# ---------------- weather rocks (whole-lineup effect for the holder\'s side, fixed for the battle) ----------------
def R(key, name, text, **flags): I(key, name, 'Weather rock', 'Whole-lineup effect, active if any Pokemon in your lineup holds it: ' + text, None, rock=1, **flags)
R('SUN_STONE', 'Sun Stone', 'every own turn count 4: heal 1 (each Pokemon).', r_heal=4)
R('HEAT_ROCK', 'Heat Rock', 'all your Pokemon gain +1 ATK; burn damage on them is halved.', r_atk=1)
R('DAMP_ROCK', 'Damp Rock', 'all your Pokemon gain 1 charge every 5th own turn.', r_charge=5)
R('ICY_ROCK', 'Icy Rock', 'every 7th attack of any of your Pokemon freezes the foe for 1 turn.', r_freeze=7)
R('SMOOTH_ROCK', 'Smooth Rock', 'all your Pokemon gain +1 speed every 4th own turn (max +3).', r_speed=4)
R('BLACK_AUGURITE', 'Black Augurite', 'all your Pokemon gain +5% crit and ignore foe crit bonus.', r_crit=5)
R('FLOAT_STONE', 'Float Stone', 'all your Pokemon gain +1 speed.', r_spd=1)
R('ELECTRIC_QUARTZ', 'Electric Quartz', 'all your Pokemon enter with 3 shield.', r_shield=3)
R('MIST_STONE', 'Mist Stone', 'all your Pokemon gain +1 SP.DEF.', r_sdf=1)
R('BLOOD_STONE', 'Blood Stone', 'your attacks heal 1 HP when the target is wounded.', r_blood=1)
R('SMELLY_CLAY', 'Smelly Clay', 'poison damage on your Pokemon is reduced by 1.', r_clay=1)
R('ODD_KEYSTONE', 'Odd Keystone', 'negative statuses on your Pokemon last 1 turn less (min 1).', r_odd=1)

# ---------------- gems: +1 to a synergy count (holder does not gain the type) ----------------
GEM_TYPES = ['NORMAL', 'GRASS', 'FIRE', 'WATER', 'ELECTRIC', 'FIGHTING', 'PSYCHIC', 'DARK', 'STEEL', 'GROUND', 'POISON', 'DRAGON', 'FIELD', 'MONSTER', 'HUMAN', 'AQUATIC', 'BUG', 'FLYING', 'FLORA', 'ROCK', 'GHOST', 'FAIRY', 'ICE', 'FOSSIL', 'SOUND', 'ARTIFICIAL', 'LIGHT', 'WILD', 'AMORPHOUS', 'GOURMET']
for t in GEM_TYPES:
    I(t + '_GEM', t.title() + ' Gem', 'Gem', f'Counts as one extra {t.title()} Pokemon for your {t.title()} synergy. The holder does not gain the type.', None, gem=t)

# ---------------- food: used up after one battle ----------------
def F(key, name, text, stats=None, **flags): I(key, name, 'Food', text + ' Used up after the battle.', stats, food=1, **flags)
F('RAGE_CANDY_BAR', 'Rage Candy Bar', '+2 ATK for the battle.', dict(atk=2))
F('TEA', 'Tea', 'Starts the battle with 1 charge.', dict(ch=1))
F('CURRY', 'Curry', '+2 ATK for the holder\'s first 3 turns.', None, curry=1)
F('ROCK_SALT', 'Rock Salt', '20% max HP as shield (min 2) and immune to negative statuses for 3 turns.', dict(sh=2), abshield=1)
F('POFFIN', 'Poffin', '5 shield, and any berry it holds is eaten immediately (its heal becomes shield).', dict(sh=5), poffin=1)
F('CASTELIACONE', 'Casteliacone', 'The first attack freezes the foe for 1 turn.', None, first_status='freeze')
F('WHIPPED_DREAM', 'Whipped Dream', 'The first attack charms the foe for 2 turns.', None, first_status='charm')
F('TART_APPLE', 'Tart Apple', 'Each attack lowers the target\'s DEF by 1 (max -2).', None, shred='df')
F('SWEET_APPLE', 'Sweet Apple', 'Each attack lowers the target\'s SP.DEF by 1 (max -2).', None, shred='sdf')
F('SIRUPY_APPLE', 'Syrupy Apple', 'Every 3rd attack paralyzes the target for 1 turn.', None, parat=3)
F('FRUIT_JUICE', 'Fruit Juice', '+3 speed.', dict(spd=3))
F('NUTRITIOUS_EGG', 'Nutritious Egg', '+50% base ATK, DEF and SP.DEF (rounded up).', None, egg=1)
F('LEEK', 'Leek', '+50% crit.', dict(crit=50))
F('LARGE_LEEK', 'Large Leek', '+100% crit (every attack crits).', dict(crit=100))
F('OLIVE_OIL', 'Olive Oil', 'Dodges every 5th incoming attack.', None, dodge=5)
F('BERRY_JUICE', 'Berry Juice', '5 shield, and 5 more whenever the holder\'s berry is eaten.', dict(sh=5), juice=1)
F('HEARTY_STEW', 'Hearty Stew', '+30% max HP.', None, hpmult=0.3)
F('BIG_MUSHROOM', 'Big Mushroom', '+30% max HP.', None, hpmult=0.3)
F('TINY_MUSHROOM', 'Tiny Mushroom', '+3 speed, -30% max HP.', dict(spd=3), hpmult=-0.3)
F('BALM_MUSHROOM', 'Balm Mushroom', '+2 speed, heals 1 HP every 2nd own turn and immune to negative statuses for 3 turns.', dict(spd=2), abshield=1, greenorb=1)
F('LUCKY_EGG', 'Lucky Egg', '+1 AP and +10% crit.', dict(ap=1, crit=10))
F('BINDING_MOCHI', 'Binding Mochi', 'The first attack flinches the foe for 2 turns.', None, first_status='flinch2')
F('HERBA_MYSTICA_SALTY', 'Herba Mystica (Salty)', 'Immune to negative statuses for the battle.', None, immune_neg=1)

# ---------------- sweets & milk: permanent upgrade, consumed on use ----------------
def P(key, name, text, stats): I(key, name, 'Permanent', text + ' Permanent; used up when given.', stats, perm=1)
P('STRAWBERRY_SWEET', 'Strawberry Sweet', '+1 ATK.', dict(atk=1))
P('LOVE_SWEET', 'Love Sweet', '+1 DEF.', dict(df=1))
P('RIBBON_SWEET', 'Ribbon Sweet', '+1 SP.DEF.', dict(sdf=1))
P('BERRY_SWEET', 'Berry Sweet', '+2 HP.', dict(hp=2))
P('FLOWER_SWEET', 'Flower Sweet', '+1 speed.', dict(spd=1))
P('STAR_SWEET', 'Star Sweet', '+1 AP.', dict(ap=1))
P('MOOMOO_MILK', 'Moomoo Milk', '+2 HP.', dict(hp=2))
P('SMOKED_FILET', 'Smoked Fillet', '-1 HP, +1 ATK and +1 AP.', dict(hp=-1, atk=1, ap=1))

EXCLUDED = [
    ('Fishing rods (Old/Good/Super Rod)', 'Catch extra Pokemon between rounds; no bench or fishing here.'),
    ('Gifts, bundles, boxes, tickets (Exchange/Recycle/Dojo/Mission/Regional), Wanted Notice, Leader\'s Crest, Potion, Gimmighoul Coin, nuggets/coins', 'Pure PAC economy and meta features.'),
    ('Instruments (Aqua Monica, Fiery Drum, Grass Cornet, Icy Flute, Rock Horn, Sky Melodica, Terra Cymbal, Soothe Bell)', 'Bias the PAC random shop; our shop is a shared, fixed singleton row.'),
    ('Rare Candy', 'Evolution item; no evolution here.'),
    ('Mulches, flower pot, nectars, berry trees, mushrooms (the plain Mushrooms/Rice/Berries/Honey/Leftovers/Sandwich/Spinda Cocktail/Black Sludge/Herba Mystica flavors)', 'Garden/town subsystems or random effects.'),
    ('Ogerpon masks, Comfey, Tatsugiri forms, Zygarde Cube, Meteorite, Auspicious/Malicious Armor, scrolls, Rotom Catalog, Mystery Box, Memory Discs, Lapras Passport', 'Tied to one species or form; handle with the cards of those Pokemon.'),
    ('Sweets/flavors for Alcremie', 'Species specific.'),
]


# ---- crit tokens: old crit % -> tokens gained per attack (5 tokens = one crit; 1 token = 20%), in halves
def qh(p):
    v = round(p / 10) / 2
    return 0.5 if v < 1 else float(int(v))   # whole tokens only (half only below 1)
for _it in ITEMS.values():
    if 'crit' in _it['stats']: _it['stats']['crit'] = qh(_it['stats']['crit'])
    for _k in ('b_crit', 'r_crit', 'w_longcrit'):
        if _k in _it['flags']: _it['flags'][_k] = qh(_it['flags'][_k])


# ---- Unholdable items (as in PAC: gems and Red Scale are not held by a Pokemon) ----
for _k, _it in ITEMS.items():
    if _it['cat'] == 'Gem':
        _t = _it['flags']['gem'].title()
        _it['flags']['unholdable'] = 1
        _it['text'] = f'UNHOLDABLE. Counts as one extra {_t} Pokemon for your {_t} synergy.'
    elif _k == 'RED_SCALE':
        _it['flags']['unholdable'] = 1
        _it['text'] = 'UNHOLDABLE. You earn +1 gold at the start of each round.'
