import asyncio
import importlib
import json
import zlib

import pytest

from shared_lib.monitoring import prometheus


class _AggregateMetricSpy:
    def __init__(self):
        self.set_values = []
        self.increments = []
        self.observations = []

    def set(self, value):
        self.set_values.append(value)

    def inc(self, value=1):
        self.increments.append(value)

    def observe(self, value):
        self.observations.append(value)


class _EventMetricSpy:
    def labels(self, **_labels):
        return self

    def inc(self, _value=1):
        return None


class _DummyWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_bytes(self, message):
        self.messages.append(message)


class _EmptyRedis:
    def get(self, _key):
        return None


class _DummyCelery:
    def send_task(self, *_args, **_kwargs):
        return None


class _StopPubSub(Exception):
    pass


class _SingleMessagePubSub:
    def __init__(self, data):
        self._message = {"type": "message", "data": data}

    def get_message(self):
        if self._message is None:
            raise _StopPubSub
        message = self._message
        self._message = None
        return message


class _BroadcastManagerSpy:
    def __init__(self):
        self.calls = []

    async def broadcast_player_data(self, message, player_id, **kwargs):
        self.calls.append((message, player_id, kwargs))


class _ValueRedis:
    def __init__(self, value):
        self.value = value

    def get(self, _key):
        return self.value


def _load_connections(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    return importlib.import_module("fast_api_app.connections")


def test_websocket_metrics_have_no_player_labels():
    assert prometheus.WEBSOCKET_CONNECTIONS._labelnames == ()
    assert prometheus.WEBSOCKET_BROADCAST_DURATION._labelnames == ()
    assert prometheus.WEBSOCKET_BYTES_SENT._labelnames == ()
    assert prometheus.PUBSUB_BYTES_BROADCAST._labelnames == ()


def test_connection_manager_records_aggregate_websocket_metrics(monkeypatch):
    connections = _load_connections(monkeypatch)
    connection_gauge = _AggregateMetricSpy()
    broadcast_duration = _AggregateMetricSpy()
    bytes_sent = _AggregateMetricSpy()
    events = _EventMetricSpy()

    monkeypatch.setattr(connections, "metrics_enabled", lambda: True)
    monkeypatch.setattr(connections, "redis_conn", _EmptyRedis())
    monkeypatch.setattr(connections, "celery", _DummyCelery())
    monkeypatch.setattr(connections, "WEBSOCKET_CONNECTIONS", connection_gauge)
    monkeypatch.setattr(
        connections, "WEBSOCKET_BROADCAST_DURATION", broadcast_duration
    )
    monkeypatch.setattr(connections, "WEBSOCKET_BYTES_SENT", bytes_sent)
    monkeypatch.setattr(connections, "WEBSOCKET_EVENTS", events)

    first = _DummyWebSocket()
    second = _DummyWebSocket()
    third = _DummyWebSocket()
    manager = connections.ConnectionManager()

    asyncio.run(manager.connect(first, "player-1", "connection-1"))
    asyncio.run(manager.connect(second, "player-1", "connection-2"))
    asyncio.run(manager.connect(third, "player-2", "connection-3"))

    assert connection_gauge.set_values == [1, 2, 3]

    payload = b"aggregate websocket metrics"
    asyncio.run(manager.broadcast_player_data(payload, "player-1"))

    compressed_payload = zlib.compress(payload)
    assert first.messages == [compressed_payload]
    assert second.messages == [compressed_payload]
    assert third.messages == []
    assert bytes_sent.increments == [len(compressed_payload) * 2]
    assert len(broadcast_duration.observations) == 1
    assert broadcast_duration.observations[0] >= 0

    manager.disconnect("player-1", "connection-1")
    manager.disconnect("player-2", "connection-3")
    manager.disconnect("player-1", "connection-2")

    assert connection_gauge.set_values == [1, 2, 3, 2, 1, 0]


def test_pubsub_chunk_bytes_are_aggregated_without_changing_player_routing(
    monkeypatch,
):
    pubsub_module = importlib.import_module("fast_api_app.pubsub")
    bytes_broadcast = _AggregateMetricSpy()
    events = _EventMetricSpy()
    manager = _BroadcastManagerSpy()
    cached_payload = b"cached legacy payload"
    raw_message = json.dumps(
        {
            "type": "player_chunk",
            "player_id": "player-1",
            "phase": "complete",
            "key": "player-cache-key",
        }
    )

    monkeypatch.setattr(pubsub_module, "metrics_enabled", lambda: True)
    monkeypatch.setattr(
        pubsub_module, "PUBSUB_BYTES_BROADCAST", bytes_broadcast
    )
    monkeypatch.setattr(pubsub_module, "PUBSUB_EVENTS", events)
    monkeypatch.setattr(pubsub_module, "connection_manager", manager)
    monkeypatch.setattr(
        pubsub_module, "redis_conn", _ValueRedis(cached_payload)
    )

    with pytest.raises(_StopPubSub):
        asyncio.run(
            pubsub_module.process_pubsub_message(
                _SingleMessagePubSub(raw_message)
            )
        )

    assert bytes_broadcast.increments == [len(raw_message), len(cached_payload)]
    assert manager.calls == [
        (raw_message, "player-1", {"progressive_only": True}),
        (cached_payload, "player-1", {"legacy_only": True}),
    ]


def test_pubsub_legacy_bytes_are_aggregated_without_changing_player_routing(
    monkeypatch,
):
    pubsub_module = importlib.import_module("fast_api_app.pubsub")
    bytes_broadcast = _AggregateMetricSpy()
    events = _EventMetricSpy()
    manager = _BroadcastManagerSpy()
    cached_payload = b"legacy payload"
    raw_message = json.dumps(
        {"player_id": "player-2", "key": "player-cache-key"}
    )

    monkeypatch.setattr(pubsub_module, "metrics_enabled", lambda: True)
    monkeypatch.setattr(
        pubsub_module, "PUBSUB_BYTES_BROADCAST", bytes_broadcast
    )
    monkeypatch.setattr(pubsub_module, "PUBSUB_EVENTS", events)
    monkeypatch.setattr(pubsub_module, "connection_manager", manager)
    monkeypatch.setattr(
        pubsub_module, "redis_conn", _ValueRedis(cached_payload)
    )

    with pytest.raises(_StopPubSub):
        asyncio.run(
            pubsub_module.process_pubsub_message(
                _SingleMessagePubSub(raw_message)
            )
        )

    assert bytes_broadcast.increments == [len(cached_payload)]
    assert manager.calls == [(cached_payload, "player-2", {})]
