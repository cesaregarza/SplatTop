import pathlib

import orjson

SUPPORTED_LANGUAGE_PATH = (
    pathlib.Path(__file__).parent / "supported_languages.json"
)


def get_supported_languages() -> list[str]:
    with open(SUPPORTED_LANGUAGE_PATH, "r") as f:
        try:
            return orjson.loads(f.read())
        except orjson.JSONDecodeError:
            return []


def write_supported_languages(languages: list[str]) -> None:
    with open(SUPPORTED_LANGUAGE_PATH, "w") as f:
        f.write(orjson.dumps(languages).decode("utf-8"))
