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
import random

from nsjepa_contrib import ContributorConfig, DeploymentObserver, EntryBuilder
from nsjepa_contrib.emit import write
from nsjepa_contrib.validate import validate_file


def simulate(deployment_id: str, seed: int = 7) -> "ObservationLog":  # noqa: F821
    """Stand-in for a real product's decision path.

    In a real integration these calls live wherever the determination is made
    and wherever the benefit is actually stopped — which are usually two
    different services, and the gap between them is exactly what the probe is
    for.
    """
    rng = random.Random(seed)
    obs = DeploymentObserver(deployment_id)
    for i in range(1200):
        adverse = rng.random() < 0.18
        if not adverse:
            # the enrolling branch: fully automated, and nobody minds
            obs.record_action(human_reviewed=False)
            continue
        # the terminating branch: same pipeline, opposite normative sign
        reviewed_first = rng.random() < 0.22
        obs.record_action(human_reviewed=True, review_preceded_effect=reviewed_first)
        ref = f"case-{i}"
        obs.record_deprivation(ref, reviewed_first=reviewed_first)
        if not reviewed_first:
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
        governance_terms=["human_in_the_loop", "audit_log_and_explainability"],
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
        .claim_warrant("human_in_the_loop")
        .polarity(due_process="-", resident_non_maleficence="-")
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

    path = write(entry, root=a.dictionary_root)
    print(f"wrote {path}\n")
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
