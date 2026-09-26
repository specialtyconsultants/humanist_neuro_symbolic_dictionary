"""Reading helpers shared across `core/`.

`read_yaml` exists because `yaml.safe_load(open(p))` leaks a file handle until
the garbage collector gets to it, and the pattern appeared at eleven call sites
across two distributions. Centralising it also puts the encoding choice in one
place, which matters for a corpus carrying Yup'ik, Inupiaq and Spanish notices.
"""
from __future__ import annotations

from typing import Any

import yaml


def read_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
