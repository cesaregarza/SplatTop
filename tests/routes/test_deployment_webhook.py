import hmac
import importlib
import time

import orjson
import pytest
from cryptography.fernet import Fernet


def _encrypt_payload(key: bytes, payload: dict) -> str:
    token = Fernet(key).encrypt(orjson.dumps(payload))
    return token.decode("utf-8")


def _build_headers(secret: str, timestamp: int, body: bytes) -> dict:
    signature_payload = f"{timestamp}\n{body.decode('utf-8')}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), signature_payload, digestmod="sha256"
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Timestamp": str(timestamp),
        "X-Signature-256": f"sha256={signature}",
    }


@pytest.fixture()
def deployment_module():
    mod = importlib.import_module("fast_api_app.routes.deployment_webhook")
    mod.reset_webhook_state()
    yield mod
    mod.reset_webhook_state()


def test_rollout_success(client, deployment_module, monkeypatch):
    module = deployment_module
    client.app.dependency_overrides[module.require_api_token] = lambda: True

    key = Fernet.generate_key()
    secret = "super-secret"
    target_config = {
        "agent8s": {
            "namespace": "discord",
            "deployment": "agent8s",
            "container": "agent8s",
            "image_prefixes": ["registry.example.com/agent8s"],
        }
    }

    monkeypatch.setenv("DEPLOY_WEBHOOK_FERNET_KEY", key.decode("utf-8"))
    monkeypatch.setenv("DEPLOY_WEBHOOK_SECRET", secret)
    monkeypatch.setenv(
        "DEPLOYMENT_WEBHOOK_TARGETS", orjson.dumps(target_config).decode()
    )
    module.reset_webhook_state()

    payload = {
        "target": "agent8s",
        "image": "registry.example.com/agent8s@sha256:abc123",
        "sha": "deadbeef",
        "annotations": {"ci": "github"},
    }
    token = _encrypt_payload(key, payload)
    body = orjson.dumps({"token": token})
    timestamp = int(time.time())
    headers = _build_headers(secret, timestamp, body)

    captured = {}

    def fake_trigger(target, image, commit_sha, extra_annotations):
        captured["target"] = target
        captured["image"] = image
        captured["commit"] = commit_sha
        captured["annotations"] = extra_annotations
        return {
            "deploy-webhook.splat-top.dev/last-triggered": "1234",
            "deploy-webhook.splat-top.dev/image": image,
        }

    monkeypatch.setattr(module, "trigger_rolling_update", fake_trigger)

    response = client.post(
        "/api/webhooks/deployments/rollout?wait=true",
        content=body,
        headers=headers,
    )

    assert response.status_code == 200
    assert captured["target"].slug == "agent8s"
    assert captured["image"] == payload["image"]
    assert captured["commit"] == payload["sha"]
    assert captured["annotations"] == {"ci": "github"}
    data = response.json()
    assert data["status"] == "accepted"
    assert data["target"] == "agent8s"
    assert data["namespace"] == "discord"
    assert data["deployment"] == "agent8s"
    assert data["image"] == payload["image"]
    assert data["commitSha"] == payload["sha"]
    client.app.dependency_overrides.clear()


def test_invalid_signature(client, deployment_module, monkeypatch):
    module = deployment_module
    client.app.dependency_overrides[module.require_api_token] = lambda: True

    key = Fernet.generate_key()
    monkeypatch.setenv("DEPLOY_WEBHOOK_FERNET_KEY", key.decode("utf-8"))
    monkeypatch.setenv("DEPLOY_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv(
        "DEPLOYMENT_WEBHOOK_TARGETS",
        orjson.dumps(
            {
                "agent8s": {
                    "namespace": "discord",
                    "deployment": "agent8s",
                }
            }
        ).decode(),
    )
    module.reset_webhook_state()

    token = _encrypt_payload(
        key, {"target": "agent8s", "image": "registry/agent8s:latest"}
    )
    body = orjson.dumps({"token": token})
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": str(timestamp),
        "X-Signature-256": "sha256=invalid",
    }

    response = client.post(
        "/api/webhooks/deployments/rollout", content=body, headers=headers
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"
    client.app.dependency_overrides.clear()


def test_disallowed_image_rejected(client, deployment_module, monkeypatch):
    module = deployment_module
    client.app.dependency_overrides[module.require_api_token] = lambda: True

    key = Fernet.generate_key()
    secret = "secret"

    monkeypatch.setenv("DEPLOY_WEBHOOK_FERNET_KEY", key.decode("utf-8"))
    monkeypatch.setenv("DEPLOY_WEBHOOK_SECRET", secret)
    monkeypatch.setenv(
        "DEPLOYMENT_WEBHOOK_TARGETS",
        orjson.dumps(
            {
                "agent8s": {
                    "namespace": "discord",
                    "deployment": "agent8s",
                    "image_prefixes": ["registry.example.com/agent8s"],
                }
            }
        ).decode(),
    )
    module.reset_webhook_state()

    payload = {
        "target": "agent8s",
        "image": "registry.example.com/other@sha256:123",
    }
    token = _encrypt_payload(key, payload)
    body = orjson.dumps({"token": token})
    timestamp = int(time.time())
    headers = _build_headers(secret, timestamp, body)

    response = client.post(
        "/api/webhooks/deployments/rollout", content=body, headers=headers
    )
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]
    client.app.dependency_overrides.clear()
