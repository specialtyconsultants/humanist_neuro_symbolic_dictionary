"""Reading helpers for nsjepa_contrib.

Duplicated from `core/schemas/_io.py` rather than imported, because this package
is a separate distribution that a vendor installs into a product without the
engine. See `core/provenance_tiers.yaml` for the same trade-off made explicitly
for corpus policy: ship a copy, and test that it has not drifted.
"""
from __future__ import annotations

from typing import Any

import yaml


def read_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
