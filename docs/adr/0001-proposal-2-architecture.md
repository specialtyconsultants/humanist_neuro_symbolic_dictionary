# ADR 0001 — Adopt Proposal 2 (JEPA encoder + symbolic reasoner)

## Status
Accepted.

## Context
Three graduated designs were studied for fitting the neuro-symbolic dictionary
into LeCun's JEPA/H-JEPA. Proposal 1 keeps the full six-module H-JEPA;
Proposal 3 strips to a single grounding encoder. Proposal 2 keeps JEPA as an
encoder only and hands causal + normative reasoning to the symbolic KG.

## Decision
Adopt Proposal 2 as the production target. JEPA does multimodal *grounding*
(its empirical strength); all consequential reasoning is symbolic, auditable,
and provenance-bearing.

## Consequences
- No actor, no reward, no interventional data collection. Active-agency data
  is ethically impermissible in every target domain (patients, citizens,
  borrowers), so causal knowledge is curated + provenance-tagged, not learned.
- Auditability is high: no protected interest passes through an opaque
  embedding. The CI `audit-gate` enforces a complete warrant chain per output.
- We lose long-horizon planning and Mode-1 skill compilation (accepted).

## Escalation
Move to Proposal 1 only if (a) reasoning shortcuts are defeated with a
provenance-preserving embedding-faithfulness method, and (b) a legitimate
simulation environment enables planning without real subjects.
