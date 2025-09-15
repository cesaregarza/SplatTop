import pytest

from shared_lib.constants import API_TOKEN_PREFIX


@pytest.mark.parametrize(
    "raw_token,expected_tid,expected_sec",
    [
        (
            f"{API_TOKEN_PREFIX}_00000000-0000-4000-8000-000000000001_abcDEF123",
            "00000000-0000-4000-8000-000000000001",
            "abcDEF123",
        ),
        ("not_a_prefixed_token", None, "not_a_prefixed_token"),
        (
            f"{API_TOKEN_PREFIX}_00000000-0000-4000-8000-0000000000AA_abc_def_ghi",
            "00000000-0000-4000-8000-0000000000AA",
            "abc_def_ghi",
        ),
        (
            f"{API_TOKEN_PREFIX}_onlyprefix",
            None,
            f"{API_TOKEN_PREFIX}_onlyprefix",
        ),
    ],
)
def test_parse_token_variants_parametrized(
    auth_module, raw_token, expected_tid, expected_sec
):
    auth = auth_module
    tid, sec = auth.parse_token(raw_token)
    assert tid == expected_tid
    assert sec == expected_sec


def test_hash_secret_with_pepper_env(auth_module, monkeypatch):
    monkeypatch.setenv("API_TOKEN_PEPPER", "pep")
    auth = auth_module
    assert (
        auth.hash_secret("s", pepper=None)
        == auth.hash_secret("s", pepper="pep")
        != auth.hash_secret("s", pepper="pep2")
    )
