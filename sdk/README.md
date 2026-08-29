# nsjepa-contrib

**Emit dictionary entries from a deployed government AI system, and contribute them to a common repository.**

For vendors shipping through NASA SEWP V, ITES-SW2, NASPO ValuePoint, or any other vehicle where a solicitation specified governance terms and somebody will eventually ask whether you met them.

---

## What this is for

A solicitation can *require* human-in-the-loop. Nothing in the procurement instrument can *observe* whether the human decided before the deprivation or after it — and that ordering is the whole of the protection. A reviewer who confirms a suspension already imposed satisfies "a person decides on every consequential action" and does not satisfy due process. The refund arrives three months later; the rent was due in March.

This SDK closes that gap from inside the product, where the decision actually runs. It does three things:

1. **Observes** whether the governance terms the solicitation bought were met in production — not at proposal time, and not as a questionnaire.
2. **Builds** a neuro-symbolic dictionary entry from those observations, under gates that will withdraw a warrant the telemetry does not support.
3. **Submits** it to the common repository as a pull request, or as a sealed bundle for air-gapped deployments.

The output is a `.entry.yaml` carrying three footnotes — grounding (what the term means), causal (what it implies, as an SCM fragment), and ethics (why acting on it is permissible, or why that question is being escalated instead).

## Why a vendor would ship this

Because the entry is evidence you can hand to a procurement officer, produced continuously and mechanically rather than assembled under deadline by the people with the most reason to shade it.

And because the alternative is worse for you. Every category on the Interstate form has a documented failure behind it — MiDAS, SyRI, Draft One, the FCC docket, FEMA's Alaska translations. In each case the vendor's compliance posture was fine right up until an auditor general, a court, or a reporter established otherwise, and the absence of contemporaneous evidence was itself part of the finding. A deployment that can show what its telemetry said at the time, including where it fell short, is in a categorically different position from one that can show a signed questionnaire.

**Read this before you integrate:** the SDK is designed so that an entry can contradict the contract that produced it. If your telemetry shows a term was not met, the warrant is withdrawn and the reason is written into the file. That is not a bug to be configured around, and there is no flag to turn it off. If that outcome is unacceptable to your organisation, do not integrate this — a corpus with the failures filtered out would be worth less than nothing, because it would look like evidence.

---

## Install

```bash
pip install nsjepa-contrib
```

Python ≥3.10. One dependency (`PyYAML`). Standard library everywhere else, deliberately — a governance SDK that drags a dependency tree into a FedRAMP boundary does not get installed, and then nothing is contributed.

You also need a checkout of the dictionary repository. The gates are enforced against *that* domain's real norms, not against a copy vendored into your product, so a vendor cannot loosen a rule by editing a file it ships.

```bash
git clone https://github.com/specialtyconsultants/humanist_neuro_symbolic_dictionary
export NSJEPA_DICTIONARY_ROOT=$PWD/humanist_neuro_symbolic_dictionary
```

## Quickstart

```bash
nsjepa-contrib init \
  --vendor-id acme-civic \
  --product "Acme Benefits Copilot 3.2" \
  --deployment-id cuyahoga-jfs-prod \
  --category CAT-02 \
  --docket "IN-2026-08-16312" \
  --terms human_in_the_loop audit_log_and_explainability
```

It writes `nsjepa_contrib.json` and then tells you which selectable terms you did **not** claim, and what that means:

```
Selectable terms NOT claimed by this deployment:
  accessibility_508_multilingual   discharges meaningful_access
  bias_and_impact_testing          discharges non_discrimination
  data_residency_no_training       discharges data_sovereignty
  exit_ready_no_lock_in            discharges continuity_of_public_capacity

Every resident-facing harm this deployment produces will carry `warrants: []`
and escalate. That is the correct behaviour, not a misconfiguration.
```

Then wire the probes into your decision path:

