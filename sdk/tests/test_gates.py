"""The gates are the product, so they are what the tests cover.

Run from the sdk/ directory with the dictionary checkout two levels up:
    pytest -q
"""
from __future__ import annotations

import os

import pytest

from nsjepa_contrib import (ContributorConfig, DeploymentObserver, EntryBuilder,
                            GateViolation, Status, assess)
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
    obs = DeploymentObserver("test-deploy", clock=lambda: 0.0)
    for i in range(actions):
        obs.record_action(human_reviewed=True, review_preceded_effect=i < reviewed_before)
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

def _builder(**kw):
    return EntryBuilder(cfg(**kw), lemma="test lemma",
                        domain_sense="a test sense").intervention("do(x) lowers y")


def test_positive_polarity_needs_independent_tier():
    b = (_builder()
         .edge("automated_data_match", "increases", "benefit_takeup_among_eligible",
               confidence=0.6, provenance="vendor:acme#internal")
         .polarity(meaningful_access="+"))
    with pytest.raises(GateViolation, match="no independent-tier edge"):
        b.build()


def test_adverse_polarity_needs_no_corroboration():
    entry, _ = (_builder()
                .edge("suspension_pending_investigation", "causes",
                      "deprivation_before_adjudication",
                      confidence=0.6, provenance="vendor:acme#incident")
                .polarity(due_process="-")
                .build())
    assert entry["ethics"]["principle_polarity"] == {"due_process": "-"}


# --- gate 3: warrants are earned --------------------------------------------

def test_warrant_withdrawn_when_telemetry_contradicts_it():
    log = observer_with(actions=100, reviewed_before=40)
    entry, report = (_builder()
                     .from_observations(log)
                     .claim_warrant("human_in_the_loop")
                     .polarity(due_process="-")
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
                     .polarity(due_process="-")
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
                .polarity(due_process="-")
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
                     .polarity(due_process="-")
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
