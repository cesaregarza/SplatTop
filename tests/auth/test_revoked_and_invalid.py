from shared_lib.constants import API_TOKENS_ACTIVE_SET


def test_revoked_or_unknown_token_401(client, token_builder, fake_redis):
    token, tid, h = token_builder(scopes=["misc.ping"])  # ensure registered
    # Simulate revocation by removing from active set
    fake_redis._sets.get(API_TOKENS_ACTIVE_SET, set()).discard(h)

    r = client.get("/api/ping", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Invalid or revoked API token"
