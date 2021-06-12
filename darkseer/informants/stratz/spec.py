from glom import glom, S, T, Coalesce, SKIP, Assign, Spec, Flatten, Invoke


PATCH_SPEC = {
    'patch_id': 'id',
    'patch': 'name',
    'release_datetime': 'asOfDateTime'
}

HERO_SPEC = {
    'hero_id': 'id',
    'patch_id': 'gameVersionId',
    'hero_internal_name': 'shortName',
    'hero_display_name': 'displayName',
    'primary_attribute': 'parse_stats.primaryAttribute',
    'mana_regen_base': 'parse_stats.mpRegen',
    'strength_base': 'parse_stats.strengthBase',
    'strength_gain': 'parse_stats.strengthGain',
    'agility_base': 'parse_stats.agilityBase',
    'agility_gain': 'parse_stats.agilityGain',
    'intelligence_base': 'parse_stats.intelligenceBase',
    'intelligence_gain': 'parse_stats.intelligenceGain',
    'base_attack_time': 'parse_stats.attackRate',
    'attack_point': 'parse_stats.attackAnimationPoint',
    'attack_range': 'parse_stats.attackType',
    'attack_type': 'parse_stats.attackRange',
    'is_captains_mode': 'parse_stats.cMEnabled',
    'movespeed': 'parse_stats.moveSpeed',
    'turn_rate': 'parse_stats.moveTurnRate',
    'armor_base': 'parse_stats.startingArmor',
    'magic_armor_base': 'parse_stats.startingMagicArmor',
    'damage_base_max': 'parse_stats.startingDamageMax',
    'damage_base_min': 'parse_stats.startingDamageMin',
    'faction': 'parse_stats.team',
    'vision_range_day': 'parse_stats.visionDaytimeRange',
    'vision_range_night': 'parse_stats.visionNighttimeRange'
}

ITEM_SPEC = {
    'item_id': 'id',
    'patch_id': S.patch_id,
    'item_internal_name': 'shortName',
    'item_display_name': 'displayName',
    'cost': 'parse_stats.cost',
    'is_recipe': 'parse_stats.isRecipe',
    'is_side_shop': 'parse_stats.isSideShop',
    'quality': 'parse_stats.quality',
    'unit_target_flags': 'parse_stats.unitTargetFlags',
    'unit_target_team': 'parse_stats.unitTargetTeam',
    'unit_target_type': 'parse_stats.unitTargetType'
}

NPC_SPEC = {
    'npc_id': 'id',
    'patch_id': S.patch_id,
    'npc_internal_name': 'name',
    'combat_class_attack': 'parse_stats.combatClassAttack',
    'combat_class_defend': 'parse_stats.combatClassDefend',
    'is_ancient': 'parse_stats.isAncient',
    'is_neutral': 'parse_stats.isNeutralUnitType',
    'health': 'parse_stats.statusHealth',
    'mana': 'parse_stats.statusMana',
    'faction': 'parse_stats.teamName',
    'unit_relationship_class': 'parse_stats.unitRelationshipClass'
}

ABILITY_SPEC = {
    'ability_id': 'id',
    'patch_id': S.patch_id,
    'ability_internal_name': 'name',
    'ability_display_name': 'parse_language.displayName',
    'is_talent': 'isTalent',
    'is_ultimate': 'parse_stats.hasScepterUpgrade',
    'has_scepter_upgrade': 'parse_stats.isGrantedByScepter',
    'is_scepter_upgrade': 'parse_stats.isGrantedByShard',
    'is_aghanims_shard': 'parse_stats.isUltimate',
    'required_level': 'parse_stats.requiredLevel',
    'ability_type': 'parse_stats.type',
    'ability_damage_type': 'parse_stats.unitDamageType',
    'unit_target_flags': 'parse_stats.unitTargetFlags',
    'unit_target_team': 'parse_stats.unitTargetTeam',
    'unit_target_type': 'parse_stats.unitTargetType',
}

TEAM_SPEC = {
    'team_id': 'id',
    'team_name': 'name',
    'team_tag': 'tag',
    'country_code': 'countryCode',
    'created': 'dateCreated'
}

TOURNAMENT_SPEC = {
    'league_id': 'id',
    'league_name': 'displayName',
    'league_start_date': 'startDateTime',
    'league_end_date': 'endDateTime',
    'tier': 'tier',
    'prize_pool': 'prizePool'
}


MATCH_SPEC = {
    'match_id': 'id',
    'replay_salt': 'replaySalt',
    'patch_id': 'gameVersionId',
    'league_id': 'leagueId',
    'series_id': 'seriesId',
    'radiant_team_id': 'radiantTeamId',
    'dire_team_id': 'direTeamId',
    'start_datetime': 'startDateTime',
    'is_stats': 'isStats',
    'winning_faction': 'didRadiantWin',
    'duration': 'durationSeconds',
    'region': 'regionId',
    'lobby_type': 'lobbyType',
    'game_mode': 'gameMode',
    'tournament': ('parse_league', Coalesce(TOURNAMENT_SPEC, default=None)),
    'teams': ('parse_teams', [Coalesce(TEAM_SPEC, default=SKIP)]),
    'accounts': (
        'parse_accounts',
        [(
            'acct',
            {
                'steam_id': 'id',
                'steam_name': Coalesce('proSteamAccount.name', 'name')
            }
        )]
    ),
    'players': (
        'parse_match_players',
        [{
            'match_id': S.match_id,
            'hero_id': 'heroId',
            'steam_id': 'steamAccountId',
            'slot': 'playerSlot',
            'party_id': 'partyId',
            'is_leaver': 'leaverStatus'
        }]
    ),
    'hero_movements': (
        'parse_hero_movements',
        [(
            S(hero_id='heroId'),
            'playbackData.playerUpdatePositionEvents',
            [{
                'match_id': S.match_id,
                'hero_id': S.hero_id,
                'time': 'time',
                'x': 'x',
                'y': 'y'
            }],
            Invoke(enumerate).specs(T),
            [lambda e: {**e[1], 'id': e[0]}]
        )],
        Flatten()
    )
}
