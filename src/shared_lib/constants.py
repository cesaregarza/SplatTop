MODES = [
    "Splat Zones",
    "Tower Control",
    "Rainmaker",
    "Clam Blitz",
]
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
]
GAME_TRANSLATION_REDIS_KEY = "weapon_translations"
ALIASES_REDIS_KEY = "player_aliases"
AUTOMATON_IS_VALID_REDIS_KEY = "automaton_is_valid"

WEAPON_LEADERBOARD_FLOOR = 5
WEAPON_LEADERBOARD_THRESHOLD = 0.6
WEAPON_LEADERBOARD_REDIS_KEY = "weapon_leaderboard"