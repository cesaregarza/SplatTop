import pathlib

import numpy as np

PATH = pathlib.Path(__file__).parent


def load_probabilities() -> np.ndarray:
    path = PATH / "probabilities.npy"
    return np.load(path)
