"""Deterministic settings shared by FFHQ-Wrinkle evaluation commands."""

from __future__ import annotations

import os
import random
from typing import Any

DEFAULT_SEED = 2024


def seed_everything(seed: int = DEFAULT_SEED, *, deterministic: bool = True) -> dict[str, Any]:
    """Seed Python, NumPy, and (when installed) PyTorch.

    ``PYTHONHASHSEED`` must be present before Python starts to affect hash
    randomization in the current interpreter. Setting it here guarantees that
    child processes inherit the requested value.
    """

    if seed < 0:
        raise ValueError("seed must be non-negative")

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)

    seeded = {"seed": seed, "python": True, "numpy": False, "torch": False}

    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        np.random.seed(seed)
        seeded["numpy"] = True

    try:
        import torch
    except ImportError:
        torch = None
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            torch.use_deterministic_algorithms(True, warn_only=True)
        seeded["torch"] = True

    return seeded


def seed_worker(worker_id: int) -> None:
    """Seed a PyTorch DataLoader worker from its framework-provided seed."""

    del worker_id  # The framework seed already incorporates the worker id.
    try:
        import numpy as np
        import torch
    except ImportError as exc:
        raise RuntimeError("seed_worker requires NumPy and PyTorch") from exc

    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)

