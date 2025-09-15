from shared_lib.constants import API_USAGE_QUEUE_KEY


def test_admin_routes_excluded_from_rate_limit(client, override_admin):
    # Using default RL config; admin routes excluded regardless of settings
    codes = [client.get("/api/admin/tokens").status_code for _ in range(5)]
    assert codes == [200] * 5


def test_admin_routes_not_enqueued_in_usage_queue(
    client, fake_redis, override_admin
):
    before = len(fake_redis._lists.get(API_USAGE_QUEUE_KEY, []))
    r = client.get("/api/admin/tokens")
    assert r.status_code == 200
    after = len(fake_redis._lists.get(API_USAGE_QUEUE_KEY, []))
    assert after == before
