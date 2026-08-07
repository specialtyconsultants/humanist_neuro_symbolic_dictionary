# Domain packs — the contract

A domain pack teaches the shared `core/` engine about one use case. The engine
never imports a domain by name; it discovers packs through a registry entry
point and drives them through the `Domain` protocol
(`core/schemas/domain.py`). **Adding a domain must never require editing
`core/`.**

## Required files

```
domains/<name>/
├── domain.py            # implements core.schemas.domain.Domain
├── ontology/            # entity/relation types (OWL/RDF or YAML) — the LexEntry vocabulary
├── norms/               # the grounding "world model": principles + warrant rules
│   ├── principles.yaml  # the finite principle set + polarities
│   └── rules.yaml       # claim ⊢ principle warrant templates
├── glyphs/              # compositional glyph vocabulary (logograms, superfixes, subfixes)
│   └── vocab.yaml
└── entries/             # seed dictionary entries (may be empty at first)
    └── *.entry.yaml
```

## The three things that change per domain

1. **Ontology** — the LexEntry vocabulary (diagnoses vs. solicitation clauses
   vs. loan covenants).
2. **Norms / grounding world model** — the *source of permissibility*:
   - `patient_advocacy`: autonomy, non-maleficence, beneficence, justice.
   - `gov_procurement`: open competition, fair treatment, transparency,
     conflict-of-interest avoidance, best-value integrity.
   - `agri_microfinance`: contract fairness, non-predatory terms,
     borrower solvency protection, disclosure, proportionate recourse.
3. **Glyph / metaphor vocabulary** — the culturally-appropriate compositional
   signs and the metaphor frames worth flagging (e.g. `DEBT IS A BURDEN`,
   `PROCUREMENT IS A CONTEST`).

## What every domain shares (do NOT reimplement)

- The three-footnote schema (G/C/E).
- The SCM/do-calculus reasoner (`core/scm`).
- The norms *engine* (`core/norms`) — only the norm *content* is per-domain.
- The knowledge-graph store, node/edge types, and the five interpretive
  readings (`core/kg`, `core/interpret`).
- The SVO-triplet + glyph-block artifact generators (`core/footnotes`).

## Minimal `domain.py`

```python
from core.schemas.domain import Domain, register

@register("agri_microfinance")
class AgriMicrofinance(Domain):
    name = "agri_microfinance"
    ontology_path = "domains/agri_microfinance/ontology"
    principles_path = "domains/agri_microfinance/norms/principles.yaml"
    warrant_rules_path = "domains/agri_microfinance/norms/rules.yaml"
    glyph_vocab_path = "domains/agri_microfinance/glyphs/vocab.yaml"
    # optional: override grounding heads, embedding space, etc.
```
