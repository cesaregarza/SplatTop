def test_admin_mint_applies_default_scopes(client, override_admin):
    r = client.post("/api/admin/tokens", json={"name": "defaults"})
    assert r.status_code == 200
    tok_id = r.json()["id"]

    rlist = client.get("/api/admin/tokens")
    assert rlist.status_code == 200
    toks = rlist.json().get("tokens", [])
    meta = next(t for t in toks if t.get("id") == tok_id)
    scopes = set(meta.get("scopes") or [])
    assert {"ripple.read", "misc.ping"}.issubset(scopes)
