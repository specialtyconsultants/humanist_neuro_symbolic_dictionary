"""The gates are the product, so they are what the tests cover.

Run from the sdk/ directory with the dictionary checkout two levels up:
    pytest -q
"""
from __future__ import annotations

import os

import pytest

from nsjepa_contrib import (ContributorConfig, DeploymentObserver, EntryBuilder,
                            GateViolation, Status, assess, compliance_record)
from nsjepa_contrib.provenance import ProvenanceError, check_confidence, shrink_to_sample
from nsjepa_contrib.validate import Level, validate_entry
from nsjepa_contrib.vocabulary import Vocabulary

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cfg(**kw):
    base = dict(vendor_id="acme-civic", product="Acme Benefits Copilot 3.2",
                deployment_id="test-deploy", category="CAT-02",
                governance_terms=["human_in_the_loop"], dictionary_root=ROOT)
    base.update(kw)
    return ContributorConfig(**base)


def observer_with(*, actions, reviewed_before):
    """A window where `reviewed_before` of `actions` were decided BEFORE effect.

    The caller never tells the observer which came first. It records the two
    events in the order they happened and the ordering is derived, which is the
    point of the events-not-conclusions change: an integrator can still decline
    to instrument a path, and can no longer get the ordering wrong by accident.
    """
    obs = DeploymentObserver("test-deploy", clock=lambda: 0.0)
    for i in range(actions):
        ref = f"case-{i}"
        if i < reviewed_before:
            obs.record_human_decision(ref)
            obs.record_effect(ref)
        else:
            obs.record_effect(ref)
            obs.record_human_decision(ref)
    return obs.close_window()


# --- provenance -------------------------------------------------------------

def test_tier_caps_confidence():
    check_confidence("court:abc#holding", 0.95)
    with pytest.raises(ProvenanceError, match="vendor ceiling"):
        check_confidence("vendor:acme#claim", 0.90)


def test_unknown_tier_is_refused():
    with pytest.raises(ProvenanceError, match="unknown provenance tier"):
        check_confidence("marketing:acme#deck", 0.5)


def test_small_samples_shrink():
    assert shrink_to_sample(0.85, 1) < 0.1
    assert shrink_to_sample(0.85, 1000) > 0.8


# --- gate 2: conflict of interest -------------------------------------------

def _builder(adverse=("vendor",), **kw):
    b = EntryBuilder(cfg(**kw), lemma="test lemma",
                     domain_sense="a test sense").intervention("do(x) lowers y")
    return b.adverse_to(*adverse) if adverse else b


def test_positive_polarity_needs_independent_tier():
    b = (_builder()
         .edge("automated_data_match", "increases", "benefit_takeup_among_eligible",
               confidence=0.6, provenance="vendor:acme#internal")
         .claim("meaningful_access", "+", because=["e1"]))
    with pytest.raises(GateViolation, match="needs .*independent support"):
        b.build()


def test_adverse_to_submitter_needs_no_corroboration():
    entry, _ = (_builder()
                .edge("suspension_pending_investigation", "causes",
                      "deprivation_before_adjudication",
                      confidence=0.6, provenance="vendor:acme#incident")
                .claim("due_process", "-", because=["e1"])
                .build())
    assert entry["ethics"]["principle_polarity"]["due_process"] == {
        "polarity": "-", "supported_by": ["e1"]}


def test_negative_finding_aimed_at_someone_else_needs_corroboration():
    """The hole the sign-based rule had.

    A vendor reporting "the county configured us to deprive first" files a
    NEGATIVE finding that is adverse to the operator and favourable to the
    vendor. Under a rule stated on the sign of the claim it sails through at
    face value, and it is exactly the contribution a vendor has an incentive to
    file.
    """
    b = (_builder(adverse=("operator",))
         .edge("suspension_pending_investigation", "causes",
               "deprivation_before_adjudication",
               confidence=0.6, provenance="vendor:acme#incident")
         .claim("due_process", "-", because=["e1"]))
    with pytest.raises(GateViolation, match="not adverse to the submitter"):
        b.build()


def test_adverse_to_must_be_declared():
    b = (_builder(adverse=None)
         .edge("a", "causes", "b", confidence=0.5, provenance="inferred:x#structural")
         .claim("due_process", "-", because=["e1"]))
    with pytest.raises(GateViolation, match="does not declare"):
        b.build()


def test_polarity_with_no_supporting_edge_is_refused():
    """Type E used to be the only footnote a reader had to take on faith."""
    b = (_builder()
         .edge("a", "causes", "b", confidence=0.5, provenance="inferred:x#structural")
         .polarity(due_process="-"))
    with pytest.raises(GateViolation, match="names no supporting"):
        b.build()


