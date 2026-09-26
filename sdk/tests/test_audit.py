"""The auditor side, and the two holes it closes.

Both defects these cover were live and reachable, and one of them built cleanly
with a made-up citation string.
"""
from __future__ import annotations

import os
import shutil

import pytest

from nsjepa_contrib import ContributorConfig, EntryBuilder, GateViolation, assess
from nsjepa_contrib import audit as A
from nsjepa_contrib.config import ConfigError
from nsjepa_contrib.observer import DeploymentObserver
from nsjepa_contrib.validate import Level, validate_entry

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEPLOY = "test-audited-deploy"


@pytest.fixture
def repo(tmp_path):
    """A dictionary checkout with the domain norms, and no attestations yet."""
    for sub in ("domains", "core"):
        shutil.copytree(os.path.join(ROOT, sub), tmp_path / sub)
    return str(tmp_path)


def attestation(**kw):
    base = dict(
        auditor_id="northwind-assurance", auditor_org="Northwind Assurance LLP",
        deployment_id=DEPLOY, vendor_id="acme-civic", category="CAT-02",
        issued_at="2026-09-25",
        findings=[A.AuditFinding(
            term="data_residency_no_training", verdict="not_met",
            method="inspected training manifests for four model revisions")],
        independence=A.Independence(engagement_reference="County PO-2026-4471"),
    )
    base.update(kw)
    return A.Attestation(**base)


def cfg(root, **kw):
    base = dict(vendor_id="acme-civic", product="p", deployment_id=DEPLOY,
                category="CAT-02", dictionary_root=root,
                governance_terms=["independent_governance_audit"])
    base.update(kw)
    return ContributorConfig(**base)


def window():
    obs = DeploymentObserver(DEPLOY, clock=lambda: 0.0)
    for i in range(40):
        obs.record_human_decision(f"c{i}")
        obs.record_effect(f"c{i}")
    return obs.close_window()


# --- hole 1: the tier was forgeable by writing the word ---------------------

def test_vendor_cannot_mint_an_audit_edge(repo):
    """This exact entry built cleanly before the auditor side existed, and gave a
    vendor a positive polarity at 0.85 on its own say-so."""
    b = (EntryBuilder(cfg(repo), lemma="t", domain_sense="s")
         .adverse_to("operator")
         .edge("automated_data_match", "increases", "benefit_takeup_among_eligible",
               confidence=0.85, provenance="audit:we_hired_our_cousin#finding")
         .claim("meaningful_access", "+", because=["e1"]))
    with pytest.raises(GateViolation, match="cites no attestation that exists"):
        b.build()


def test_audit_edge_resolves_when_the_attestation_is_on_file(repo):
    A.write(attestation(), repo)
    entry, report = (
        EntryBuilder(cfg(repo), lemma="t", domain_sense="s")
        .adverse_to("vendor", "resident")
        .audit_edge("fine_tuning_on_resident_text", "prevents", "resident_data_control",
                    attestation_id="audit:northwind-assurance/" + DEPLOY + "/2026-09-25",
                    term="data_residency_no_training", confidence=0.85)
        .claim("data_sovereignty", "-", because=["e1"])
        .build())
    assert entry["causal"]["edges"][0]["provenance"].endswith("#data_residency_no_training")
    assert any("AUDIT RESOLVED" in line for line in report.lines())


def test_self_attestation_is_refused(repo):
    """An attestation whose author is the vendor it assesses is not one."""
    with pytest.raises(A.AttestationError, match="independent of the party"):
        attestation(auditor_id="acme-civic").check()


def test_attestation_filed_by_the_citing_vendor_is_refused(repo):
    att = attestation(auditor_id="acme-civic-audit-division")
    att.vendor_id = "someone-else"
    A.write(att, repo)
    atts = A.load_all(repo)
    with pytest.raises(A.AttestationError, match="which is the vendor citing it"):
        A.resolve(att.provenance_for("data_residency_no_training"), atts,
                  citing_vendor_id="acme-civic-audit-division")


def test_inconclusive_is_not_support(repo):
    A.write(attestation(findings=[A.AuditFinding(
        term="minority_view_preservation", verdict="inconclusive",
        method="no synthesis ran during the engagement period")]), repo)
    b = (EntryBuilder(cfg(repo), lemma="t", domain_sense="s").adverse_to("vendor")
         .audit_edge("a", "causes", "b",
                     attestation_id="audit:northwind-assurance/" + DEPLOY + "/2026-09-25",
                     term="minority_view_preservation", confidence=0.8)
         .claim("fair_treatment", "-", because=["e1"]))
    with pytest.raises(GateViolation, match="INCONCLUSIVE"):
        b.build()


