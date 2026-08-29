"""Turn observations into warrants that can be withdrawn, and edges that can be cited.

The design commitment here is that a governance term is DISCHARGED BY EVIDENCE,
not by having been ticked. A vendor declares `human_in_the_loop` in its config
because the solicitation required it; this module then reads the telemetry and,
if the decisions did not in fact precede the effects, refuses to emit the
warrant and records why. The entry that ships is therefore capable of
contradicting the contract it was produced under, which is the only reason
anyone outside the vendor should find it interesting.

`assess` never raises. It returns findings, including `UNMEASURED`, which is a
distinct and honest state: the term may well be met, and this deployment did not
instrument it. Silence is reported as silence.
"""
from __future__ import annotations

import time as _time
from dataclasses import dataclass, field
from enum import Enum

from .config import ALL_TERMS, ContributorConfig
from .observer import ObservationLog
from .provenance import TIERS, shrink_to_sample

#: Below this, a rate-based term is reported NOT_MET rather than MET. It is not
#: 1.0 because no production system achieves 1.0 and a threshold nobody can meet
#: gets the SDK switched off. It is high because these are the terms the
#: solicitation actually paid for. Overridable per deployment, and the override
#: is recorded in the entry.
DEFAULT_THRESHOLD = 0.98

#: An impact test older than this is stale. Every entry with a feedback loop
#: degrades after deployment, so a pre-deployment test is a fact about t=0 and
#: not about now.
IMPACT_TEST_MAX_AGE_SECONDS = 180 * 24 * 3600

UNOBSERVABLE_DETAIL = (
    "not observable from inside the product, and no amount of vendor "
    "instrumentation will make it so. Needs `independent_governance_audit` — a "
    "third-party assessor engaged and paid by the issuing body, whose findings "
    "enter at the `audit:` tier. The SDK will not convert an assertion into "
    "evidence by restating it."
)


class Status(str, Enum):
    MET = "met"
    NOT_MET = "not_met"
    UNMEASURED = "unmeasured"
    NOT_CLAIMED = "not_claimed"


@dataclass
class TermFinding:
    term: str
    principle: str
    status: Status
    observed: float | None = None      # the measured rate, where there is one
    n: int = 0                         # sample size behind it
    detail: str = ""

    @property
    def discharges(self) -> bool:
        return self.status is Status.MET


@dataclass
class ComplianceRecord:
    """A window that ran, whether or not it produced an entry.

    THE DENOMINATOR. A fully compliant deployment derives no edges and so no
    entry — correct, because meeting your terms is a compliance fact and not a
    claim about the world. The consequence is survivorship: without this record
    the corpus fills only with failures and has no denominator, and the first
    person to compute "X% of CAT-02 deployments deprive before review" over it
    gets a number that means nothing and looks authoritative.

    These are cheap, they carry no causal claims, and they are the difference
    between an anecdote pile and a rate. They cannot be retrofitted, because by
    then the windows are gone.
    """
    deployment_id: str
    vendor_id: str
    category: str
    domain: str
    window_started_at: float
    window_ended_at: float
    terms_claimed: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    produced_entry: bool = False
    sdk_version: str = ""

    @property
    def window_id(self) -> str:
        return f"{int(self.window_started_at)}-{int(self.window_ended_at)}"

    def as_dict(self) -> dict:
        return {"kind": "compliance_record", "window_id": self.window_id,
                "deployment_id": self.deployment_id, "vendor_id": self.vendor_id,
                "category": self.category, "domain": self.domain,
                "window_started_at": self.window_started_at,
                "window_ended_at": self.window_ended_at,
                "terms_claimed": self.terms_claimed, "findings": self.findings,
                "produced_entry": self.produced_entry,
                "sdk_version": self.sdk_version}


