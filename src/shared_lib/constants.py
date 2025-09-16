BASE_CDN_URL = "https://splat-top.nyc3.cdn.digitaloceanspaces.com/"
MODES = [
    "Splat Zones",
    "Tower Control",
    "Rainmaker",
    "Clam Blitz",
]
MODES_SNAKE_CASE = {
    "Splat Zones": "splat_zones",
    "Tower Control": "tower_control",
    "Rainmaker": "rainmaker",
    "Clam Blitz": "clam_blitz",
}
REGIONS = [
    "Tentatek",
    "Takoroka",
]
REDIS_PORT = 6379
REDIS_HOST = "redis"
REDIS_URI = f"redis://{REDIS_HOST}:{REDIS_PORT}"
PLAYER_PUBSUB_CHANNEL = "player_data_channel"
PLAYER_LATEST_REDIS_KEY = "player_latest_data"
PLAYER_DATA_REDIS_KEY = "player_data"
WEAPON_INFO_URL = (
    "https://splat-top.nyc3.cdn.digitaloceanspaces.com/data/weapon_info.json"
)
WEAPON_INFO_REDIS_KEY = "weapon_info"
GAME_TRANSLATION_BASE_URL = (
    "https://splat-top.nyc3.digitaloceanspaces.com/data/language/%s.json"
)
LANGUAGES = [
    "USen",
    "USes",
    "JPja",
    "EUfr",
    "EUde",
    "CNzh",
]
GAME_TRANSLATION_REDIS_KEY = "weapon_translations"
ALIASES_REDIS_KEY = "player_aliases"
AUTOMATON_IS_VALID_REDIS_KEY = "automaton_is_valid"
SKILL_OFFSET_REDIS_KEY = "skill_offset"
GINI_COEFF_REDIS_KEY = "gini_coeff"
LORENZ_CURVE_REDIS_KEY = "gini_coeff_data"
WEAPON_LEADERBOARD_PEAK_REDIS_KEY = "weapon_leaderboard_peak"
SEASON_RESULTS_REDIS_KEY = "season_results"

# API token management (Redis keys)
API_TOKENS_ACTIVE_SET = "api:tokens:active"
API_TOKEN_HASH_MAP_PREFIX = "api:token:hash:"
API_TOKEN_META_PREFIX = "api:token:meta:"
API_TOKEN_IDS_SET = "api:tokens:ids"
API_USAGE_QUEUE_KEY = "api:usage:queue"
API_USAGE_PROCESSING_KEY = "api:usage:queue:processing"
API_USAGE_LOCK_KEY = "api:usage:flush:lock"
API_TOKEN_PREFIX = "rpl"
MAIN_ONLY_ABILITIES = [
    "comeback",
    "last_ditch_effort",
    "opening_gambit",
    "tenacity",
    "ability_doubler",
    "haunt",
    "ninja_squid",
    "respawn_punisher",
    "thermal_ink",
    "drop_roller",
    "object_shredder",
    "stealth_jump",
]
STANDARD_ABILITIES = [
    "ink_recovery_up",
    "ink_resistance_up",
    "ink_saver_main",
    "ink_saver_sub",
    "intensify_action",
    "quick_respawn",
    "quick_super_jump",
    "run_speed_up",
    "special_charge_up",
    "special_power_up",
    "special_saver",
    "sub_power_up",
    "sub_resistance_up",
    "swim_speed_up",
]
BUCKET_THRESHOLDS = [3, 6, 12, 15, 21, 29, 38, 51, 57]