```python
from nsjepa_contrib import ContributorConfig, DeploymentObserver, EntryBuilder

cfg = ContributorConfig.load()
obs = DeploymentObserver(cfg.deployment_id)

# The probes take EVENTS, not conclusions. You are never asked whether the
# review came first; you record that each thing happened, where it happens, and
# the ordering is derived from timestamps the SDK stamps itself.

# wherever a person actually decides
obs.record_human_decision(case_ref)

# wherever the determination actually takes effect on somebody
obs.record_effect(case_ref)

# wherever the benefit is actually stopped — usually a different service, and
# the gap between the two is exactly what this probe is for
obs.record_deprivation(case_ref)
obs.record_review_completed(case_ref)
```

An earlier version asked you for `review_preceded_effect=True/False` and treated
the answer as a measurement. That is a judgement wearing a measurement's
clothes. You can still decline to instrument a path; you can no longer get the
ordering wrong by accident, which is the way this error actually happens.

and at the end of a reporting window:

```python
entry, report = (
    EntryBuilder(cfg,
                 lemma="unreviewed eligibility determination",
                 domain_sense="an eligibility outcome issued as the position of "
                              "the agency with no human having opened the file")
    .from_observations(log)
    .adverse_to("vendor", "resident")     # who these findings cut against
    .claim_warrant("human_in_the_loop")
    .polarity(due_process="-")            # auto-linked: see below
    .claim("resident_non_maleficence", "-", because=["e1", "e2"])
    .balancing_note("...")
    .build()
)
print("\n".join(report.lines()))

# ALWAYS emit the window record, entry or no entry. It is the denominator.
rec = compliance_record(cfg, log, assess(cfg, log), produced_entry=bool(entry))
write_compliance(rec)
```

`due_process` needs no `because=`, because it is the principle
`human_in_the_loop` discharges: failing that term auto-links the edges the
failure derived. `resident_non_maleficence` maps to no governance term, so
nothing links it automatically and the gate refuses it until you name the edges.
That refusal is the feature.

A worked end-to-end example, including a simulated deployment, is in [`examples/cat02_benefits.py`](examples/cat02_benefits.py).

---

## The four gates

They run at `build()`. None is configurable off. They are the reason a vendor-authored entry is worth reading at all.

### 1. Provenance — the tier caps the confidence

Every causal edge carries `<tier>:<identifier>#<section>`, and the tier sets a ceiling:

| Tier | Ceiling | Independent | What it is |
|---|---|---|---|
| `court` | 0.95 | ✔ | a judgment or holding |
| `regulator` | 0.90 | ✔ | inspector general, auditor general, regulator finding |
| `legislature` | 0.85 | ✔ | parliamentary or legislative inquiry |
| `acad` | 0.85 | ✔ | peer-reviewed or working-paper empirical work |
| `audit` | 0.85 | ✔ | third-party audit — commissioned by you, performed by someone else |
| `press` | 0.80 | ✔ | reporting by a named outlet with a named author |
| `runtime` | 0.85 | ✘ | telemetry from this SDK — measured, not asserted |
| `operator` | 0.75 | ✘ | an assertion by the government body |
| `inferred` | 0.70 | ✘ | a structural inference, not an observation |
| `vendor` | 0.60 | ✘ | an assertion by the party that built or sells the system |

Runtime edges are additionally shrunk toward zero for small samples, so one adverse event does not emit a 0.85 edge. The shrinkage is crude on purpose and documented as a placeholder — replace it with a Wilson lower bound before any of this feeds institution-level aggregation.

An edge you could not ground says so in the identifier: `inferred:<what>#needs_grounding`. Validation reports these as open grounding targets, not as errors. **An honestly-marked weak edge is a contribution; a tool that failed the build over one would teach you to launder it into something that passes.**

### 2. Conflict of interest — who the finding cuts against

Every polarity names the edges that earn it, and **a claim needs independent
support unless it is adverse to the party submitting it.**

