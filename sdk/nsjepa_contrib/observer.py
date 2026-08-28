"""Runtime probes: measure whether the governance terms were met in production.

This is the part a vendor wires into the product, and it is the part that makes
a contribution worth more than a questionnaire. A solicitation can require
human-in-the-loop; nothing in the procurement instrument can currently observe
whether the human decided BEFORE the deprivation or after it. These probes can,
because they run where the decision runs.

NO RESIDENT DATA CROSSES THIS BOUNDARY. The observer holds counters and
interval statistics. A caller-supplied `subject_ref` is used only to pair a
deprivation with its later review inside one process, is never written to the
log, and is discarded when the pair closes or the window rolls. There is no
field on `ObservationLog` capable of carrying a person: no identifiers, no free
text, no payloads. This is a hard constraint of the design and not a
configuration option, because a dictionary of institutional harms that
accumulated a shadow copy of the people harmed would be a worse artifact than
the harms it records.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Iterable


@dataclass
class ObservationLog:
    """Aggregates only. Serialisable, inspectable, and safe to attach to a PR."""
    deployment_id: str = ""
    window_started_at: float = 0.0
    window_ended_at: float = 0.0

    # --- human_in_the_loop --------------------------------------------------
    consequential_actions: int = 0
    human_reviewed: int = 0
    human_reviewed_before_effect: int = 0

    # --- no_deprivation_pending_review -------------------------------------
    deprivations: int = 0
    deprivations_before_review: int = 0
    review_latency_seconds: list[float] = field(default_factory=list)

    # --- source_record_retention -------------------------------------------
    generated_records: int = 0
    records_with_source_retained: int = 0
    records_with_draft_retained: int = 0

    # --- accessibility_508_multilingual ------------------------------------
    outputs_by_locale: dict[str, int] = field(default_factory=dict)
    outputs_verified_by_locale: dict[str, int] = field(default_factory=dict)

    # --- appealable_intake_decision ----------------------------------------
    intake_rejections: int = 0
    intake_rejections_appealable: int = 0

    # --- bias_and_impact_testing (periodic, not one-shot) ------------------
    last_impact_test_at: float = 0.0

    # --- escape hatch, deliberately narrow ---------------------------------
    counters: dict[str, int] = field(default_factory=dict)

    def rate(self, num: int, den: int) -> float | None:
        return None if den == 0 else round(num / den, 4)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["review_latency_seconds"] = _summary(self.review_latency_seconds)
        return d


def _summary(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    return {
        "n": len(s),
        "median": round(s[len(s) // 2], 1),
        "p90": round(s[min(len(s) - 1, int(len(s) * 0.9))], 1),
        "max": round(s[-1], 1),
    }


class DeploymentObserver:
    """Wire these calls into the product's decision path.

    Every method is cheap, non-blocking, and safe to call from a request
    handler. None of them raise on bad input: an observer that can break a
    production benefits system will be removed from the production benefits
    system, and then nothing is measured at all.
    """

    def __init__(self, deployment_id: str, clock=time.time) -> None:
        self._clock = clock
        self.log = ObservationLog(deployment_id=deployment_id,
                                  window_started_at=clock())
        self._pending: dict[str, float] = {}   # subject_ref -> deprivation start

    # -- human_in_the_loop ---------------------------------------------------
    def record_action(self, *, consequential: bool = True,
                      human_reviewed: bool = False,
                      review_preceded_effect: bool | None = None) -> None:
        """One consequential action taken by the system.

        `review_preceded_effect` is the whole of the protection and is
        deliberately a separate argument from `human_reviewed`. A reviewer who
        confirms a suspension already imposed satisfies "a person decides on
        every consequential action" and does not satisfy due process. Passing
        None when a human did review is treated as NOT preceding, because an
        integrator who cannot tell which side of the effect the review fell on
        does not have the control the solicitation paid for.
        """
        if not consequential:
            return
        self.log.consequential_actions += 1
        if human_reviewed:
            self.log.human_reviewed += 1
            if review_preceded_effect:
                self.log.human_reviewed_before_effect += 1

    # -- no_deprivation_pending_review --------------------------------------
    def record_deprivation(self, subject_ref: str, *, reviewed_first: bool = False) -> None:
        """A benefit, payment, licence, or asset withheld or withdrawn."""
        self.log.deprivations += 1
        if reviewed_first:
            return
        self.log.deprivations_before_review += 1
        self._pending[subject_ref] = self._clock()

    def record_review_completed(self, subject_ref: str) -> None:
        """The human review of an earlier deprivation finished."""
        started = self._pending.pop(subject_ref, None)
        if started is not None:
            self.log.review_latency_seconds.append(self._clock() - started)

    # -- source_record_retention --------------------------------------------
    def record_generated_record(self, *, source_retained: bool,
                                draft_retained: bool) -> None:
        """A machine-drafted artifact entering an official file.

        `draft_retained` is the separable one: a log that records THAT a model
        was used survives export; the pre-edit draft recording WHAT it wrote is
        what a later challenge needs, and is what gets destroyed by default.
        """
        self.log.generated_records += 1
        self.log.records_with_source_retained += int(source_retained)
        self.log.records_with_draft_retained += int(draft_retained)

    # -- accessibility_508_multilingual -------------------------------------
    def record_localised_output(self, locale: str, *, verified: bool = False) -> None:
        """One notice or answer delivered in `locale`.

        `verified` means a person competent in that language judged this output
        or a sample containing it. Delivery in N languages is testable by the
        issuing body; correctness in those N languages is not, unless somebody
        who reads them is employed to check.
        """
        self.log.outputs_by_locale[locale] = self.log.outputs_by_locale.get(locale, 0) + 1
        if verified:
            self.log.outputs_verified_by_locale[locale] = (
                self.log.outputs_verified_by_locale.get(locale, 0) + 1)

    # -- appealable_intake_decision -----------------------------------------
    def record_intake_rejection(self, *, appealable: bool) -> None:
        """An application returned at intake without reaching adjudication."""
        self.log.intake_rejections += 1
        self.log.intake_rejections_appealable += int(appealable)

    # -- bias_and_impact_testing --------------------------------------------
    def record_impact_test(self) -> None:
        self.log.last_impact_test_at = self._clock()

    # -- misc ----------------------------------------------------------------
    def count(self, name: str, n: int = 1) -> None:
        self.log.counters[name] = self.log.counters.get(name, 0) + n

    def close_window(self) -> ObservationLog:
        """Freeze and return the window. Unclosed reviews are dropped, not
        imputed: an open review is not evidence of a long one."""
        self.log.window_ended_at = self._clock()
        self._pending.clear()
        return self.log

    # -- convenience for integrators ----------------------------------------
    def observe_many(self, actions: Iterable[dict]) -> None:
        for a in actions:
            self.record_action(**a)
