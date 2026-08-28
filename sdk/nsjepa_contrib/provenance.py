"""Provenance tiers and the confidence ceilings they impose.

Every causal edge in the dictionary carries a provenance string of the form
``<tier>:<identifier>#<section>``. The tier is not decoration: it caps how much
confidence an edge may assert, and it determines whether the edge counts as
INDEPENDENT of the party submitting it.

The asymmetry in `POSITIVE_CLAIM_REQUIRES_INDEPENDENT` is the conflict-of-
interest control for vendor contributions, and it is the reason this module
exists rather than a bare enum. A vendor reporting that its own deployment
harmed someone is testifying against interest, and is believed. A vendor
reporting that its own deployment worked is testifying in interest, and needs
somebody else to say so too.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    ceiling: float          # max confidence an edge on this tier may assert
    independent: bool       # independent of the contributing vendor?
    measured: bool          # mechanically observed rather than asserted?
    gloss: str


TIERS: dict[str, Tier] = {
    # --- independent, adjudicated -------------------------------------------
    "court": Tier("court", 0.95, True, False,
                  "a judgment or holding of a court"),
    "regulator": Tier("regulator", 0.90, True, False,
                      "a finding by a regulator, inspector general, or auditor general"),
    "legislature": Tier("legislature", 0.85, True, False,
                        "a parliamentary or legislative inquiry finding"),
    # --- independent, unadjudicated -----------------------------------------
    "acad": Tier("acad", 0.85, True, False,
                 "peer-reviewed or working-paper empirical work"),
    "audit": Tier("audit", 0.85, True, True,
                  "a third-party audit of this deployment, commissioned but not performed by the vendor"),
    "press": Tier("press", 0.80, True, False,
                  "reporting by a named outlet with a named author"),
    # --- not independent -----------------------------------------------------
    "runtime": Tier("runtime", 0.85, False, True,
                    "telemetry emitted by nsjepa_contrib from the running deployment"),
    "operator": Tier("operator", 0.75, False, False,
                     "an assertion by the government body operating the system"),
    "inferred": Tier("inferred", 0.70, False, False,
                     "a structural inference, not an observation"),
    "vendor": Tier("vendor", 0.60, False, False,
                   "an assertion by the party that built or sells the system"),
}

#: A positive polarity on any principle needs at least one independent-tier
#: edge somewhere in the entry's support. Adverse polarities do not: nobody
#: files a self-incriminating finding casually, and requiring corroboration
#: before a vendor may report its own failure would suppress exactly the
#: contributions this dictionary is for.
POSITIVE_CLAIM_REQUIRES_INDEPENDENT = True

#: Edges the contributor could not ground must SAY so in the identifier, not
#: quietly carry a low number. `inferred:<what>#needs_grounding` is the marker;
#: `validate` reports every one of them as an open grounding target rather than
#: as an error, because an honestly-marked weak edge is a contribution and a
#: silently-confident one is not.
NEEDS_GROUNDING = "#needs_grounding"


class ProvenanceError(ValueError):
    """Raised when a provenance string is malformed or over-claims."""


def parse(provenance: str) -> tuple[Tier, str, str]:
    """Split ``tier:identifier#section``. Section may be empty."""
    if ":" not in provenance:
        raise ProvenanceError(
            f"provenance {provenance!r} has no tier. Expected '<tier>:<id>#<section>', "
            f"tier one of {sorted(TIERS)}"
        )
    tier_name, rest = provenance.split(":", 1)
    if tier_name not in TIERS:
        raise ProvenanceError(
            f"unknown provenance tier {tier_name!r} in {provenance!r}. "
            f"Known tiers: {sorted(TIERS)}. Do not invent one — if the evidence "
            f"does not fit an existing tier, it is probably 'inferred'."
        )
    identifier, _, section = rest.partition("#")
    if not identifier:
        raise ProvenanceError(f"provenance {provenance!r} has an empty identifier")
    return TIERS[tier_name], identifier, section


def check_confidence(provenance: str, confidence: float) -> None:
    """Raise if an edge asserts more confidence than its tier permits."""
    tier, _, _ = parse(provenance)
    if not 0.0 < confidence <= 1.0:
        raise ProvenanceError(f"confidence {confidence} outside (0, 1]")
    if confidence > tier.ceiling:
        raise ProvenanceError(
            f"confidence {confidence} exceeds the {tier.name} ceiling "
            f"({tier.ceiling}). {tier.gloss}. Either lower the confidence or "
            f"ground the edge on a higher tier — do not relabel the tier."
        )


def shrink_to_sample(ceiling: float, n: int, prior: int = 30) -> float:
    """Confidence for an edge derived from `n` runtime observations.

    Shrinks the tier ceiling toward zero for small samples: ``ceiling * n/(n+prior)``.
    Deliberately crude and deliberately visible. It is a placeholder for a
    proper interval and is documented as such in the README — a deployment
    reporting one adverse event should not emit a 0.85 edge, and this is the
    smallest thing that prevents it. Replace with a Wilson lower bound before
    any of this feeds an institution-level aggregation.
    """
    if n <= 0:
        return 0.0
    return round(ceiling * n / (n + prior), 2)
