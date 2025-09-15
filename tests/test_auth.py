import importlib

from shared_lib.constants import API_TOKEN_PREFIX


def test_auth_parse_token_variants(monkeypatch):
    # Set DB envs so importing auth -> connections won't error
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    auth = importlib.import_module("fast_api_app.auth")

    # Valid token format
    token_id = "00000000-0000-4000-8000-000000000001"
    secret = "abcDEF123"
    raw = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"
    tid, sec = auth.parse_token(raw)
    assert tid == token_id
    assert sec == secret

    # Fallback: non-prefixed raw token returns (None, raw)
    tid2, sec2 = auth.parse_token("not_a_prefixed_token")
    assert tid2 is None
    assert sec2 == "not_a_prefixed_token"


def test_hash_secret_with_pepper_env(monkeypatch):
    # Set DB envs so importing auth -> connections won't error
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    monkeypatch.setenv("API_TOKEN_PEPPER", "pep")

    auth = importlib.import_module("fast_api_app.auth")
    assert (
        auth.hash_secret("s", pepper=None)
        == auth.hash_secret("s", pepper="pep")
        != auth.hash_secret("s", pepper="pep2")
    )
