def test_ripple_limit_validation_422(client, test_token):
    headers = {"authorization": f"Bearer {test_token}"}
    r = client.get("/api/ripple/leaderboard?limit=0", headers=headers)
    assert r.status_code == 422
