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

#: Interstate §3, verbatim in meaning. term id -> (label, principle discharged)
GOVERNANCE_TERMS: dict[str, tuple[str, str]] = {
    "human_in_the_loop":
        ("A person decides on every consequential action.", "due_process"),
    "audit_log_and_explainability":
        ("Every output traceable and reviewable.", "transparency"),
    "exit_ready_no_lock_in":
        ("Open formats; data portable on exit.", "continuity_of_public_capacity"),
    "data_residency_no_training":
        ("No training on resident data; defined hosting.", "data_sovereignty"),
    "bias_and_impact_testing":
        ("Pre-deployment disparate-impact review.", "non_discrimination"),
    "accessibility_508_multilingual":
        ("Section 508 + multilingual delivery.", "meaningful_access"),
}

#: Required by the CAT-01..09 seed; not offered on the form.
PROPOSED_TERMS: dict[str, tuple[str, str]] = {
    "no_deprivation_pending_review":
        ("Benefits continue while a flag is investigated.", "due_process"),
    "source_record_retention":
        ("Source and pre-edit draft retained, diffable against the filed record.",
         "transparency"),
    "appealable_intake_decision":
        ("Every rejection yields a decision that can be appealed.", "due_process"),
    "minority_view_preservation":
        ("Un-collapsed minority positions carried separately from volume.",
         "fair_treatment"),
}

ALL_TERMS = {**GOVERNANCE_TERMS, **PROPOSED_TERMS}

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
        return {ALL_TERMS[t][1]: t for t in self.governance_terms}

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
