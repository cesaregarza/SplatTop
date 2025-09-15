def test_mint_sends_persist_and_revoke_sends_task(
    client, override_admin, celery_spy
):
    r = client.post("/api/admin/tokens", json={"name": "celery"})
    assert r.status_code == 200
    body = r.json()
    tok_id = body["id"]

    # Verify persist call
    names = [c[0] for c in celery_spy.calls]
    assert "tasks.persist_api_token" in names
    # Find the persist call and assert token id and name flow through
    idx = names.index("tasks.persist_api_token")
    args = celery_spy.calls[idx][1]
    assert args[0] == tok_id
    assert args[1] == "celery"

    # Clear calls and revoke
    celery_spy.calls.clear()
    rr = client.delete(f"/api/admin/tokens/{tok_id}")
    assert rr.status_code == 200
    names2 = [c[0] for c in celery_spy.calls]
    assert names2 == ["tasks.revoke_api_token"]
    assert celery_spy.calls[0][1] == [tok_id]
