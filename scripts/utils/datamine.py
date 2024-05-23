import boto3
import orjson
import requests
from utils.constants import (
    API_URL,
    BUCKET_NAME,
    LANGUAGE_BASE_URL,
    LANGUAGE_PATH,
)


def list_images_in_repo(subpath: str) -> list[str]:
    TARGET_URL = f"{API_URL}/contents/{subpath}"
    response = requests.get(TARGET_URL)
    response_json = orjson.loads(response.text)
    # Throw out all non-png files
    return [file for file in response_json if file["name"].endswith(".png")]


def download_file_from_repo(file: dict) -> bytes:
    response = requests.get(file["download_url"])
    response.raise_for_status()
    return response.content


def pull_language_data(client: boto3.client, language: str):
    BASE_KEY = "CommonMsg/Weapon/%s"
    KEYS = [
        "WeaponName_Main",
        "WeaponName_Sub",
        "WeaponName_Special",
        "WeaponTypeName",
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
