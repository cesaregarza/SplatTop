import os

import boto3
import orjson
import requests
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)
from tqdm import tqdm

REPO_PATH = "Leanny/splat3"
API_URL = f"https://api.github.com/repos/{REPO_PATH}"
RAW_URL = f"https://raw.githubusercontent.com/{REPO_PATH}/main"

BASE_XREF_URL = f"{RAW_URL}/data/mush/%s"
WEAPON_ID_XREF = f"{BASE_XREF_URL}/WeaponInfoMain.json"
BADGE_ID_XREF = f"{BASE_XREF_URL}/BadgeInfo.json"
BANNER_ID_XREF = f"{BASE_XREF_URL}/NamePlateBgInfo.json"
LANGUAGE_BASE_URL = f"{RAW_URL}/data/language/%s.json"

SUPPORTED_LANGUAGES = [
    "USen",
    "USes",
    "JPja",
    "EUfr",
    "EUde",
]

BUCKET_NAME = "splat-top"
ASSETS_PATH = "assets"
WEAPON_PATH = "images/weapon_flat"
BADGE_PATH = "images/badge"
BANNER_PATH = "images/npl"
DATA_PATH = "data"
LANGUAGE_PATH = f"{DATA_PATH}/language"

WEAPON_KEY = f"{ASSETS_PATH}/weapon_flat"
BADGE_KEY = f"{ASSETS_PATH}/badge"
BANNER_KEY = f"{ASSETS_PATH}/npl"


KIT_XREF = {"H": "00", "O": "00", "Oct": "01"}


def get_latest_version() -> str:
    TARGET_URL = "data/mush/latest"
    response = requests.get(f"{RAW_URL}/{TARGET_URL}")
    response.raise_for_status()
    return response.text.strip()


def get_boto3_session() -> boto3.Session:
    try:
        return boto3.Session(
            aws_access_key_id=os.getenv("DO_SPACES_KEY"),
            aws_secret_access_key=os.getenv("DO_SPACES_SECRET"),
            region_name=os.getenv("DO_SPACES_REGION"),
        )
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Error in creating boto3 session: {e}")
        raise


def get_boto3_client(session: boto3.Session) -> boto3.client:
    try:
        return session.client(
            "s3",
            endpoint_url=os.getenv("DO_SPACES_ENDPOINT"),
        )
    except NoCredentialsError as e:
        print(f"Error in creating boto3 client: {e}")
        raise


def check_if_needs_update(client: boto3.client, latest_version: str) -> bool:
    try:
        response = client.get_object(
            Bucket=BUCKET_NAME,
            Key=ASSETS_PATH + "/latest_stored_version",
        )
        current_version = response["Body"].read().decode("utf-8").strip()
        return current_version != latest_version
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return True
        else:
            raise


def list_files_in_repo(subpath: str) -> list[str]:
    TARGET_URL = f"{API_URL}/contents/{subpath}"
    response = requests.get(TARGET_URL).json()
    # Throw out all non-png files
    return [file for file in response if file["name"].endswith(".png")]


def get_existing_file_names(client: boto3.client, key: str) -> list[str]:
    try:
        response = client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=key)
        return [obj["Key"] for obj in response.get("Contents", [])]
    except ClientError as e:
        print(f"Error listing objects: {e}")
        return []


def download_file_from_repo(file: dict) -> bytes:
    response = requests.get(file["download_url"])
    response.raise_for_status()
    return response.content


def upload_file_to_bucket(client: boto3.client, key: str, data: bytes):
    try:
        client.put_object(
            ACL="public-read", Bucket=BUCKET_NAME, Key=key, Body=data
        )
    except ClientError as e:
        print(f"Error uploading file to bucket: {e}")
        raise


def update_version_file(client: boto3.client, latest_version: str):
    try:
        client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{ASSETS_PATH}/latest_stored_version",
            Body=latest_version,
            ACL="public-read",
        )
    except ClientError as e:
        print(f"Error updating version file: {e}")
        raise


def overwrite_xref_files(client: boto3.client, latest_version: str):
    xref_urls = [
        WEAPON_ID_XREF % latest_version,
        BADGE_ID_XREF % latest_version,
        BANNER_ID_XREF % latest_version,
    ]
    xref_keys = [
        f"{WEAPON_KEY}/WeaponInfoMain.json",
        f"{BADGE_KEY}/BadgeInfo.json",
        f"{BANNER_KEY}/NamePlateBgInfo.json",
    ]
    for url, key in zip(xref_urls, xref_keys):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.content
            upload_file_to_bucket(client, key, data)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading xref file from {url}: {e}")
        except ClientError as e:
            print(f"Error uploading xref file to bucket: {e}")


