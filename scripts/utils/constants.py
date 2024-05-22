# Repository and API URLs
REPO_PATH = "Leanny/splat3"
API_URL = f"https://api.github.com/repos/{REPO_PATH}"
DATAMINE_RAW_URL = f"https://raw.githubusercontent.com/{REPO_PATH}/main"

# Cross-reference URLs for various data types
BASE_XREF_URL = f"{DATAMINE_RAW_URL}/data/mush/%s"
WEAPON_ID_XREF = f"{BASE_XREF_URL}/WeaponInfoMain.json"
BADGE_ID_XREF = f"{BASE_XREF_URL}/BadgeInfo.json"
BANNER_ID_XREF = f"{BASE_XREF_URL}/NamePlateBgInfo.json"
LANGUAGE_BASE_URL = f"{DATAMINE_RAW_URL}/data/language/%s.json"

# S3 bucket and asset paths
BUCKET_NAME = "splat-top"
ASSETS_PATH = "assets"
WEAPON_PATH = "images/weapon_flat"
BADGE_PATH = "images/badge"
BANNER_PATH = "images/npl"
DATA_PATH = "data"
LANGUAGE_PATH = f"{DATA_PATH}/language"

# S3 keys for assets
WEAPON_KEY = f"{ASSETS_PATH}/weapon_flat"
BADGE_KEY = f"{ASSETS_PATH}/badge"
BANNER_KEY = f"{ASSETS_PATH}/npl"

# Weapon kit cross-reference mapping
# Weapons like the Hero Shot, Octoshot, and Order replicas will end with
# "H", "Oct", and "O" respectively. This dictionary maps those to the
# appropriate reference kit number.
KIT_XREF = {"H": "00", "O": "00", "Oct": "01"}
