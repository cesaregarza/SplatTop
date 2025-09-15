from shared_lib.constants import API_TOKEN_META_PREFIX


def test_admin_list_sorted_desc_and_revoke_404(
    client, override_admin, monkeypatch, fake_redis
):
    import types

    import fast_api_app.routes.admin_tokens as admin_mod

    # Make minting deterministic in time
    times = [1000.0, 2000.0]
    last = {"v": times[0]}

    def _next_time():
        # Return first two controlled values, then stick to the last one to avoid
        # interfering with unrelated middleware that also calls time.time().
        if times:
            last["v"] = times.pop(0)
        return last["v"]

    monkeypatch.setattr(admin_mod.time, "time", _next_time, raising=False)

    # Mint two tokens
    r1 = client.post("/api/admin/tokens", json={"name": "A"})
    assert r1.status_code == 200
    r2 = client.post("/api/admin/tokens", json={"name": "B"})
    assert r2.status_code == 200

    # List sorted by created_at_ms desc -> second minted first
    rlist = client.get("/api/admin/tokens")
    assert rlist.status_code == 200
    toks = rlist.json()["tokens"]
    assert len(toks) >= 2
    # Ensure sorted by created_at_ms desc
    sorted_copy = sorted(
        toks, key=lambda x: x.get("created_at_ms", 0), reverse=True
    )
    assert toks == sorted_copy

    # Revoking unknown id yields 404
    r404 = client.delete("/api/admin/tokens/does-not-exist")
    assert r404.status_code == 404
    assert r404.json().get("detail") == "Token not found"

    # Revoke the first token and verify meta updated
    tok_id = r1.json()["id"]
    rr = client.delete(f"/api/admin/tokens/{tok_id}")
    assert rr.status_code == 200
    meta = fake_redis.hgetall(f"{API_TOKEN_META_PREFIX}{tok_id}")
    assert int(meta.get("revoked", 0)) == 1
    assert int(meta.get("revoked_at_ms", 0)) > 0
