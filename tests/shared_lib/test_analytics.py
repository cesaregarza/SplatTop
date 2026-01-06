import numpy as np

from shared_lib.analytics import load_probabilities


def test_load_probabilities_returns_array() -> None:
    data = load_probabilities()

    assert isinstance(data, np.ndarray)
    assert data.size > 0