def update_data(client: boto3.client):
    WEAPON_DATA_PATH = "assets/weapon_flat/WeaponInfoMain.json"
    DESTINATION_PATH = "data/weapon_info.json"
    try:
        response = client.get_object(Bucket=BUCKET_NAME, Key=WEAPON_DATA_PATH)
        data = orjson.loads(response["Body"].read())
        data = parse_weapon_data(data)
        data_string = orjson.dumps({str(k): v for k, v in data.items()})
        client.put_object(
            ACL="public-read",
            Bucket=BUCKET_NAME,
            Key=DESTINATION_PATH,
            Body=data_string,
        )
    except ClientError as e:
        print(f"Error updating data: {e}")
        raise


def parse_weapon_data(data: list[dict]) -> dict:
    data = [x for x in data if x["Type"] == "Versus"]
    KEYS_TO_KEEP = [
        "Season",
        "__RowId",
        "SpecialWeapon",
        "SubWeapon",
        "SpecialPoint",
    ]
    preprocessed_data = {x["Id"]: {k: x[k] for k in KEYS_TO_KEEP} for x in data}
    return process_weapon_data(preprocessed_data)


def extract_sub_special(raw_subspecial: str) -> str:
    return raw_subspecial[len("Work/Gyml/") :].split(".spl")[0]


def process_rowid(row_id: str) -> dict[str, str]:
    weapon_class = row_id.split("_")[0]
    weapon_main = row_id.split("_")[1]
    weapon_suffix = row_id.split("_")[-1]

    if weapon_suffix in KIT_XREF:
        weapon_reference_suffix = KIT_XREF[weapon_suffix]
    else:
        weapon_reference_suffix = weapon_suffix

    return {
        "class": weapon_class,
        "kit": weapon_main + weapon_suffix,
        "reference_kit": weapon_main + weapon_reference_suffix,
    }


def process_weapon_data(preprocessed_data: dict[int, dict]) -> dict[int, dict]:
    out = {}
    for key, value in preprocessed_data.items():
        row_id = value["__RowId"]
        out[key] = {
            "season": value["Season"],
            "sub": extract_sub_special(value["SubWeapon"]),
            "special": extract_sub_special(value["SpecialWeapon"]),
            **process_rowid(row_id),
        }
    return out

def pull_language_data(client: boto3.client, language: str):
    BASE_KEY = "CommonMsg/Weapon/%s"
    KEYS = [
        "WeaponName_Main",
        "WeaponName_Sub",
        "WeaponName_Special",
    ]
    response = requests.get(LANGUAGE_BASE_URL % language)
    data = orjson.loads(response.text)
    data = {k: data[BASE_KEY % k] for k in KEYS}
    client.put_object(
        ACL="public-read",
        Bucket=BUCKET_NAME,
        Key=f"{LANGUAGE_PATH}/{language}.json",
        Body=orjson.dumps(data),
    )

def pull_all_language_data(client: boto3.client):
    for language in SUPPORTED_LANGUAGES:
        pull_language_data(client, language)


def main():
    try:
        session = get_boto3_session()
        client = get_boto3_client(session)

        latest_version = get_latest_version()
        if not check_if_needs_update(client, latest_version):
            print("No update needed.")
            return

        print("Updating assets...")

        for key, path in zip(
            [WEAPON_KEY, BADGE_KEY, BANNER_KEY],
            [WEAPON_PATH, BADGE_PATH, BANNER_PATH],
        ):
            existing_files = get_existing_file_names(client, key)
            new_files = list_files_in_repo(path)
            for file in tqdm(new_files, desc=f"Updating {key}"):
                if f"{key}/{file['name']}" not in existing_files:
                    data = download_file_from_repo(file)
                    upload_file_to_bucket(client, f"{key}/{file['name']}", data)

        overwrite_xref_files(client, latest_version)

        update_version_file(client, latest_version)
        print("Assets updated.")
        print("Updating data...")
        update_data(client)
        pull_all_language_data(client)
        print("Data updated.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
