import os

import boto3
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

BUCKET_NAME = "assets"
WEAPON_PATH = "images/weapon_flat"
BADGE_PATH = "images/badge"
BANNER_PATH = "images/npl"

WEAPON_KEY = "weapon_flat"
BADGE_KEY = "badge"
BANNER_KEY = "npl"


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
            Bucket=BUCKET_NAME, Key="latest_stored_version"
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
        client.put_object(Bucket=BUCKET_NAME, Key=key, Body=data)
    except ClientError as e:
        print(f"Error uploading file to bucket: {e}")
        raise


def update_version_file(client: boto3.client, latest_version: str):
    try:
        client.put_object(
            Bucket=BUCKET_NAME,
            Key="latest_stored_version",
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
                if file["name"] not in existing_files:
                    data = download_file_from_repo(file)
                    upload_file_to_bucket(client, f"{key}/{file['name']}", data)

        overwrite_xref_files(client, latest_version)

        update_version_file(client, latest_version)
        print("Assets updated.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