def test_citation_must_name_a_term(repo):
    A.write(attestation(), repo)
    atts = A.load_all(repo)
    with pytest.raises(A.AttestationError, match="no term"):
        A.resolve("audit:northwind-assurance/" + DEPLOY + "/2026-09-25", atts,
                  citing_vendor_id="acme-civic")


def test_receiving_side_repeats_the_resolution(repo):
    """A contribution can arrive by any route, including a hand-edited file."""
    A.write(attestation(), repo)
    entry, _ = (EntryBuilder(cfg(repo), lemma="t", domain_sense="s")
                .adverse_to("vendor")
                .audit_edge("a", "prevents", "b",
                            attestation_id="audit:northwind-assurance/" + DEPLOY
                                           + "/2026-09-25",
                            term="data_residency_no_training", confidence=0.85)
                .claim("data_sovereignty", "-", because=["e1"])
                .build())
    entry["review_by"] = "2027-03-01"
    assert not [f for f in validate_entry(entry, root=repo) if f.level is Level.ERROR]

    entry["causal"]["edges"][0]["provenance"] = "audit:invented/x/2026-01-01#whatever"
    errs = [f for f in validate_entry(entry, root=repo) if f.level is Level.ERROR]
    assert any("cites no attestation" in f.message for f in errs)


# --- hole 2: the term could never be met ------------------------------------

def test_audit_term_is_met_when_an_attestation_is_on_file(repo):
    A.write(attestation(), repo)
    f = {x.term: x for x in assess(cfg(repo), window())}["independent_governance_audit"]
    assert f.status.value == "met"


def test_audit_term_not_met_with_no_attestation(repo):
    f = {x.term: x for x in assess(cfg(repo), window())}["independent_governance_audit"]
    assert f.status.value == "not_met"
    assert "absence is itself the finding" in f.detail


def test_vendor_engaged_assessment_does_not_qualify(repo):
    A.write_unchecked = None  # noqa: F841  (documents that write() would refuse this)
    att = attestation()
    att.independence.engaged_by = "vendor"
    with pytest.raises(A.AttestationError, match="engaged and paid by the issuing body"):
        att.check()


def test_contingent_fee_is_disqualifying(repo):
    att = attestation()
    att.independence.fee_contingent_on_outcome = True
    with pytest.raises(A.AttestationError, match="contingent"):
        att.check()


def test_coi_avoidance_can_finally_be_discharged(repo):
    """Before the auditor side, no code path could discharge this principle:
    the term was observable=False, so assess always returned UNMEASURED, so
    claim_warrant always withdrew it. Declared, wired, and unreachable."""
    A.write(attestation(), repo)
    entry, report = (
        EntryBuilder(cfg(repo), lemma="t", domain_sense="s")
        .adverse_to("vendor", "resident")
        .audit_edge("fine_tuning_on_resident_text", "prevents", "resident_data_control",
                    attestation_id="audit:northwind-assurance/" + DEPLOY + "/2026-09-25",
                    term="data_residency_no_training", confidence=0.85)
        .claim("data_sovereignty", "-", because=["e1"])
        .from_observations(window())
        .claim_warrant("independent_governance_audit")
        .build())
    assert entry["ethics"]["warrants"] == [
        {"claim": "independent_governance_audit", "principle": "coi_avoidance"}]
    assert not report.escalated


# --- the auditor as a submitter ---------------------------------------------

def test_auditor_role_is_not_the_vendor_role(repo):
    a = A.AuditorConfig(auditor_id="northwind-assurance",
                        auditor_org="Northwind Assurance LLP", dictionary_root=repo)
    assert a.role == "auditor"
    assert getattr(ContributorConfig(vendor_id="v", product="p", deployment_id="d",
                                     dictionary_root=repo), "role", "vendor") == "vendor"


def test_auditor_id_must_be_a_slug(repo):
    with pytest.raises(ConfigError, match="lowercase slug"):
        A.AuditorConfig(auditor_id="Northwind Assurance!", auditor_org="x")


def test_finding_requires_a_method(repo):
    with pytest.raises(A.AttestationError, match="no `method`"):
        A.AuditFinding(term="exit_ready_no_lock_in", verdict="met", method="  ")


def test_roundtrip_through_disk(repo):
    p = A.write(attestation(), repo)
    back = A.load(p)
    assert back.id == attestation().id
    assert back.verdict_for("data_residency_no_training") == "not_met"
