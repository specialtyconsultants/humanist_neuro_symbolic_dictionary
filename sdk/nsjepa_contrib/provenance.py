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
    #: May an edge on this tier be the independent support for a POSITIVE
    #: polarity? False for `analytic`, which is independent in the sense that
    #: any reader can check it and useless as evidence that anything worked —
    #: without this flag a contributor could define its way to a favourable
    #: ethics footnote.
    can_support_positive: bool = True


TIERS: dict[str, Tier] = {
    # --- analytic -------------------------------------------------------------
    # True from the definitions, not from the evidence. `inferred` was carrying
    # both of these and its 0.70 ceiling is right for one and wrong for the
    # other: "an application rejected at intake produces no adjudicated
    # decision" is not a weak empirical guess, it is what the entry's own
    # domain_sense says, and no amount of fieldwork would move it.
    #
    # The rule, and it is checkable by a reviewer without leaving the file: an
    # analytic edge must follow from this entry's `domain_sense` or from a
    # doctrinal premise named in the section. Anything requiring an observation
    # about the world is `inferred` at 0.70, however obvious it feels.
    "analytic": Tier("analytic", 0.95, True, False,
                     "true by the definitions in this entry, or by a named doctrinal "
                     "premise; evidence can neither raise nor lower it",
                     can_support_positive=False),
    # --- independent, adjudicated -------------------------------------------
    "court": Tier("court", 0.95, True, False,
                  "a judgment or holding of a court"),
    "regulator": Tier("regulator", 0.90, True, False,
                      "a finding by a regulator, inspector general, or auditor general"),
    "legislature": Tier("legislature", 0.85, True, False,
                        "a parliamentary or legislative inquiry finding"),
    # --- independent, documentary -------------------------------------------
    "standards": Tier("standards", 0.90, True, False,
                      "a published standard or list maintained by a recognised body "
                      "(ISMP high-alert list, NIST AI RMF, Section 508)"),
    "instrument": Tier("instrument", 0.90, True, False,
                       "the text of the procurement instrument or contract under "
                       "analysis. Documentary: it establishes what the instrument "
                       "SAYS, never that the thing it describes works"),
    # --- independent, unadjudicated -----------------------------------------
    "acad": Tier("acad", 0.85, True, False,
                 "peer-reviewed or working-paper empirical work"),
    # An audit is a human judgement, not a mechanical measurement — `measured`
    # was True here and that was simply wrong. It reaches the corpus only via an
    # attestation filed separately by the assessor; see nsjepa_contrib.audit for
    # why the tier cannot be claimed by writing the word.
    "audit": Tier("audit", 0.85, True, False,
                  "a third-party assessment of this deployment, engaged and paid by "
                  "the issuing body, filed by the assessor under contrib/audits/"),
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
