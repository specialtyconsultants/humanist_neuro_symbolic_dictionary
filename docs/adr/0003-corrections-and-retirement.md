# ADR 0003 — Corrections and retirement

**Status:** accepted
**Supersedes:** nothing
**Context:** `Status.RETIRED` has existed since ADR 0001 with no protocol behind
it. That is worse than not having the value at all: it looks like the corpus has
a way to be wrong, and it does not.

## Why this is urgent rather than tidy

Entries in this corpus name real parties. `gpr:unreviewed_eligibility_determination`
names a state agency and a decided case. `gpr:investigative_flag_as_determination`
names a national government. Contributed entries name a vendor, a product, and a
deployment, and usually the county operating it.

A provisional finding about a real party is a claim with no expiry unless
somebody writes one down. Once instances aggregate to *named* institutions —
which is the whole point of `instance_of` and the reason the ratification gate
exists — evidence tier stops being a nicety and becomes a defamation surface. A
corpus that can accuse cannot rely on argument to correct itself. It needs a
clock.

## Decision

**1. `review_by` is mandatory on any provisional entry that names a party.**
ISO date. Enforced as an ERROR for contributed entries, which always name a
vendor and a deployment; a WARN for hand-written ones, where the validator
cannot tell whether a party is named and the author can.

A `review_by` in the past is not a failure. It is a queue.

**2. `retired_reason` is mandatory on retirement.** Retirement without a stated
reason is deletion with extra steps, and the corpus cannot learn from it. The
reason is the only durable record of *why* a finding did not hold, which is
frequently more useful than the finding was.

**3. Supersession is explicit and paired.** The replacement carries
`supersedes: [old_id]`; the replaced entry carries `superseded_by` and moves to
`retired`. An entry with `superseded_by` that is still `provisional` or
`ratified` is an ERROR — two live entries making the same claim is exactly how a
corrected finding keeps circulating.

**4. Retired entries are not deleted.** They stay in the tree, retired. A
finding that was withdrawn is itself evidence about how the corpus behaves, and
a corpus that quietly removes its errors is asking to be trusted rather than
checked.

## The four events that retire an entry

| Event | Action |
|---|---|
| Regulatory or judicial finding contradicts it | supersede with the finding cited at its tier |
| Contributor discovers its telemetry miscounted | retire; `retired_reason` states the defect; re-emit if the corrected window still supports a finding |
| Deployment decommissioned | retire. The finding was true of a system that no longer runs, and a live claim about a dead system reads as a live claim |
| `review_by` passes with no re-check | NOT automatic retirement. It raises the entry in the review queue. Expiring findings on a timer would let anyone run out the clock by not looking |

## What this does not settle

Who may retire an entry. The ratification gate says a contributor cannot ratify
its own entry; it is silent on whether a contributor may retire one, and there
is a real argument on both sides — a vendor discovering its own instrumentation
defect is the fastest path to a correction, and a vendor retiring an unflattering
finding is the obvious abuse. The current implementation permits it and records
it, on the grounds that a retirement is visible and a suppressed contribution
never appears at all. Revisit once more than one vendor is contributing.

## Consequences

- `core/schemas/entry.py` gains `supersedes`, `superseded_by`, `retired_reason`,
  `review_by`.
- `nsjepa_contrib.validate` enforces the rules above.
- The nine `gov_procurement` seed entries and three `patient_advocacy` entries
  are provisional with no `review_by` and currently emit that WARN. They name
  institutions through their sources rather than as subjects of a live
  accusation, so this is a queue item and not a blocker — but it is a real one,
  and the warning is left on rather than suppressed.
