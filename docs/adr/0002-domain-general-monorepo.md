# ADR 0002 — Domain-general monorepo with swappable domain packs

## Status
Accepted.

## Context
Three use cases are planned: patient advocacy, government procurement, and
agriculture microfinance. They share architecture but differ in ontology,
grounding norms, and glyph/metaphor vocabulary.

## Decision
One monorepo. A domain-independent `core/` engine plus `domains/<name>/` packs
that implement `core.schemas.domain.Domain` and are auto-registered. Adding a
domain = adding a folder; `core/` is never edited for a new domain.

## What differs per domain (only these three)
1. Ontology (the LexEntry vocabulary).
2. Norms / grounding "world model" (the source of permissibility):
   - patient_advocacy: autonomy, non-maleficence, beneficence, justice
   - gov_procurement: open competition, fair treatment, transparency,
     conflict-of-interest avoidance, best-value integrity
   - agri_microfinance: contract fairness, non-predatory terms, solvency
     protection, disclosure, proportionate recourse
3. Glyph / metaphor vocabulary.

## What is shared (never reimplemented)
Three-footnote schema, SCM/do-calculus reasoner, norms *engine*, KG store,
the five interpretive readings, artifact generators.

## Consequences
- Norm content is data (YAML), not code — reviewable by domain experts.
- The immutable-floor property of the norms engine is enforced centrally,
  identically across domains.
