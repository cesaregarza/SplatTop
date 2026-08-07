import zlib
from functools import partial


def test_player_websocket_dispatches_and_streams_compressed_payload(
    client, monkeypatch
):
    import fast_api_app.connections as connections
    import fast_api_app.routes.player_detail as player_detail

    class CelerySpy:
        def __init__(self):
            self.calls = []

        def send_task(self, name, args=None, kwargs=None):
            self.calls.append((name, list(args or []), dict(kwargs or {})))

    celery_spy = CelerySpy()
    monkeypatch.setattr(connections, "celery", celery_spy)
    connection_manager = player_detail.connection_manager
    connection_manager.active_connections.clear()
    payload = b'{"phase":"complete","player_id":"test-player"}'

    try:
        with client.websocket_connect(
            "/ws/player/test-player?progressive=1&version=2"
        ) as websocket:
            assert celery_spy.calls == [
                ("tasks.fetch_player_data", ["test-player"], {})
            ]

            player_connections = connection_manager.active_connections[
                "test-player"
            ]
            assert len(player_connections) == 1
            assert (
                next(iter(player_connections.values()))["progressive"] is True
            )

            client.portal.call(
                partial(
                    connection_manager.broadcast_player_data,
                    payload,
                    "test-player",
                    progressive_only=True,
                )
            )
            assert zlib.decompress(websocket.receive_bytes()) == payload

        assert "test-player" not in connection_manager.active_connections
    finally:
        connection_manager.active_connections.clear()