The rule used to be stated on the *sign* of the claim: positives need
corroboration, negatives do not. That has a hole. A vendor reporting *"the
county configured us to deprive first"* is filing a **negative** finding that is
adverse to the operator and favourable to the vendor, and it sailed through at
face value — which is precisely the contribution a vendor has an incentive to
file. So `adverse_to` is required on every contribution, it is deliberately not
defaulted, and the requirement keys on it.

Testimony against interest is credible on its own. A negative finding aimed at
somebody else is not testimony against interest merely because it is negative.

One tier is independent and still cannot support a *positive* claim:
`analytic:`, which is true from the definitions. Without that exclusion a
contributor could define its way to a favourable ethics footnote.

Before `supported_by` existed, Type G was checkable against the glyph
vocabulary and Type C against its provenance tiers, and **Type E was an
assertion sitting beside the graph with no link to it** — the only footnote a
reader had to take on faith. Applying the rule to the nine hand-written
`gov_procurement` entries dropped four of their five positive polarities. Only
one had independent, non-analytic support.

### 3. Warrants are earned, not declared

You declare `human_in_the_loop` in your config because the solicitation required it. The SDK then reads the telemetry and decides whether you get to claim it:

```
WARRANT WITHDRAWN  human_in_the_loop: not_met (observed 0.0467, n=1200)
                   consequential actions took effect before a human decided;
                   the term fixes THAT a person decides, and this deployment
                   shows it was not WHEN
ESCALATED          warrants: [] -- no rule reaches this harm; a human
                   normative decision is required before ratification
```

Warrants may only cite claims that exist in the domain's `norms/rules.yaml`. A harm no rule reaches gets `warrants: []`, which is the escalation signal and survives into the file. **The engine never manufactures permissibility.**

Four statuses, and the difference between the middle two matters:

- `MET` — claimed, measured, and satisfied.
- `NOT_MET` — claimed, measured, and not satisfied. The warrant is withdrawn.
- `UNMEASURED` — claimed, and this deployment did not instrument it. Reported as silence, not as failure. The term may well be met.
- `NOT_CLAIMED` — the solicitation did not require it. Not a finding.

Three terms are permanently `UNMEASURED` when claimed: `exit_ready_no_lock_in`, `data_residency_no_training`, and `minority_view_preservation`. No probe inside your product can honestly reach them, and the SDK will not convert an assertion into evidence by restating it. Those need an independent audit tier.

### 4. Ratification — you cannot ratify yourself

Every contributed entry is `status: provisional`, and lands in `contrib/<vendor>/<deployment>/`, outside the canonical `domains/<domain>/entries/` namespace. Promotion is a maintainer action. The gate is structural, not a field anyone could flip, and it exists because once instances aggregate to *named* institutions, evidence tier stops being a nicety and becomes a defamation surface.

A contribution is an **instance of** a lemma, not a competing definition of one:

```yaml
id: gpr:unreviewed_eligibility_determination#acme-civic/cuyahoga-jfs-prod
instance_of: gpr:unreviewed_eligibility_determination
```

Ten deployments of the same category produce ten entries that group cleanly rather than colliding on one URI.

---

## Node vocabulary — why your names get rewritten

The dictionary's claim to say anything structural rests on entries written by unrelated people from unrelated events converging on shared causal nodes. That convergence is real and it is **not automatic**.

The first pass at the nine Interstate category entries produced 71 nodes with zero overlap, because the same capacity had been named `reliance_defense`, `impeachment_of_the_record`, `contestation_of_grounds`, `right_of_appeal`, and `informed_recourse` in five different entries. Nothing was wrong with any of those names. The graph simply could not tell they meant the same thing. Unified, they showed five of nine entries — and both entries in an unrelated medical domain — foreclosing one capacity.

So node names resolve against `domains/<domain>/vocab/nodes.yaml`:

```bash
$ nsjepa-contrib vocab reliance_defense right_of_appeal made_up_node
reliance_defense -> informed_recourse
     the affected person's ability to contest an outcome before a body that can reverse it
right_of_appeal -> informed_recourse
made_up_node UNREGISTERED
```