def _rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def assess(config: ContributorConfig, log: ObservationLog,
           threshold: float = DEFAULT_THRESHOLD,
           now: float | None = None) -> list[TermFinding]:
    """Score every term the deployment claimed against what was observed."""
    findings: list[TermFinding] = []

    def add(term, status, observed=None, n=0, detail=""):
        findings.append(
            TermFinding(term, ALL_TERMS[term].principle, status, observed, n, detail))

    def rate_term(term, num, den, detail_met, detail_bad):
        if not config.selected(term):
            return add(term, Status.NOT_CLAIMED)
        r = _rate(num, den)
        if r is None:
            return add(term, Status.UNMEASURED, None, 0,
                       "claimed, and the probe recorded no events in this window")
        add(term, Status.MET if r >= threshold else Status.NOT_MET, round(r, 4), den,
            detail_met if r >= threshold else detail_bad)

    # The numerator is decisions that PRECEDED their effect. A decision taken
    # after the effect and an effect nobody ever decided both fail, and they are
    # counted separately so the entry can say which failure this was.
    rate_term("human_in_the_loop",
              log.decided_before_effect, log.consequential_actions,
              "a person decided before the effect on every consequential action observed",
              f"{log.decided_after_effect} action(s) were decided only after taking "
              f"effect and {log.never_decided} were never decided at all; the term "
              f"fixes THAT a person decides, and this deployment shows it was not WHEN")

    rate_term("no_deprivation_pending_review",
              log.reviewed_before_deprivation, log.deprivations,
              "no deprivation preceded its review",
              f"{log.reviewed_after_deprivation} deprivation(s) were reviewed only "
              f"afterwards and {log.never_reviewed} not at all; the reviewer then "
              f"determines whether to refund, and a refund later is not the same good")

    rate_term("source_record_retention",
              log.records_with_draft_retained, log.generated_records,
              "pre-edit drafts retained and diffable against the filed record",
              "generated records entered the file with no retained draft; the fact "
              "that a model was used survives, the evidence of what it wrote does not")

    rate_term("appealable_intake_decision",
              log.intake_rejections_appealable, log.intake_rejections,
              "every intake rejection produced an appealable decision",
              "intake rejections produced nothing to appeal, and so left the "
              "cycle-time denominator rather than appearing in it as a failure")

    # accessibility: delivery is easy, verification is the claim
    if not config.selected("accessibility_508_multilingual"):
        add("accessibility_508_multilingual", Status.NOT_CLAIMED)
    else:
        delivered = sum(log.outputs_by_locale.values())
        verified = sum(log.outputs_verified_by_locale.values())
        unverified = sorted(set(log.outputs_by_locale) - set(log.outputs_verified_by_locale))
        if delivered == 0:
            add("accessibility_508_multilingual", Status.UNMEASURED)
        else:
            r = verified / delivered
            add("accessibility_508_multilingual",
                Status.MET if r >= threshold else Status.NOT_MET, round(r, 4), delivered,
                "output verified by a competent speaker in every locale delivered"
                if r >= threshold else
                f"delivered unverified in {unverified}; correctness in a language "
                f"nobody at the issuing body reads produces no error signal, so the "
                f"failure is silent by construction")

    # bias testing: a date, not a rate, and it goes stale
    if not config.selected("bias_and_impact_testing"):
        add("bias_and_impact_testing", Status.NOT_CLAIMED)
    elif not log.last_impact_test_at:
        add("bias_and_impact_testing", Status.UNMEASURED, detail="no impact test recorded")
    else:
        age = (now if now is not None else _time.time()) - log.last_impact_test_at
        fresh = age <= IMPACT_TEST_MAX_AGE_SECONDS
        add("bias_and_impact_testing", Status.MET if fresh else Status.NOT_MET, None, 0,
            f"impact test {int(age // 86400)}d old" + ("" if fresh else
            "; a pre-deployment test is a fact about t=0, and a model that reshapes "
            "its own next training set produces its disparity after t=0"))

    # The forcing function. It is the one term whose evidence is the act of
    # producing evidence — and the one failure mode worth catching is an SDK
    # that is installed, declared, and wired to nothing.
    if not config.selected("verifiable_governance_telemetry"):
        add("verifiable_governance_telemetry", Status.NOT_CLAIMED)
    else:
        events = (log.consequential_actions + log.deprivations
                  + log.generated_records + log.intake_rejections
                  + sum(log.outputs_by_locale.values()))
        add("verifiable_governance_telemetry",
            Status.MET if events else Status.NOT_MET, None, events,
            "a closed observation window was produced and submitted" if events else
            "claimed, and no probe in this deployment recorded a single event in "
            "this window. An SDK installed but not wired in satisfies the term on "
            "paper and reports nothing, which is the failure this term exists to "
            "prevent — so it is NOT_MET rather than UNMEASURED")

    # Whatever is left has no probe above. Two very different reasons for that,
    # and collapsing them would be the kind of quiet imprecision this module
    # exists to avoid: a term nothing CAN reach is a permanent gap that costs
    # money to close, and a term this SDK merely does not implement yet is a
    # backlog item.
    for term, spec in ALL_TERMS.items():
        if any(f.term == term for f in findings):
            continue
        if not config.selected(term):
            add(term, Status.NOT_CLAIMED)
        elif not spec.observable:
            add(term, Status.UNMEASURED, detail=UNOBSERVABLE_DETAIL)
        else:
            add(term, Status.UNMEASURED,
                detail="observable in principle, and this SDK has no probe for it "
                       "yet. Not a finding about the deployment — a gap in the "
                       "instrumentation, and it belongs in the SDK rather than in "
                       "an entry")
    return findings


