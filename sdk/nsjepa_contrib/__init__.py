"""nsjepa_contrib — emit dictionary entries from a deployed government AI system.

A vendor embeds this in a product sold through a procurement vehicle. It does
three things:

  1. OBSERVES whether the governance terms the solicitation actually bought were
     met in production — not at proposal time, and not as a questionnaire.
  2. BUILDS a dictionary entry from those observations, under gates that will
     withdraw a warrant the telemetry does not support.
  3. SUBMITS it to the common repository as a pull request, or as a sealed
     bundle for air-gapped deployments.

The gates are the product. A vendor-authored corpus with no conflict-of-interest
controls would be worth less than nothing, because it would look like evidence.

    from nsjepa_contrib import ContributorConfig, DeploymentObserver, EntryBuilder

    cfg = ContributorConfig(
        vendor_id="acme-civic", product="Acme Benefits Copilot 3.2",
        deployment_id="cuyahoga-jfs-prod", category="CAT-02",
        governance_terms=["human_in_the_loop", "audit_log_and_explainability"],
        dictionary_root="/srv/dictionary",
    )
    obs = DeploymentObserver(cfg.deployment_id)
    ...                                   # wire obs.record_* into the decision path
    log = obs.close_window()

    entry, report = (
        EntryBuilder(cfg, lemma="unreviewed eligibility determination",
                     domain_sense="an eligibility outcome issued with no human "
                                  "having opened the individual case file")
        .from_observations(log)
        .claim_warrant("human_in_the_loop")
        .polarity(due_process="-")
        .balancing_note("...")
        .build()
    )
    print("\\n".join(report.lines()))
"""
from . import audit
from .audit import (Attestation, AttestationError, AuditFinding, AuditorConfig,
                    Independence)
from .builder import BuildReport, EntryBuilder, GateViolation
from .config import (ALL_TERMS, CATEGORIES, GOVERNANCE_TERMS, PROPOSED_TERMS,
                     ContributorConfig)
from .derive import (ComplianceRecord, Status, TermFinding, assess,
                     compliance_record, derive_edges)
from .observer import DeploymentObserver, ObservationLog
from .provenance import TIERS, ProvenanceError
from .vocabulary import Vocabulary
from .version import __version__

__all__ = [
    "ALL_TERMS", "Attestation", "AttestationError", "AuditFinding",
    "AuditorConfig", "Independence", "audit", "BuildReport", "CATEGORIES", "ContributorConfig",
    "DeploymentObserver", "EntryBuilder", "GOVERNANCE_TERMS", "GateViolation",
    "ObservationLog", "PROPOSED_TERMS", "ProvenanceError", "Status", "TIERS",
    "ComplianceRecord", "TermFinding", "Vocabulary", "assess",
    "compliance_record", "derive_edges", "__version__",
]
