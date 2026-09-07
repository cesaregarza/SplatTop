import importlib

import numpy as np
import orjson
import pandas as pd

from shared_lib.constants import SKILL_OFFSET_REDIS_KEY


def test_skill_offset_selects_mode_and_region_slices(
    client, fake_redis, monkeypatch
):
    import fast_api_app.routes.weapon_info as weapon_info_mod

    monkeypatch.setattr(
        weapon_info_mod, "redis_conn", fake_redis, raising=False
    )

    payload = {
        "all": {
            "all": [{"weapon_name": "global"}],
            "Tentatek": [{"weapon_name": "tentatek"}],
            "Takoroka": [{"weapon_name": "takoroka"}],
        },
        "Splat Zones": {
            "all": [{"weapon_name": "zones"}],
            "Tentatek": [{"weapon_name": "zones_tentatek"}],
            "Takoroka": [{"weapon_name": "zones_takoroka"}],
        },
    }
    fake_redis.set(SKILL_OFFSET_REDIS_KEY, orjson.dumps(payload))

    assert client.get("/api/skill-offset").json() == payload["all"]["all"]
    assert (
        client.get("/api/skill-offset?region=Tentatek").json()
        == payload["all"]["Tentatek"]
    )
    assert (
        client.get("/api/skill-offset?mode=Splat%20Zones").json()
        == payload["Splat Zones"]["all"]
    )
    assert (
        client.get(
            "/api/skill-offset?mode=Splat%20Zones&region=Takoroka"
        ).json()
        == payload["Splat Zones"]["Takoroka"]
    )


def test_skill_offset_rejects_unknown_slices(client, fake_redis, monkeypatch):
    import fast_api_app.routes.weapon_info as weapon_info_mod

    monkeypatch.setattr(
        weapon_info_mod, "redis_conn", fake_redis, raising=False
    )
    fake_redis.set(SKILL_OFFSET_REDIS_KEY, orjson.dumps({"all": {"all": []}}))

    response = client.get("/api/skill-offset?mode=Unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Skill offset slice not found."}


def test_align_sorted_xp_scaled_to_surface_resamples_percentiles(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )

    input_values = np.linspace(0, 1, 5)
    aligned = skill_offset_mod.align_sorted_xp_scaled_to_surface(
        skill_offset_mod.pd.Series(input_values), 11
    )

    assert len(aligned) == 11
    assert np.isclose(aligned.iloc[0], 0.0)
    assert np.isclose(aligned.iloc[-1], 1.0)
    assert np.all(np.diff(aligned.to_numpy()) >= 0)


def test_align_sorted_xp_scaled_to_surface_keeps_canonical_size(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )

    input_values = np.array([0.1, 0.3, 0.6, 0.9])
    aligned = skill_offset_mod.align_sorted_xp_scaled_to_surface(
        skill_offset_mod.pd.Series(input_values), len(input_values)
    )

    np.testing.assert_allclose(aligned.to_numpy(), input_values)


def test_load_probabilities_reuses_one_readonly_mmap(monkeypatch, tmp_path):
    import shared_lib.analytics as analytics_mod

    surface = np.arange(12, dtype=np.float64).reshape(4, 3)
    np.save(tmp_path / "probabilities.npy", surface)
    monkeypatch.setattr(analytics_mod, "PATH", tmp_path)
    analytics_mod.load_probabilities.cache_clear()
    try:
        first = analytics_mod.load_probabilities()
        second = analytics_mod.load_probabilities()
    finally:
        analytics_mod.load_probabilities.cache_clear()

    assert first is second
    assert isinstance(first, np.memmap)
    assert not first.flags.writeable
    np.testing.assert_array_equal(first, surface)


def test_compute_probability_map_does_not_mutate_probability_surface(
    monkeypatch,
):
    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )
    surface = np.arange(24, dtype=np.float64).reshape(6, 4)
    original = surface.copy()
    surface.flags.writeable = False
    monkeypatch.setattr(skill_offset_mod, "load_probabilities", lambda: surface)
    monkeypatch.setattr(skill_offset_mod, "NUM_BINS", 2)

    skill_offset_mod.compute_probability_map(
        pd.Series(np.linspace(0.1, 0.9, surface.shape[0]))
    )

    np.testing.assert_array_equal(surface, original)