def test_analytic_tier_cannot_support_a_positive_polarity():
    """Independent, and useless as evidence that anything worked. Without the
    exclusion a contributor could define its way to a favourable footnote."""
    b = (_builder()
         .edge("adjudicated_decision", "enables", "informed_recourse",
               confidence=0.9, provenance="analytic:appeal_predicate#definitional")
         .claim("due_process", "+", because=["e1"]))
    with pytest.raises(GateViolation, match="analytic"):
        b.build()


# --- gate 3: warrants are earned --------------------------------------------

def test_warrant_withdrawn_when_telemetry_contradicts_it():
    log = observer_with(actions=100, reviewed_before=40)
    entry, report = (_builder()
                     .from_observations(log)
                     .claim_warrant("human_in_the_loop")
                     .build())
    assert entry["ethics"]["warrants"] == []
    assert report.escalated
    assert any(t == "human_in_the_loop" for t, _ in report.withdrawn_warrants)


def test_warrant_survives_when_telemetry_supports_it():
    log = observer_with(actions=100, reviewed_before=100)
    entry, report = (_builder()
                     .from_observations(log)
                     # a fully compliant window derives NO edges — see
                     # test_compliance_alone_is_not_an_entry — so the entry has
                     # to stand on something the deployment did not measure
                     .edge("burden_shift_to_the_affected_person", "prevents",
                           "informed_recourse", confidence=0.7,
                           provenance="acad:some_study#finding")
                     .claim_warrant("human_in_the_loop")
                     .claim("due_process", "-", because=["e1"])
                     .build())
    assert entry["ethics"]["warrants"] == [
        {"claim": "human_in_the_loop", "principle": "due_process"}]
    assert not report.escalated


def test_compliance_alone_is_not_an_entry():
    """A deployment that met every term has produced a compliance record, not a
    claim about the world. `derive_edges` emits nothing and the builder refuses,
    which is the intended shape: the dictionary is for what institutions do to
    people, and an attestation that nothing was done to anyone is not an entry."""
    log = observer_with(actions=100, reviewed_before=100)
    b = _builder().from_observations(log).claim_warrant("human_in_the_loop")
    with pytest.raises(GateViolation, match="no causal edges"):
        b.build()


def test_unknown_warrant_claim_is_refused():
    b = (_builder(governance_terms=["human_in_the_loop"])
         .edge("a", "causes", "b", confidence=0.5, provenance="inferred:x#structural"))
    b._claimed_warrants.append("not_a_real_term")
    with pytest.raises(GateViolation, match="unknown governance term"):
        b.build()


# --- gate 4: ratification and vocabulary ------------------------------------

def test_contributor_cannot_ratify_itself():
    entry, _ = (_builder()
                .edge("suspension_pending_investigation", "causes",
                      "deprivation_before_adjudication",
                      confidence=0.5, provenance="inferred:x#structural")
                .claim("due_process", "-", because=["e1"])
                .build())
    assert entry["status"] == "provisional"
    entry["status"] = "ratified"
    findings = validate_entry(entry, root=ROOT)
    assert any(f.level is Level.ERROR and "provisional" in f.message for f in findings)


def test_aliases_resolve_to_the_canonical_node():
    v = Vocabulary.load("gov_procurement", ROOT)
    for alias in ("reliance_defense", "right_of_appeal", "contestation_of_grounds"):
        assert v.resolve(alias).canonical == "informed_recourse"


def test_time_index_survives_resolution():
    v = Vocabulary.load("gov_procurement", ROOT)
    assert v.resolve("informed_recourse@t1").canonical == "informed_recourse@t1"


def test_unregistered_node_warns_but_does_not_block():
    entry, report = (_builder()
                     .edge("some_node_nobody_registered", "causes",
                           "deprivation_before_adjudication",
                           confidence=0.5, provenance="inferred:x#structural")
                     .claim("due_process", "-", because=["e1"])
                     .build())
    assert entry["causal"]["edges"]
    assert ("some_node_nobody_registered", "") in [
        (n, s) for n, s in report.unregistered_nodes]


# --- assessment -------------------------------------------------------------

def test_unclaimed_terms_are_not_failures():
    findings = {f.term: f for f in assess(cfg(governance_terms=[]),
                                          observer_with(actions=10, reviewed_before=0))}
    assert findings["human_in_the_loop"].status is Status.NOT_CLAIMED
    assert findings["exit_ready_no_lock_in"].status is Status.NOT_CLAIMED


