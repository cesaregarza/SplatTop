from __future__ import annotations

from typing import TYPE_CHECKING

import orjson
import requests
from botocore.exceptions import ClientError
from tqdm import tqdm
from utils.constants import (
    ASSETS_PATH,
    BADGE_ID_XREF,
    BADGE_KEY,
    BADGE_PATH,
    BANNER_ID_XREF,
    BANNER_KEY,
    BANNER_PATH,
    BUCKET_NAME,
    DATAMINE_RAW_URL,
    KIT_XREF,
    WEAPON_ID_XREF,
    WEAPON_KEY,
    WEAPON_PATH,
)
from utils.datamine import (
    download_file_from_repo,
    list_images_in_repo,
    pull_language_data,
)
from utils.languages import get_supported_languages
from utils.spaces import (
    get_boto3_client,
    get_boto3_session,
    get_existing_file_names,
    upload_file_to_bucket,
)

if TYPE_CHECKING:
    import boto3


def get_latest_version() -> str:
    TARGET_URL = "data/mush/latest"
    response = requests.get(f"{DATAMINE_RAW_URL}/{TARGET_URL}")
    response.raise_for_status()
    return response.text.strip()


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


def update_version_file(client: boto3.client, latest_version: str) -> None:
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


def overwrite_xref_files(client: boto3.client, latest_version: str) -> None:
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


def update_data(client: boto3.client) -> None:
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
        "kit": f"{weapon_main}_{weapon_suffix}",
        "reference_kit": f"{weapon_main}_{weapon_reference_suffix}",
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
    # Find the reverse mapping for each weapon and add it
    reverse_map = {v["reference_kit"]: k for k, v in out.items()}
    for _, weapon_data in out.items():
        weapon_data["reference_id"] = reverse_map[weapon_data["reference_kit"]]
    return out


def pull_all_language_data(client: boto3.client) -> None:
    for language in get_supported_languages():
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
            new_files = list_images_in_repo(path)
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
