from shared_lib.monitoring.prometheus import _merge_keys, _to_float


def test_merge_keys_combines_iterables() -> None:
    combined = _merge_keys(["a", "b"], ["b", "c"], [])

    assert combined == {"a", "b", "c"}


def test_to_float_handles_none_and_invalid() -> None:
    assert _to_float(None, default=1.5) == 1.5
    assert _to_float("3.2") == 3.2
    assert _to_float("bad", default=2.0) == 2.0
