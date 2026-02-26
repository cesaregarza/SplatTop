import datetime as dt

import orjson
import pytest

import shared_lib.utils as utils
from shared_lib.constants import BASE_CDN_URL


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    utils.weapon_cache.clear()
    utils.badge_cache.clear()
    utils.banner_cache.clear()
    utils.alt_weapon_cache.clear()


def test_get_seasons_bounds_and_order() -> None:
    seasons = utils.get_seasons(dt.datetime(2023, 7, 15))

    assert seasons[0] == (dt.datetime(2022, 9, 1), "Drizzle Season 2022")
    assert seasons[-1] == (dt.datetime(2023, 6, 1), "Sizzle Season 2023")
    assert len(seasons) == 4


def test_calculate_cache_refresh_flags_negative_and_max() -> None:
    reference = dt.datetime(2024, 1, 1, 10, 10)
    target_before = reference - dt.timedelta(seconds=1)
    target_far = reference + dt.timedelta(seconds=4000)

    assert utils.calculate_cache_refresh(
        reference, target_before, [15], max_cache_time=3600
    )
    assert utils.calculate_cache_refresh(
        reference, target_far, [15], max_cache_time=3600
    )


def test_calculate_cache_refresh_barrier_crossing() -> None:
    reference = dt.datetime(2024, 1, 1, 10, 10)
    target_ok = dt.datetime(2024, 1, 1, 10, 12)
    target_cross = dt.datetime(2024, 1, 1, 10, 16)

    assert not utils.calculate_cache_refresh(
        reference, target_ok, [15], max_cache_time=3600
    )
    assert utils.calculate_cache_refresh(
        reference, target_cross, [15], max_cache_time=3600
    )


def test_calculate_cache_refresh_wraps_hour() -> None:
    reference = dt.datetime(2024, 1, 1, 10, 55)
    target_wrapped = dt.datetime(2024, 1, 1, 11, 3)

    assert utils.calculate_cache_refresh(
        reference, target_wrapped, [2], max_cache_time=3600
    )


def test_weapon_badge_banner_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        utils,
        "get_weapon_xref",
        lambda: [{"Id": 1, "__RowId": "HeroShot"}],
    )
    monkeypatch.setattr(
        utils,
        "get_badge_xref",
        lambda: [{"Id": 2, "Name": "Champion"}],
    )
    monkeypatch.setattr(
        utils,
        "get_banner_xref",
        lambda: [{"Id": 3, "__RowId": "Banner"}],
    )

    assert utils.get_weapon_name(1) == "HeroShot"
    assert (
        utils.get_weapon_image(1)
        == f"{BASE_CDN_URL}assets/weapon_flat/Path_Wst_HeroShot.png"
    )
    assert utils.get_badge_name(2) == "Champion"
    assert (
        utils.get_badge_image("2")
        == f"{BASE_CDN_URL}assets/badge/Badge_Champion.png"
    )
    assert utils.get_badge_image(None) == ""
    assert utils.get_banner_name(3) == "Banner"
    assert (
        utils.get_banner_image(3)
        == f"{BASE_CDN_URL}assets/npl/Npl_Banner.png"
    )


def test_get_all_alt_kits_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "1": {"reference_id": 1},
        "2": {"reference_id": 1},
        "3": {"reference_id": None},
        "4": "invalid",
        "5": {"reference_id": "5"},
        "6": {"reference_id": 7},
    }

    class DummyResponse:
        content = orjson.dumps(payload)

        def raise_for_status(self):
            return None

    monkeypatch.setattr(utils.requests, "get", lambda *args, **kwargs: DummyResponse())

    assert utils.get_all_alt_kits() == {"2": "1", "6": "7"}


def test_get_all_alt_kits_handles_request_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_error(*args, **kwargs):
        raise utils.requests.RequestException("boom")

    monkeypatch.setattr(utils.requests, "get", raise_error)

    assert utils.get_all_alt_kits() == {}


def test_get_all_alt_kits_handles_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyResponse:
        content = b"not-json"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(utils.requests, "get", lambda *args, **kwargs: DummyResponse())

    assert utils.get_all_alt_kits() == {}