Unregistered names are a warning, not an error — you may genuinely have found something new. But check the suggestion first. A corpus that grows without governed node identity stops producing convergence on its first day, and nobody notices, because the entries all still validate.

## Privacy — what cannot cross this boundary

**No resident data.** `ObservationLog` holds counters and interval statistics. There is no field on it capable of carrying a person: no identifiers, no free text, no payloads. The `subject_ref` you pass to `record_deprivation` pairs a deprivation with its later review inside one process, is never written to the log, and is discarded when the pair closes.

This is a constraint of the design and not a configuration option. A dictionary of institutional harms that accumulated a shadow copy of the people harmed would be a worse artifact than the harms it records. There is a test asserting it (`test_observation_log_carries_no_subject_identifiers`); keep it in your fork.

## Submission

**Online** — a pull request against the common repo, from your fork:

```bash
export NSJEPA_CONTRIB_TOKEN=...     # contents:write + pull_requests:write on YOUR FORK only
nsjepa-contrib submit contrib/acme-civic/cuyahoga-jfs-prod/*.entry.yaml
```

Never a direct push. A token with write access to upstream is a finding in its own right.

**Air-gapped** — Interstate's own instrument offers a local/on-premise hardware CLIN, and a contribution path assuming outbound HTTPS would exclude exactly the deployments whose entries are hardest to obtain any other way:

```bash
export NSJEPA_BUNDLE_HMAC_KEY=...   # optional; unsigned bundles report signed:false plainly
nsjepa-contrib bundle contrib/acme-civic/*/*.entry.yaml --out acme.zip \
  --vendor-id acme-civic --deployment-id cuyahoga-jfs-prod
# on the far side
nsjepa-contrib verify acme.zip
```

Bundles carry a SHA-256 per file and refuse to unpack anything outside `contrib/` — a crafted archive that could write `norms/rules.yaml` is precisely how you would make a dishonest entry validate.

## Command reference

| Command | Does |
|---|---|
| `init` | write a contributor config; report unclaimed terms |
| `terms` | list governance terms and the principle each discharges |
| `assess --log <json>` | score an observation window against claimed terms |
| `validate [path]` | validate one entry, or the whole `contrib/` tree |
| `vocab [names...]` | resolve node names against the canonical registry |
| `convergence [--check]` | shared causal nodes across the corpus; `--check` fails on regression |
| `bundle` / `verify` | air-gapped packaging and receipt |
| `submit` | open a PR against the common repo |

`validate` exits non-zero on ERROR only. Warnings are informational by design.

---

## The denominator

A fully compliant window derives no edges and therefore no entry — correct,
because meeting your terms is a compliance fact and not a claim about the world.
The consequence is survivorship: without a record that the window happened, the
corpus fills only with failures and has no denominator, and the first person to
compute *"X% of CAT-02 deployments deprive before review"* over it gets a number
that means nothing and looks authoritative.

So emit a `ComplianceRecord` every window, entry or no entry. They are cheap,
they carry no causal claims, and they cannot be retrofitted, because by then the
windows are gone.

---

## The two terms that are not on the form

Everything else here is well-formed and, absent a term that buys it, nobody
installs it: **a vendor ships something capable of withdrawing its own
compliance claim only when not shipping it costs more.**

`nsjepa-contrib terms` prints both of these at the bottom of the list.

**`verifiable_governance_telemetry`** — the system emits signed, continuous
evidence of whether the other terms were met in production. It is the only term
on any of these lists discharged by mechanism rather than by assertion, and the
only one that is checkable *after* award, which is when every failure in the
CAT-01..09 seed actually happened. It is also the forcing function for this
package.

**`independent_governance_audit`** — a third-party assessor, engaged and paid by
the issuing body rather than the vendor, verifying the terms no runtime probe
can reach. `nsjepa-contrib terms` marks three of the six selectable §3 terms
`[NOT OBSERVABLE from inside a product]`: `exit_ready_no_lock_in`,
`data_residency_no_training`, `minority_view_preservation`. They are facts about
corporate conduct, hosting, and what was left *out* of a synthesis. No amount of
vendor instrumentation reaches them.