def test_map_indices_interpolates_unique_bins_once_per_missing_count(
    monkeypatch,
):
    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )
    melted = pd.DataFrame(
        {
            "bin_center": [0.25, 0.75, 0.25, 0.75],
            "lower": [0.0, 0.5, 0.0, 0.5],
            "upper": [0.5, 1.0, 0.5, 1.0],
            "k": [1, 1, 3, 3],
            "log_prob": [2.0, 2.0, 3.0, 3.0],
        }
    )
    monkeypatch.setattr(
        skill_offset_mod, "compute_probability_map", lambda _series: melted
    )

    created = []
    interpolation_points = []

    def fake_create_interpolator(_df):
        created.append(True)

        def interpolate(points):
            interpolation_points.append(points)
            return np.array([2.0, 1.0])

        return interpolate

    monkeypatch.setattr(
        skill_offset_mod, "create_interpolator", fake_create_interpolator
    )
    source = pd.DataFrame(
        {
            "weapon_name": [
                "exact",
                "missing-a",
                "missing-a",
                "missing-b",
                "missing-b",
            ],
            "weapon_image": ["e", "a", "a", "b", "b"],
            "xp_scaled": [0.25, 0.4, 0.6, 0.3, 0.7],
        }
    )

    result = skill_offset_mod.map_indices_to_data(source)

    assert len(created) == 1
    assert len(interpolation_points) == 1
    centers, counts = interpolation_points[0]
    assert len(centers) == len(melted["bin_center"].unique())
    assert len(counts) == len(centers)
    assert result.loc[result["count"] == 2, "mode_bin_center"].eq(0.25).all()
    assert result.loc[result["count"] == 2, "median_logprob"].eq(2.0).all()
    assert (
        skill_offset_mod.subcompute_skill_offset(
            result.loc[result["count"] == 2], "median"
        )
        .eq(0.0)
        .all()
    )


def test_map_indices_preserves_legacy_interpolation_and_exact_results(
    monkeypatch,
):
    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )
    surface = np.arange(1, 81, dtype=float).reshape(10, 8)
    surface.flags.writeable = False
    monkeypatch.setattr(skill_offset_mod, "load_probabilities", lambda: surface)
    monkeypatch.setattr(skill_offset_mod, "NUM_BINS", 4)
    source = pd.DataFrame(
        {
            "weapon_name": ["odd"] * 3 + ["even"] * 4 + ["repeat-even"] * 4,
            "weapon_image": ["o"] * 3 + ["e"] * 4 + ["r"] * 4,
            "xp_scaled": np.linspace(0.05, 0.95, 11),
        }
    )
    melted = skill_offset_mod.compute_probability_map(
        source["xp_scaled"].sort_values()
    )
    interpolator = skill_offset_mod.create_interpolator(melted)
    expected = []
    for name, rows in source.groupby("weapon_name", sort=True):
        count = len(rows)
        median = rows["xp_scaled"].median()
        subset = melted.loc[melted["k"] == count]
        if subset.empty:
            subset = melted[["bin_center", "lower", "upper"]].assign(
                log_prob=interpolator(
                    (melted["bin_center"], [count] * len(melted))
                )
            )
        mode = subset.loc[subset["log_prob"].idxmax()]
        matching = subset.loc[
            (subset["lower"] <= median) & (subset["upper"] >= median)
        ]
        expected.append(
            {
                "weapon_name": name,
                "weapon_image": rows["weapon_image"].iloc[0],
                "count": count,
                "median": median,
                "mode_logprob": mode["log_prob"],
                "mode_bin_center": mode["bin_center"],
                "median_logprob": matching["log_prob"].iloc[0],
            }
        )
    actual = skill_offset_mod.map_indices_to_data(source)
    pd.testing.assert_frame_equal(actual, pd.DataFrame(expected))


def test_exact_counts_do_not_construct_an_interpolator(monkeypatch):
    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )
    surface = np.ones((4, 2), dtype=float)
    monkeypatch.setattr(skill_offset_mod, "load_probabilities", lambda: surface)
    monkeypatch.setattr(skill_offset_mod, "NUM_BINS", 2)

    def unexpected_interpolator(_melted):
        raise AssertionError("Exact grid count should not need interpolation")

    monkeypatch.setattr(
        skill_offset_mod, "create_interpolator", unexpected_interpolator
    )
    source = pd.DataFrame(
        {"weapon_name": ["one"], "weapon_image": ["o"], "xp_scaled": [0.5]}
    )
    result = skill_offset_mod.map_indices_to_data(source)
    assert len(result) == 1
    assert result["count"].iloc[0] == 1
