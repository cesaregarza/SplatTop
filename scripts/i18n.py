from __future__ import annotations

import glob
import os
import re
from typing import TYPE_CHECKING

import orjson
from utils.constants import LANGUAGE_PATH
from utils.datamine import pull_language_data
from utils.languages import get_supported_languages, write_supported_languages
from utils.spaces import (
    get_boto3_client,
    get_boto3_session,
    get_existing_file_names,
)

if TYPE_CHECKING:
    import boto3

# Constants
REFERENCE_FILE = "i18n/USen.json"
REACT_BASE_DIR = "src/react_app/"
REACT_SRC_DIR = os.path.join(REACT_BASE_DIR, "src")
REACT_LOCALES_DIR = os.path.join(REACT_BASE_DIR, "public/locales/")
REACT_SUPPLANG_FILE = os.path.join(
    REACT_SRC_DIR, "components/supported_languages.js"
)
REACT_I18N_FILE = os.path.join(REACT_SRC_DIR, "i18n.js")


def get_i18n_data(client: boto3.client) -> tuple[dict, dict]:
    lang_files = glob.glob("i18n/*.json")

    # Make English the first language
    lang_files.remove(REFERENCE_FILE)
    lang_files.insert(0, REFERENCE_FILE)

    existing_file_names = [
        x.split("/")[-1] for x in get_existing_file_names(client, LANGUAGE_PATH)
    ]

    lang_data = {}
    lang_metadata = {}
    for lang_file in lang_files:
        data: dict = orjson.loads(open(lang_file, "rb").read())
        metadata = data.pop("metadata")
        key = metadata["key"]
        splatoon_language_key = metadata["splatoonLanguageKey"]
        lang_data[key] = data
        lang_metadata[key] = metadata

        # If the language file isn't already in the bucket, download from the
        # datamine and upload it to the bucket
        if f"{splatoon_language_key}.json" not in existing_file_names:
            pull_language_data(client, splatoon_language_key)
        else:
            print(f"{splatoon_language_key}.json already exists in bucket")

    return lang_data, lang_metadata


def align_lists(
    reference_list: list[dict], target_list: list[dict]
) -> list[dict]:
    target_dict = {item["key"]: item for item in target_list}

    aligned_target = []
    for ref_item in reference_list:
        key = ref_item["key"]
        if key in target_dict:
            aligned_target.append(target_dict[key])
        else:
            aligned_target.append(ref_item)

    return aligned_target


def update_dict_with_new_keys(reference_dict: dict, target_dict: dict) -> dict:
    for key in reference_dict:
        if key not in target_dict:
            print(f"Adding new key: {key}")
            target_dict[key] = reference_dict[key]
            continue
        refval = reference_dict[key]
        if isinstance(refval, dict):
            print(f"Updating nested dictionary for key: {key}")
            target_dict[key] = update_dict_with_new_keys(
                refval, target_dict[key]
            )
        elif isinstance(refval, list):
            print(f"Aligning lists for key: {key}")
            target_dict[key] = align_lists(refval, target_dict[key])
    return target_dict


def save_updated_languages(language_data: dict, lang_metadata: dict) -> None:
    reference_data = language_data["USen"]

    for lang_key, lang_specific_data in language_data.items():
        if lang_key == "USen":
            continue

        print("Updating language:", lang_key)
        metadata = lang_metadata[lang_key]
        # Update the language data with new keys
        updated_data = update_dict_with_new_keys(
            reference_data, lang_specific_data
        )

        filename = metadata["splatoonLanguageKey"] + ".json"
        # Add metadata back to the language data as the first key
        data = {"metadata": metadata, **updated_data}
        with open(f"i18n/{filename}", "w") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode())


def update_supported_languages(lang_metadata: dict) -> None:
    supported_languages = get_supported_languages()
    for metadata in lang_metadata.values():
        spl_key = metadata["splatoonLanguageKey"]
        if spl_key not in supported_languages:
            supported_languages.append(spl_key)

    write_supported_languages(supported_languages)

    # Update supported_languages.js
    supported_languages_js = {}
    for metadata in lang_metadata.values():
        key = metadata["splatoonLanguageKey"]
        supported_languages_js[key] = metadata["languageNames"]

    with open(REACT_SUPPLANG_FILE, "w") as f:
        f.write(
            "const SUPPORTED_LANGUAGES = "
            + orjson.dumps(
                supported_languages_js, option=orjson.OPT_INDENT_2
            ).decode()
            + ";\n\nexport default SUPPORTED_LANGUAGES;\n"
        )


def update_i18n_js(lang_metadata: dict) -> None:
    with open(REACT_I18N_FILE, "r") as f:
        i18n_js = f.read()

    supported_languages = list(lang_metadata.keys())

    new_i18n_js = re.sub(
        r"supportedLngs: \[.*?\]",
        f"supportedLngs: {orjson.dumps(supported_languages).decode()}",
        i18n_js,
    )

    with open(REACT_I18N_FILE, "w") as f:
        f.write(new_i18n_js)


def update_locales(language_data: dict) -> None:
    for lang_key, lang_data in language_data.items():
        locale_path = os.path.join(REACT_LOCALES_DIR, lang_key)
        if not os.path.exists(locale_path):
            os.makedirs(locale_path)

        for key, value in lang_data.items():
            with open(os.path.join(locale_path, f"{key}.json"), "w") as f:
                f.write(
                    orjson.dumps(value, option=orjson.OPT_INDENT_2).decode()
                )


if __name__ == "__main__":
    session = get_boto3_session()
    client = get_boto3_client(session)

    language_data, lang_metadata = get_i18n_data(client)
    save_updated_languages(language_data, lang_metadata)
    update_supported_languages(lang_metadata)
    update_i18n_js(lang_metadata)
    update_locales(language_data)
    print("Languages updated.")