Roughly half the governance surface the form sells cannot be verified by the
party being asked to verify it. That half closes with money, not with code. Cost
is the honest objection and the answer is that an unverifiable requirement is
not cheaper than an audited one — it is a requirement whose failure nobody will
detect.

---

## Corrections and retirement

See [`docs/adr/0003-corrections-and-retirement.md`](../docs/adr/0003-corrections-and-retirement.md).

Entries name real parties. A provisional finding about a real party is a claim
with no expiry unless somebody writes one down, so `review_by` is mandatory on
every contributed entry, `retired_reason` is mandatory on retirement, and
supersession is explicit and paired. Retired entries stay in the tree: a
withdrawn finding is itself evidence about how the corpus behaves, and a corpus
that quietly removes its errors is asking to be trusted rather than checked.

A `review_by` in the past is a queue, not a failure. Entries do not expire on a
timer, because that would let anyone run out the clock by not looking.

---

## Things this deliberately will not do

- **Emit an entry from a clean run.** A deployment that met every term has produced a compliance record, which `assess` prints, and not a claim about the world. The dictionary is for what institutions do to people; an attestation that nothing was done to anyone is not an entry.
- **Let you set `status: ratified`.** Validation errors on it.
- **Let you write a warrant for a rule that does not exist upstream.** Propose the rule first.
- **Convert an assertion into evidence** by relabelling its tier.
- **Score a positive claim about your own product on your own say-so.**
- **Push to the common repo.**

## Known gaps

Stated plainly, because a governance tool that hides its own limits is the thing it is supposed to prevent.

- **`shrink_to_sample` is not a real interval.** It is `ceiling · n/(n+30)`. Adequate to stop a single incident emitting a confident edge, inadequate for anything downstream of that. Needs a Wilson lower bound before institution-level aggregation ships.
- **The `runtime` tier still trusts the integrator.** Taking events instead of conclusions removed the case where the ordering is reported wrongly by accident — which is how that error actually happens — but nothing stops a vendor calling `record_human_decision` before `record_effect` unconditionally. The tier stays capped at 0.85 and non-independent for that reason. Runtime telemetry establishes what your instrumentation reported, not what happened; `independent_governance_audit` is what converts one into the other.
- **The 0.98 threshold is a judgement call**, not a derived figure. It is not 1.0 because no production system reaches 1.0 and a threshold nobody can meet gets the SDK switched off. Overrides are recorded in the entry.
- **The `analytic` tier is a judgement about which claims are definitional.** It exists because `inferred` at 0.70 was capping claims that follow from an entry's own `domain_sense` and that no fieldwork would move. The guard is that a reviewer must be able to check an analytic edge without leaving the file, and it is a guard enforced by review rather than by code. Expect it to be the most-abused tier.
- **Three of the six §3 terms are unobservable from inside a product.** Roughly half the governance surface the form sells cannot be verified by the party being asked to verify it. That is a finding about the instrument, not about this code.
- **`assess` reports two different silences as `UNMEASURED`** and distinguishes them only in the detail text: a term nothing can reach, and a term this SDK has not implemented a probe for. The second is a backlog item in here; the first costs money to close.
- **HMAC establishes integrity, not authorship.** Key distribution is your deployment's problem and this module does not pretend otherwise.

### Convergence is measured, not assumed

`python tools/convergence_report.py --check` runs in CI. The corpus rests on
unrelated entries converging on shared causal nodes, and **nothing else fails
when that dies** — every entry still validates, the graph just quietly stops
being one graph. The first pass at the nine seed entries produced 71 nodes with
zero overlap because the same capacity had five different names.

The check fails only on regression: a node that was shared and no longer is.
Unregistered recurring nodes are reported and do not fail, because a contributor
may genuinely have found something new.

---

## Licence

Apache-2.0, same as the dictionary.
