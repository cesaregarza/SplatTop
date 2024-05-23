import os

import boto3
import requests
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)
from utils.constants import BUCKET_NAME


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


def upload_file_to_bucket(client: boto3.client, key: str, data: bytes):
    try:
        client.put_object(
            ACL="public-read", Bucket=BUCKET_NAME, Key=key, Body=data
        )
    except ClientError as e:
        print(f"Error uploading file to bucket: {e}")
        raise


def get_existing_file_names(client: boto3.client, key: str) -> list[str]:
    try:
        response = client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=key)
        return [obj["Key"] for obj in response.get("Contents", [])]
    except ClientError as e:
        print(f"Error listing objects: {e}")
        return []
