import os

import orjson
import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from fast_api_app.routes.sendou_proxy import (
    ROUTE_KEY_TOURNAMENT_MATCH,
    _decode_and_extract,
)


def _turbo_stream(route_key: str) -> bytes:
    return orjson.dumps(
        [
            {"_1": 2},
            route_key,
            {"_3": 4},
            "data",
            {"_5": 6},
            "match",
            {"_7": 8},
            "id",
            134701,
        ]
    )


def test_tournament_match_extracts_current_sendou_route_data():
    result = _decode_and_extract(
        _turbo_stream(ROUTE_KEY_TOURNAMENT_MATCH),
        ROUTE_KEY_TOURNAMENT_MATCH,
    )

    assert ROUTE_KEY_TOURNAMENT_MATCH == (
        "features/tournament-match/routes/to.$id.matches.$mid"
    )
    assert result == {"data": {"match": {"id": 134701}}}


def test_missing_sendou_route_data_fails_instead_of_returning_route_tree():
    with pytest.raises(ValueError, match="Route data not found"):
        _decode_and_extract(
            _turbo_stream("features/sendou/renamed-route"),
            ROUTE_KEY_TOURNAMENT_MATCH,
        )
