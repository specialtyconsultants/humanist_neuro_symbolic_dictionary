# nsjepa — Neuro-Symbolic JEPA Advisor (Proposal 2)

A **Kautz Type-3** neuro-symbolic system: a JEPA encoder does multimodal
*grounding only*, and a symbolic knowledge graph does all causal and
normative reasoning. The system **advises, it never acts** — there is no
actor, no reward, no interventional data collection.

This repository implements **Proposal 2** ("JEPA-Encoder + Symbolic Reasoner")
from the architecture study. It is deliberately domain-general: the same core
engine serves three domains that differ only in their ontology, their
*grounding norms* (the "world model" of duties/rules), and their glyph
vocabulary.

```
percept ──► [JEPA encoder]  s_x        (neural: grounding, Type-G footnote)
                 │
                 ▼
          [symbolic knowledge graph]
                 │
         Type-C SCM query (do-calculus, edge→confidence, edge→provenance)
                 │
         Type-E norms filter (domain principles; polarity + warrant chain)
                 │
                 ▼
        recommendation + full auditable graph trace
```

## Why this shape

- **JEPA is used only where it is empirically strong** — robust,
  augmentation-free multimodal grounding (I-JEPA, LeJEPA/SIGReg).
- **Everything consequential stays symbolic and provenance-bearing.** No
  patient/citizen/borrower interest passes through an opaque embedding.
- **No active-agency data.** You cannot ethically run interventional
  experiments on patients (or citizens, or smallholder farmers), so causal
  knowledge comes from curated, provenance-tagged SCM fragments — not from a
  learned world model.

## The three footnotes (per dictionary entry)

| Footnote | What it grounds | Lives in |
|---|---|---|
| **Type G** — Grounding | what a term *means* | `core/encoder` + `core/kg` |
| **Type C** — Causal-Provenance | what it *implies* (SCM, do-calculus) | `core/scm` |
| **Type E** — Ethics/Norms-Warrant | why acting on it is *permissible* | `core/norms` |

## Layout

- `core/` — domain-independent engine (encoder, footnotes, SCM, norms, KG,
  metaphor, interpret, schemas).
- `domains/` — one pack per use case. A pack supplies an ontology, a norm
  set, a glyph vocabulary, and seed entries. **Adding a domain = adding a
  folder, not editing `core/`.**
- `services/` — API, audit service, CLI.
- `training/` — encoder pretraining/finetuning (SIGReg/VICReg configs).
- `eval/` — collapse checks, reasoning-shortcut probes, audit-trace tests.
- `docs/adr/` — architecture decision records.

## Domains

| Pack | Grounding norms ("world model") | Status |
|---|---|---|
| `patient_advocacy` | Beauchamp & Childress: autonomy, non-maleficence, beneficence, justice | reference impl |
| `gov_procurement` | procurement-integrity rules (competition, fairness, transparency, conflict-of-interest) | planned |
| `agri_microfinance` | contract-fairness + borrower/creditor-protection norms | planned |

See `domains/README.md` for the domain-pack contract.

## Quickstart

```bash
pip install -e .
nsjepa ground --domain patient_advocacy --input examples/consent_case.json
nsjepa audit  --trace last          # replay the full graph trace
```

## Non-goals

- No actor / effectors / planning loop (that is Proposal 1).
- No claim that the JEPA is a "world model" (that is Proposal 3's honest
  concession, inherited here).
- Government-procurement and microfinance packs reuse the same engine; they do
  **not** fork it.