def test_claimed_but_uninstrumented_is_unmeasured_not_met():
    log = observer_with(actions=0, reviewed_before=0)
    findings = {f.term: f for f in assess(cfg(), log)}
    assert findings["human_in_the_loop"].status is Status.UNMEASURED


def test_terms_unobservable_from_inside_are_never_met():
    log = observer_with(actions=10, reviewed_before=10)
    findings = {f.term: f
                for f in assess(cfg(governance_terms=["data_residency_no_training"]), log)}
    assert findings["data_residency_no_training"].status is Status.UNMEASURED


# --- privacy ----------------------------------------------------------------

def test_observation_log_carries_no_subject_identifiers():
    obs = DeploymentObserver("test-deploy", clock=lambda: 0.0)
    obs.record_deprivation("resident-12345")
    obs.record_review_completed("resident-12345")
    log = obs.close_window()
    assert "resident-12345" not in repr(log.as_dict())
    assert log.deprivations == 1


# --- the denominator --------------------------------------------------------

def test_compliance_record_exists_even_with_no_entry():
    """Survivorship control.

    A compliant window derives no edges and so no entry. Without a record that
    the window happened at all, the corpus fills only with failures and has no
    denominator, and the first person to compute "X% of CAT-02 deployments
    deprive before review" over it gets a number that means nothing and looks
    authoritative.
    """
    c = cfg()
    log = observer_with(actions=100, reviewed_before=100)
    rec = compliance_record(c, log, assess(c, log), produced_entry=False)
    assert rec.produced_entry is False
    assert any(f["term"] == "human_in_the_loop" and f["status"] == "met"
               for f in rec.findings)
    assert "edges" not in rec.as_dict()      # a denominator, not an entry


def test_compliance_record_omits_unclaimed_terms():
    c = cfg(governance_terms=["human_in_the_loop"])
    log = observer_with(actions=10, reviewed_before=10)
    rec = compliance_record(c, log, assess(c, log), produced_entry=False)
    assert {f["term"] for f in rec.findings} == {"human_in_the_loop"}


# --- the forcing function ---------------------------------------------------

def test_telemetry_term_not_met_when_nothing_is_wired_in():
    """An SDK installed but wired to nothing satisfies the term on paper and
    reports nothing, which is the failure the term exists to prevent — so it is
    NOT_MET rather than UNMEASURED."""
    c = cfg(governance_terms=["verifiable_governance_telemetry"])
    findings = {f.term: f for f in assess(c, observer_with(actions=0, reviewed_before=0))}
    assert findings["verifiable_governance_telemetry"].status is Status.NOT_MET


def test_telemetry_term_met_when_probes_fired():
    c = cfg(governance_terms=["verifiable_governance_telemetry"])
    findings = {f.term: f for f in assess(c, observer_with(actions=25, reviewed_before=25))}
    assert findings["verifiable_governance_telemetry"].status is Status.MET


def test_audit_term_is_never_self_measurable():
    """No amount of vendor activity moves this term.

    It used to be permanently UNMEASURED, which meant `claim_warrant` always
    withdrew it and `coi_avoidance` could not be discharged by any code path at
    all. It is now NOT_MET when nothing is on file — the absence is a finding,
    not a silence — and only an attestation filed by somebody else makes it MET.
    See tests/test_audit.py for that half; here the point is that a busy,
    fully-compliant window does not help.
    """
    c = cfg(governance_terms=["independent_governance_audit"])
    findings = {f.term: f for f in assess(c, observer_with(actions=25, reviewed_before=25))}
    f = findings["independent_governance_audit"]
    assert f.status is Status.NOT_MET
    assert "a vendor cannot produce this evidence" in f.detail.lower()


# --- retirement -------------------------------------------------------------

def _built_entry():
    entry, _ = (_builder()
                .edge("a", "causes", "b", confidence=0.5, provenance="inferred:x#s")
                .claim("due_process", "-", because=["e1"])
                .build())
    return entry


def test_retired_entry_needs_a_reason():
    entry = _built_entry()
    entry["status"] = "retired"
    findings = validate_entry(entry, root=ROOT)
    assert any(f.level is Level.ERROR and "retired_reason" in f.message for f in findings)


def test_superseded_entry_must_be_retired():
    entry = _built_entry()
    entry["superseded_by"] = "gpr:something#other/deploy"
    findings = validate_entry(entry, root=ROOT)
    assert any(f.level is Level.ERROR and "retired" in f.message for f in findings)


def test_provisional_contribution_needs_a_review_date():
    findings = validate_entry(_built_entry(), root=ROOT)
    assert any(f.level is Level.ERROR and "review_by" in f.message for f in findings)
