"""Provenance tiers, loaded from the canonical table in `core/`.

The tier table is corpus policy: what counts as evidence, how much confidence
each kind may assert, and which kinds are independent of the party submitting
an entry. It lived in the contributor SDK, which put the definition of
"independent" inside the vendor-facing distribution — the engine could not read
it without installing that SDK, and a fork of the SDK could redefine the tiers
for its own submissions.

Domain norms and glyph vocabularies were already loaded from the repository for
exactly this reason. This is the same kind of object and now works the same way.
`nsjepa_contrib` keeps a copy so it can run air-gapped, and a test there asserts
the copy matches this file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from core.schemas._io import read_yaml

TIERS_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "provenance_tiers.yaml")


class ProvenanceError(ValueError):
    """A provenance string is malformed, or over-claims for its tier."""


@dataclass(frozen=True)
class Tier:
    name: str
    ceiling: float
    independent: bool
    measured: bool
    gloss: str
    can_support_positive: bool = True


@lru_cache(maxsize=4)
def load_tiers(path: str | None = None) -> dict[str, Tier]:
    path = path or TIERS_PATH
    data = read_yaml(path) or {}
    return {
        name: Tier(name=name, ceiling=float(spec["ceiling"]),
                   independent=bool(spec["independent"]),
                   measured=bool(spec.get("measured", False)),
                   gloss=spec.get("gloss", ""),
                   can_support_positive=bool(spec.get("can_support_positive", True)))
        for name, spec in (data.get("tiers") or {}).items()
    }


def parse(provenance: str, tiers: dict[str, Tier] | None = None) -> tuple[Tier, str, str]:
    """Split ``tier:identifier#section``. Section may be empty."""
    tiers = tiers if tiers is not None else load_tiers()
    if ":" not in provenance:
        raise ProvenanceError(
            f"provenance {provenance!r} has no tier; expected '<tier>:<id>#<section>'")
    tier_name, rest = provenance.split(":", 1)
    if tier_name not in tiers:
        raise ProvenanceError(
            f"unknown provenance tier {tier_name!r} in {provenance!r}; "
            f"known: {sorted(tiers)}")
    identifier, _, section = rest.partition("#")
    if not identifier:
        raise ProvenanceError(f"provenance {provenance!r} has an empty identifier")
    return tiers[tier_name], identifier, section


def check_confidence(provenance: str, confidence: float,
                     tiers: dict[str, Tier] | None = None) -> None:
    tier, _, _ = parse(provenance, tiers)
    if not 0.0 < confidence <= 1.0:
        raise ProvenanceError(f"confidence {confidence} outside (0, 1]")
    if confidence > tier.ceiling:
        raise ProvenanceError(
            f"confidence {confidence} exceeds the {tier.name} ceiling {tier.ceiling}")
