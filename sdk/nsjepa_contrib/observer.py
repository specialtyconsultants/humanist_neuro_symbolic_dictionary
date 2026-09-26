"""Runtime probes: measure whether the governance terms were met in production.

This is the part a vendor wires into the product, and it is the part that makes
a contribution worth more than a questionnaire. A solicitation can require
human-in-the-loop; nothing in the procurement instrument can currently observe
whether the human decided BEFORE the deprivation or after it. These probes can,
because they run where the decision runs.

THE OBSERVER TAKES EVENTS, NOT CONCLUSIONS. An earlier version asked the
integrator for `review_preceded_effect=True/False` and then treated the answer
as a measurement. That is a judgement wearing a measurement's clothes, and
capping the tier at 0.85 priced the problem rather than fixing it. The probes
below record that a thing happened and let `derive` work out the ordering from
timestamps this module stamps itself. A vendor can still decline to instrument
a path; it can no longer get the ordering wrong by accident, which is the way
this error actually happens.

NO RESIDENT DATA CROSSES THIS BOUNDARY. The observer holds counters and interval
statistics. A caller-supplied `ref` correlates two events about the same case
inside one process, is never written to the log, and is discarded when the pair
closes or the window rolls. There is no field on `ObservationLog` capable of
carrying a person: no identifiers, no free text, no payloads. This is a hard
constraint of the design and not a configuration option, because a dictionary of
institutional harms that accumulated a shadow copy of the people harmed would be
a worse artifact than the harms it records.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field

#: Bound on in-flight correlation refs. A long-running deployment must not grow
#: this map without limit. Overflow is counted and reported, never silently
#: dropped: an unmatched event whose partner was evicted is not evidence of
#: anything and the log says how many there were.
MAX_INFLIGHT = 50_000


class _Ordering:
    """Which of two paired events happened first, counted, without keeping rows.

    `a` is the thing that happens to the person (the effect, the deprivation).
    `b` is the human decision about it. The whole protection is whether b
    precedes a, and neither call site knows the answer on its own.
    """

    def __init__(self, clock) -> None:
        self._clock = clock
        self._a: OrderedDict[str, float] = OrderedDict()
        self._b: OrderedDict[str, float] = OrderedDict()
        self.total = 0
        self.b_first = 0
        self.a_first = 0
        self.evicted = 0
        self.latencies: list[float] = []

    def _put(self, book: OrderedDict, ref: str, ts: float) -> None:
        book[ref] = ts
        while len(book) > MAX_INFLIGHT:
            book.popitem(last=False)
            self.evicted += 1

    def a(self, ref: str) -> None:
        self.total += 1
        ts = self._clock()
        if ref in self._b:
            self.b_first += 1
            self.latencies.append(ts - self._b.pop(ref))
        else:
            self._put(self._a, ref, ts)

    def b(self, ref: str) -> None:
        ts = self._clock()
        if ref in self._a:
            self.a_first += 1
            self.latencies.append(ts - self._a.pop(ref))
        else:
            self._put(self._b, ref, ts)

    @property
    def unpaired_a(self) -> int:
        """`a` happened and no `b` ever did — no human decision at all."""
        return len(self._a)

    def clear(self) -> None:
        self._a.clear()
        self._b.clear()


@dataclass
class ObservationLog:
    """Aggregates only. Serialisable, inspectable, safe to attach to a PR."""
    deployment_id: str = ""
    window_started_at: float = 0.0
    window_ended_at: float = 0.0

    # --- human_in_the_loop: ordering, not a self-report ---------------------
    consequential_actions: int = 0
    decided_before_effect: int = 0
    decided_after_effect: int = 0
    never_decided: int = 0

    # --- no_deprivation_pending_review --------------------------------------
    deprivations: int = 0
    reviewed_before_deprivation: int = 0
    reviewed_after_deprivation: int = 0
    never_reviewed: int = 0
    review_latency: dict = field(default_factory=dict)

    # --- source_record_retention --------------------------------------------
    generated_records: int = 0
    records_with_source_retained: int = 0
    records_with_draft_retained: int = 0

    # --- accessibility_508_multilingual -------------------------------------
    outputs_by_locale: dict[str, int] = field(default_factory=dict)
    outputs_verified_by_locale: dict[str, int] = field(default_factory=dict)

    # --- appealable_intake_decision -----------------------------------------
    intake_rejections: int = 0
    intake_rejections_appealable: int = 0

    # --- bias_and_impact_testing (periodic, not one-shot) -------------------
    last_impact_test_at: float = 0.0

    # --- honesty about the instrumentation itself ---------------------------
    #: Events whose partner was evicted under MAX_INFLIGHT pressure. Reported so
    #: a reader can see when the ordering counts are incomplete.
    unpaired_events: int = 0
    counters: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _summary(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    return {"n": len(s), "median": round(s[len(s) // 2], 1),
            "p90": round(s[min(len(s) - 1, int(len(s) * 0.9))], 1),
            "max": round(s[-1], 1)}


class DeploymentObserver:
    """Wire these calls into the product's decision path.

    Every method is cheap, non-blocking, and safe to call from a request
    handler. None of them raise on bad input: an observer that can break a
    production benefits system will be removed from the production benefits
    system, and then nothing is measured at all.

    The `ref` arguments only have to be equal for two events about the same
    case, and unique enough not to collide within a window. A case number works.
    So does a random token held for the life of the request. It is never stored.
    """

    def __init__(self, deployment_id: str, clock=time.time) -> None:
        self._clock = clock
        self.log = ObservationLog(deployment_id=deployment_id,
                                  window_started_at=clock())
        self._action = _Ordering(clock)
        self._deprivation = _Ordering(clock)

    # -- human_in_the_loop ---------------------------------------------------
    def record_effect(self, ref: str) -> None:
        """A consequential action took effect on somebody.

        Call this where the effect lands, not where it is queued. Whether a
        human decided, and whether they decided first, is worked out by pairing
        this with `record_human_decision` — the integrator is not asked.
        """
        self._action.a(ref)

    def record_human_decision(self, ref: str) -> None:
        """A person decided the action identified by `ref`.

        Call it whether the decision authorised or reversed the action; the
        term is about a person deciding, and the ordering is what this measures.
        """
        self._action.b(ref)

    # -- no_deprivation_pending_review --------------------------------------
    def record_deprivation(self, ref: str) -> None:
        """A benefit, payment, licence, or asset withheld or withdrawn."""
        self._deprivation.a(ref)

    def record_review_completed(self, ref: str) -> None:
        """The human review bearing on that deprivation concluded."""
        self._deprivation.b(ref)

    # -- source_record_retention --------------------------------------------
    def record_generated_record(self, *, source_retained: bool,
                                draft_retained: bool) -> None:
        """A machine-drafted artifact entering an official file.

        `draft_retained` is the separable one: a log recording THAT a model was
        used survives export; the pre-edit draft recording WHAT it wrote is what
        a later challenge needs, and is what gets destroyed by default.
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
        """Freeze and return the window.

        Effects with no matching decision are counted as never decided, which is
        the honest reading: the window ended and nobody had. Decisions with no
        matching effect are dropped — a decision about an action that never
        landed is not evidence about ordering.
        """
        a, d = self._action, self._deprivation
        self.log.consequential_actions = a.total
        self.log.decided_before_effect = a.b_first
        self.log.decided_after_effect = a.a_first
        self.log.never_decided = a.unpaired_a

        self.log.deprivations = d.total
        self.log.reviewed_before_deprivation = d.b_first
        self.log.reviewed_after_deprivation = d.a_first
        self.log.never_reviewed = d.unpaired_a
        self.log.review_latency = _summary(d.latencies)

        self.log.unpaired_events = a.evicted + d.evicted
        self.log.window_ended_at = self._clock()
        a.clear()
        d.clear()
        return self.log