def compliance_record(config: ContributorConfig, log: ObservationLog,
                      findings: list[TermFinding], *, produced_entry: bool,
                      sdk_version: str = "") -> ComplianceRecord:
    """The denominator record for one window. Emit this every window, always."""
    return ComplianceRecord(
        deployment_id=config.deployment_id, vendor_id=config.vendor_id,
        category=config.category, domain=config.domain,
        window_started_at=log.window_started_at, window_ended_at=log.window_ended_at,
        terms_claimed=sorted(config.governance_terms),
        findings=[{"term": f.term, "status": f.status.value,
                   "observed": f.observed, "n": f.n}
                  for f in findings if f.status is not Status.NOT_CLAIMED],
        produced_entry=produced_entry, sdk_version=sdk_version,
    )


def derive_edges(config: ContributorConfig, log: ObservationLog,
                 findings: list[TermFinding]) -> list[dict]:
    """Runtime-grounded causal edges, confidence shrunk to sample size.

    Only ADVERSE findings become edges. A deployment that met its terms has
    produced a compliance record — see `compliance_record`, emitted either way —
    and not a claim about the world. The dictionary is for what institutions do
    to people; an attestation that nothing was done to anyone is a denominator,
    not an entry.
    """
    ceiling = TIERS["runtime"].ceiling
    dep = f"runtime:{config.deployment_id}"
    edges: list[dict] = []

    def edge(cause, relation, effect, n, section):
        edges.append({"id": f"e{len(edges) + 1}",
                      "cause": cause, "relation": relation, "effect": effect,
                      "confidence": shrink_to_sample(ceiling, n),
                      "provenance": f"{dep}#{section}"})

    by_term = {f.term: f for f in findings}

    def failed(term):
        f = by_term.get(term)
        return f is not None and f.status is Status.NOT_MET

    if failed("no_deprivation_pending_review"):
        n = log.reviewed_after_deprivation + log.never_reviewed
        edge("suspension_pending_investigation", "causes",
             "deprivation_before_adjudication", n, "deprivation_before_review")
        edge("deprivation_before_adjudication", "prevents", "informed_recourse", n,
             "recourse")

    if failed("human_in_the_loop"):
        n = log.decided_after_effect + log.never_decided
        edge("automated_action_without_prior_human_decision", "causes",
             "deprivation_before_adjudication", n, "hitl_ordering")

    if failed("source_record_retention"):
        n = log.generated_records - log.records_with_draft_retained
        edge("draft_erased_on_export", "prevents", "attribution_of_authorship", n,
             "draft_retention")
        edge("attribution_of_authorship", "enables", "informed_recourse", n, "recourse")

    if failed("appealable_intake_decision"):
        n = log.intake_rejections - log.intake_rejections_appealable
        edge("automated_completeness_rejection", "prevents", "adjudicated_decision", n,
             "intake_rejection")
        edge("adjudicated_decision", "enables", "informed_recourse", n, "recourse")

    if failed("accessibility_508_multilingual"):
        n = (sum(log.outputs_by_locale.values())
             - sum(log.outputs_verified_by_locale.values()))
        edge("unverifiable_translation", "prevents", "meaningful_notice", n,
             "locale_verification")

    return edges
