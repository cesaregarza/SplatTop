import pathlib
from functools import lru_cache

import numpy as np

PATH = pathlib.Path(__file__).parent


@lru_cache(maxsize=1)
def load_probabilities() -> np.ndarray:
    """Return the static probability surface as a shared read-only mapping.

    The surface is used by each skill-offset slice, so loading it lazily and
    retaining the mmap avoids a fresh 61 MiB allocation for every slice.  A
    read-only mapping is safe to share with forked workers; the cache itself
    remains process-local.
    """
    path = PATH / "probabilities.npy"
    return np.load(path, mmap_mode="r", allow_pickle=False)
