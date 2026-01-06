import pytest

from shared_lib.turbo_stream import decode_turbo_stream, extract_route_data


def test_decode_turbo_stream_resolves_references_and_sentinels() -> None:
    data = [
        {
            "_1": 2,
            "_3": -5,
            "_4": -7,
            "plain": "ok",
            "_5": [6, 7],
            "_8": -2,
        },
        "route.key",
        {"name": "Alice"},
        "nullable",
        "undefined",
        "list",
        "alpha",
        "beta",
        "negative",
    ]

    decoded = decode_turbo_stream(data)

    assert decoded["route.key"] == {"name": "Alice"}
    assert decoded["nullable"] is None
    assert decoded["plain"] == "ok"
    assert decoded["list"] == ["alpha", "beta"]
    assert decoded["negative"] == -2
    assert "undefined" not in decoded


def test_decode_turbo_stream_returns_empty_for_non_object_root() -> None:
    assert decode_turbo_stream([123]) == {}


def test_decode_turbo_stream_rejects_non_list_payload() -> None:
    with pytest.raises(ValueError):
        decode_turbo_stream({"route": "data"})


def test_extract_route_data_returns_route_payload() -> None:
    data = [
        {"_1": 2},
        "route.key",
        {"name": "Alice"},
    ]

    assert extract_route_data(data, "route.key") == {"name": "Alice"}
    assert extract_route_data(data, "missing") is None
