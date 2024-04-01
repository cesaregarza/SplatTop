import os

import boto3
import requests
from botocore.client import BaseClient

REPO_PATH = "Leanny/splat3"
API_URL = f"https://api.github.com/repos/{REPO_PATH}"
RAW_URL = f"https://raw.githubusercontent.com/{REPO_PATH}/main"

BUCKET_NAME = "assets"
WEAPON_PATH = "images/weapon_flat"
BADGE_PATH = "images/badge"
BANNER_PATH = "images/npl"


def get_latest_version() -> str:
    TARGET_URL = "data/mush/latest"
    response = requests.get(f"{RAW_URL}/{TARGET_URL}")
    response.raise_for_status()
    return response.text.strip()


def get_boto3_session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.getenv("DO_SPACES_KEY"),
        aws_secret_access_key=os.getenv("DO_SPACES_SECRET"),
        region_name=os.getenv("DO_SPACES_REGION"),
    )


def get_boto3_client(session: boto3.Session) -> BaseClient:
    return session.client(
        "s3",
        endpoint_url=os.getenv("DO_SPACES_ENDPOINT"),
    )


def check_if_needs_update(client: BaseClient, latest_version: str) -> bool:
    try:
        response = client.get_object(
            Bucket=BUCKET_NAME, Key="latest_stored_version"
        )
        current_version = response["Body"].read().decode("utf-8").strip()
        return current_version != latest_version
    except client.exceptions.NoSuchKey:
        return True


def list_files_in_repo(subpath: str) -> list[str]:
    TARGET_URL = f"{API_URL}/contents/{subpath}"
    response = requests.get(TARGET_URL).json()
    # Throw out all non-png files
    return [file["name"] for file in response if file["name"].endswith(".png")]
