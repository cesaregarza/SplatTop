def test_rate_limit_separate_identities_for_different_tokens(
    client_factory, token_builder, fake_redis
):
    # Build two different tokens in same redis instance
    t1, _, _ = token_builder(scopes=["misc.ping"])
    t2, _, _ = token_builder(scopes=["misc.ping"])

    with client_factory(redis=fake_redis) as c:
        codes1 = [
            c.get(
                "/api/ping", headers={"authorization": f"Bearer {t1}"}
            ).status_code
            for _ in range(11)
        ]
        assert codes1.count(200) >= 10
        assert 429 in codes1

        # Second identity should get its own allowance
        codes2 = [
            c.get(
                "/api/ping", headers={"authorization": f"Bearer {t2}"}
            ).status_code
            for _ in range(10)
        ]
        assert 429 not in codes2
        assert codes2.count(200) == 10
