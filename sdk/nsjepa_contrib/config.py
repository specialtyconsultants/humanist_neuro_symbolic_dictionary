"""Deployment identity and the governance terms the solicitation actually bought.

`GOVERNANCE_TERMS` is a transcription of Interstate §3 "Governance posture".
Those six checkboxes are the only place in the solicitation instrument where a
claim binds to a principle and becomes binding on a bidder before a price is
named — which makes them, structurally, warrant claims. `norms/rules.yaml` in
the dictionary carries them as exactly that, tagged `source: "interstate:s3"`.

The four `PROPOSED_TERMS` have no checkbox on the form today. Each was forced by
an entry whose harm none of the six discharge. A deployment may declare them
voluntarily; the SDK will hold it to them the same way.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import NamedTuple

class Term(NamedTuple):
    """A governance term, and whether anything can check it.

    `observable` is the field that matters and the one the form has no column
    for. A term the vendor cannot observe from inside its own product is not
    thereby met or unmet — it is UNMEASURED, and the SDK says so rather than
    converting an assertion into evidence by restating it.
    """
    label: str
    principle: str
    observable: bool = True
    source: str = "interstate:s3"


#: Interstate §3, verbatim in meaning.
GOVERNANCE_TERMS: dict[str, Term] = {
    "human_in_the_loop": Term(
        "A person decides on every consequential action.", "due_process"),
    "audit_log_and_explainability": Term(
        "Every output traceable and reviewable.", "transparency"),
    "exit_ready_no_lock_in": Term(
        "Open formats; data portable on exit.", "continuity_of_public_capacity",
        observable=False),
    "data_residency_no_training": Term(
        "No training on resident data; defined hosting.", "data_sovereignty",
        observable=False),
    "bias_and_impact_testing": Term(
        "Pre-deployment disparate-impact review.", "non_discrimination"),
    "accessibility_508_multilingual": Term(
        "Section 508 + multilingual delivery.", "meaningful_access"),
}

#: Required by the CAT-01..09 seed; no checkbox on the form.
PROPOSED_TERMS: dict[str, Term] = {
    "no_deprivation_pending_review": Term(
        "Benefits continue while a flag is investigated.", "due_process",
        source="proposed"),
    "source_record_retention": Term(
        "Source and pre-edit draft retained, diffable against the filed record.",
        "transparency", source="proposed"),
    "appealable_intake_decision": Term(
        "Every rejection yields a decision that can be appealed.", "due_process",
        source="proposed"),
    "minority_view_preservation": Term(
        "Un-collapsed minority positions carried separately from volume.",
        "fair_treatment", observable=False, source="proposed"),

    # ---- the forcing function ------------------------------------------------
    # Everything else in this package is well-formed and, absent a term that
    # buys it, nobody installs it: a vendor ships something capable of
    # withdrawing its own compliance claim only when not shipping it costs more.
    # This is the term that makes that true, and it is the only one on any of
    # these lists that is verified by mechanism rather than by assertion.
    #
    # It also does something for the buyer none of the six do. The other terms
    # are checkable at proposal time and unfalsifiable afterwards; this one is
    # continuous, and every failure in the CAT-01..09 seed happened after award.
    "verifiable_governance_telemetry": Term(
        "The system emits signed, continuous evidence of whether the other "
        "governance terms were met in production, on a schedule, to the issuing "
        "body and to a common repository.",
        "transparency", source="proposed"),

    # ---- the other half of the same argument ---------------------------------
    # Telemetry cannot reach the terms marked observable=False, and no amount of
    # vendor instrumentation ever will: they are facts about corporate conduct,
    # hosting, and what was NOT in a synthesis. Roughly half the governance
    # surface the form sells cannot be verified by the party being asked to
    # verify it. That gap closes with money, not with code — an independent
    # assessor, priced as its own CLIN, whose findings enter at the `audit:`
    # tier and therefore count as independent support where a vendor's do not.
    "independent_governance_audit": Term(
        "A third-party assessor, engaged and paid by the issuing body rather "
        "than the vendor, verifies the terms no runtime probe can reach and "
        "files findings at the audit tier.",
        "coi_avoidance", observable=False, source="proposed"),
}

ALL_TERMS: dict[str, Term] = {**GOVERNANCE_TERMS, **PROPOSED_TERMS}

#: Terms no probe inside a vendor product can honestly reach.
UNOBSERVABLE = tuple(t for t, spec in ALL_TERMS.items() if not spec.observable)

CATEGORIES = {
    "CAT-01": "Resident service assistants",
    "CAT-02": "Proactive eligibility & benefits",
    "CAT-03": "Plain-language & translation",
    "CAT-04": "Predictive infrastructure",
    "CAT-05": "Document & records processing",
    "CAT-06": "Public-comment synthesis",
    "CAT-07": "Fraud & anomaly detection",
    "CAT-08": "Permitting & case workflow",
    "CAT-09": "Custom — define your own",
}


class ConfigError(ValueError):
    pass


@dataclass
class ContributorConfig:
    """Everything the SDK needs to attribute a contribution and score it.

    `vendor_id` is not cosmetic. It selects the provenance tier applied to
    self-reported edges and it is what the conflict-of-interest gate keys on.
    Contributions are never anonymous.
    """
    vendor_id: str                      # e.g. "acme-civic" — stable, lowercase
    product: str                        # product name and version
    deployment_id: str                  # opaque, stable per installation
    domain: str = "gov_procurement"
    category: str = "CAT-09"
    issuing_body: str = ""              # the government body, if disclosable
    docket_reference: str = ""          # e.g. "IN-2026-··-16312"
    governance_terms: list[str] = field(default_factory=list)
    dictionary_root: str = "."          # checkout of the dictionary repo
    offline: bool = False               # air-gapped: bundle instead of submit

    def __post_init__(self) -> None:
        if not self.vendor_id or self.vendor_id != self.vendor_id.strip().lower():
            raise ConfigError("vendor_id must be a stable lowercase identifier")
        if self.category not in CATEGORIES:
            raise ConfigError(f"unknown category {self.category!r}; one of {sorted(CATEGORIES)}")
        unknown = set(self.governance_terms) - set(ALL_TERMS)
        if unknown:
            raise ConfigError(
                f"unknown governance terms {sorted(unknown)}. Selectable today: "
                f"{sorted(GOVERNANCE_TERMS)}. Additionally declarable: {sorted(PROPOSED_TERMS)}."
            )

    # -- derived ------------------------------------------------------------
    @property
    def claimed_principles(self) -> dict[str, str]:
        """principle -> the term claimed to discharge it."""
        return {ALL_TERMS[t].principle: t for t in self.governance_terms}

    def selected(self, term: str) -> bool:
        return term in self.governance_terms

    # -- io -----------------------------------------------------------------
    @classmethod
    def load(cls, path: str = "nsjepa_contrib.json") -> "ContributorConfig":
        if not os.path.exists(path):
            raise ConfigError(
                f"no config at {path}. Run `nsjepa-contrib init` to write one."
            )
        return cls(**json.load(open(path, encoding="utf-8")))

    def save(self, path: str = "nsjepa_contrib.json") -> str:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)
            fh.write("\n")
        return path
