def test_rate_limit_per_minute_cap(client_factory, test_token, fake_redis):
    # Disable per-sec limit and set tight per-minute cap
    with client_factory(
        env={"API_RL_PER_SEC": "0", "API_RL_PER_MIN": "5"},
        redis=fake_redis,
    ) as c:
        headers = {"Authorization": f"Bearer {test_token}"}
        codes = [
            c.get("/api/ping", headers=headers).status_code for _ in range(7)
        ]
        assert codes.count(200) >= 5
        assert 429 in codes


import pytest


@pytest.mark.parametrize(
    "env,expected",
    [
        ({"API_RL_FAIL_OPEN": "true"}, 200),  # allow when fail-open
        ({}, 429),  # default fail-closed
    ],
)
def test_rate_limit_outage_behavior(client_factory, monkeypatch, env, expected):
    """When Redis pipeline raises, behavior depends on API_RL_FAIL_OPEN."""
    with client_factory(env=env) as c:
        import fast_api_app.middleware as mw_mod

        def _boom():
            raise RuntimeError("down")

        # Make pipeline blow up to simulate outage
        monkeypatch.setattr(mw_mod.redis_conn, "pipeline", _boom, raising=False)

        r = c.get("/api/ripple/leaderboard/docs")
        assert r.status_code == expected
