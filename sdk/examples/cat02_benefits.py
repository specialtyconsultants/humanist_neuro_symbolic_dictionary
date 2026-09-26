"""Worked example: CAT-02, proactive eligibility & benefits.

A deployment that claimed human-in-the-loop, and did not deliver it in the
direction that mattered. Run it:

    PYTHONPATH=sdk python sdk/examples/cat02_benefits.py --dictionary-root .

The point of the example is the last thing it prints. The vendor claimed the
term because the solicitation required it; the telemetry says reviews followed
the deprivations rather than preceding them; the SDK withdraws the warrant and
the entry escalates. Nobody at the vendor had to decide to disclose that.
"""
from __future__ import annotations

import argparse
import datetime
import random

#: The corrections protocol (docs/adr/0003) requires a review date on any
#: provisional entry that names a party. This one names a vendor, a product, and
#: a county.
REVIEW_BY = (datetime.datetime.now(datetime.timezone.utc).date()  # noqa: UP017
             + datetime.timedelta(days=180)).isoformat()

from nsjepa_contrib import (
    ContributorConfig,
    DeploymentObserver,
    EntryBuilder,
    __version__,
    assess,
    compliance_record,
)
from nsjepa_contrib.emit import write, write_compliance
from nsjepa_contrib.validate import validate_file


def simulate(deployment_id: str, seed: int = 7) -> ObservationLog:  # noqa: F821
    """Stand-in for a real product's decision path.

    In a real integration these calls live wherever the determination is made
    and wherever the benefit is actually stopped — which are usually two
    different services, and the gap between them is exactly what the probe is
    for.
    """
    rng = random.Random(seed)
    obs = DeploymentObserver(deployment_id)
    for i in range(1200):
        ref = f"case-{i}"
        adverse = rng.random() < 0.18
        if not adverse:
            # The enrolling branch: fully automated, and nobody minds. Note that
            # it still records an effect. An automated enrolment IS a
            # consequential action, and leaving it out of the denominator is how
            # a deployment reports a flattering human-in-the-loop rate while
            # automating everything that matters.
            obs.record_effect(ref)
            continue

        # The terminating branch: same pipeline, opposite normative sign.
        reviewed_first = rng.random() < 0.22
        if reviewed_first:
            obs.record_human_decision(ref)
            obs.record_effect(ref)
            obs.record_deprivation(ref)
            obs.record_review_completed(ref)
        else:
            # the ordering the term is supposed to prevent, and the one the
            # integrator is never asked to characterise
            obs.record_effect(ref)
            obs.record_deprivation(ref)
            obs.record_human_decision(ref)
            obs.record_review_completed(ref)
    return obs.close_window()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dictionary-root", default=".")
    a = ap.parse_args()

    cfg = ContributorConfig(
        vendor_id="acme-civic",
        product="Acme Benefits Copilot 3.2",
        deployment_id="cuyahoga-jfs-prod",
        category="CAT-02",
        docket_reference="IN-2026-08-16312",
        governance_terms=[
            "human_in_the_loop",
            "audit_log_and_explainability",
            # The proposed term this category forces. A deployment may declare
            # it voluntarily, and the SDK then holds it to it exactly as if the
            # solicitation had required it — which is the point: a term is
            # discharged by evidence, and where the evidence comes from does not
            # change what it shows.
            "no_deprivation_pending_review",
            # The forcing function. Declared here so the worked example shows
            # the whole loop: the term that buys the telemetry is itself
            # assessed by the telemetry it buys.
            "verifiable_governance_telemetry",
        ],
        dictionary_root=a.dictionary_root,
    )
    log = simulate(cfg.deployment_id)

    entry, report = (
        EntryBuilder(
            cfg,
            lemma="unreviewed eligibility determination",
            domain_sense=(
                "an eligibility outcome produced by automated matching and issued "
                "to the resident as the position of the agency, with no human "
                "having opened the individual case file"),
        )
        .grounding(
            conceptual_region=["specificity", "risk", "consequentiality", "reversibility"],
            glyphs=[{"form": "figure-at-counter", "peirce": "icon", "role": "logogram"},
                    {"form": "gate-bar", "peirce": "symbol", "role": "logogram"}],
        )
        .from_observations(log)
        # The findings are adverse to this vendor's own deployment. That is what
        # makes them credible without corroboration, and declaring it is a
        # deliberate act — a contribution adverse only to the county would need
        # independent support like any other favourable claim.
        .adverse_to("vendor", "resident")
        .claim_warrant("human_in_the_loop")
        # No `because=` anywhere here. The polarities and the edges that earn
        # them both come out of the telemetry, already linked, so there is no
        # step at which a person writes down a normative conclusion the graph
        # does not reach.
        .polarity(due_process="-")
        # `due_process` needs no `because=`: it is the principle
        # `human_in_the_loop` discharges, so failing that term auto-links the
        # edges the failure derived. `resident_non_maleficence` maps to no
        # governance term, so nothing links it automatically and the gate refuses
        # it until the edges are named. That refusal is the feature — it is the
        # exact shape of the error this whole change was for, caught in the
        # example that ships.
        .claim("resident_non_maleficence", "-", because=["e1", "e2"])
        # e1/e2 are the deprivation edges: the benefit stopped before anyone
        # looked, and the recourse that forecloses. e3 is the ordering failure
        # on the action itself.
        .balancing_note(
            "the efficiency is won on the enrolling cases and the cost is paid on "
            "the terminating ones, and those are different people. An aggregate "
            "best-value calculation that nets them against each other is the "
            "specific error this deployment reproduces: the system is, on average, "
            "cheap.")
        .intervention("do(human_review_conditional_on_adverse_direction) "
                      "removes unreviewed_eligibility_determination")
        .intervention("do(continue_benefit_pending_appeal) "
                      "removes deprivation_before_adjudication")
        .glyph_block(logogram="gate", superfix="fast_is_forward", subfix="due_process")
        .metaphor("orientational (PROACTIVE IS FORWARD) — the metaphor is "
                  "directionless about sign, which is the defect")
        .build()
    )

    entry["review_by"] = REVIEW_BY
    path = write(entry, root=a.dictionary_root)
    print(f"wrote {path}")

    # ALWAYS emit the window record, entry or no entry. It is the denominator,
    # and it cannot be retrofitted because by then the windows are gone.
    findings = assess(cfg, log)
    rec = compliance_record(cfg, log, findings, produced_entry=True,
                            sdk_version=__version__)
    print(f"wrote {write_compliance(rec, root=a.dictionary_root)}\n")
    print("\n".join(report.lines()) or "(no gate actions)")
    print()
    for f in validate_file(path, a.dictionary_root):
        print(f)

    print("\n--- what the entry says about the contract that produced it ---")
    for tf in entry["term_findings"]:
        if tf["status"] in ("not_met", "unmeasured") and tf["detail"]:
            print(f"  {tf['term']}: {tf['status']}")
            print(f"    {tf['detail']}")
    print(f"\n  warrants: {entry['ethics']['warrants']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
