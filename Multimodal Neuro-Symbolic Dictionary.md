# Neuro-Symbolic Thought and a Multimodal Neuro-Symbolic Dictionary for Patient-Advocate AI

## TL;DR
- Neuro-symbolic cognition converges from two independent literatures — cognitive science (dual-process theory, symbol grounding, conceptual spaces, conceptual metaphor theory) and machine learning (Kautz's taxonomy, DeepProbLog, Logic Tensor Networks, concept bottleneck models) — and together they justify a design in which neural pattern-recognition is disciplined by symbolic, auditable structure.
- The deliverable is a multi-layered knowledge-graph "dictionary" whose entries each carry three named neuro-symbolic footnotes (a Grounding footnote, a Causal-Provenance footnote, and an Ethics-Warrant footnote), generate supplemental artifacts (an SVO triplet plus 2–3 compositional Maya-glyph-style icons), and are typed by a conceptual-metaphor layer.
- The system is grounded in patient-protection ethics (Beauchamp & Childress's four principles) as its "world model" source — explicitly contrasted with robot/embodied-agent world models that are grounded in physical use-cases — and is readable through five interpretive schemes: causal, ethical-audit, metaphor-structural, embedding-similarity, and semiotic.

## Key Findings

1. **Kautz's taxonomy is the organizing spine for the ML side.** Henry Kautz's AAAI-2020 taxonomy defines six types of neuro-symbolic integration along a spectrum of coupling tightness, from Type 1 (symbolic in/out around a neural core) through Type 3 (neural and symbolic components loosely coupled, e.g., the Neuro-Symbolic Concept Learner and DeepProbLog) to Types 4–6 (symbolic knowledge compiled into or embedded within the network). Verifiability increases with "hard" logic; learnability increases with end-to-end training. Our design deliberately targets Type 3–5.

2. **The symbol grounding problem defines the core challenge, and conceptual spaces offer a bridge.** Harnad (1990, *Physica D* 42:335–346) framed the problem as: "How can the semantic interpretation of a formal symbol system be made intrinsic to the system, rather than just parasitic on the meanings in our heads?" — likening ungrounded symbol manipulation to trying to learn Chinese from a Chinese/Chinese dictionary alone. Gärdenfors's conceptual spaces propose a geometric intermediate layer (convex regions in quality-dimension spaces) between subsymbolic and symbolic representation — directly motivating our embedding-similarity interpretive scheme.

3. **Conceptual metaphor theory supplies a ready-made classification layer.** Lakoff & Johnson (1980) distinguish three metaphor types — structural (ARGUMENT IS WAR), orientational (MORE IS UP), and ontological (IDEAS ARE OBJECTS) — with Grady's primary metaphors as embodied atoms and Fauconnier & Turner's conceptual blending as the compositional operation. The MetaNet repository (ICSI Berkeley) formalizes these as source→target frame mappings, providing a computational precedent for our metaphor-typing layer.

4. **Peirce's icon/index/symbol trichotomy plus Maya logosyllabic structure model compositional multimodal glyphs.** Peirce's triad classifies signs by their relation to their object (resemblance/causal-connection/convention). Maya script demonstrates how logograms and syllabograms compose into glyph blocks via affixation and infixing — an attested natural model for our compositional glyph artifacts.

5. **Pearl's structural causal models provide the causal-chain layer, and CoT-faithfulness research warns why it must be verifiable.** Pearl's SCMs and do-calculus formalize interventional/counterfactual reasoning over directed acyclic graphs. Anthropic's April 2025 study "Reasoning Models Don't Always Say What They Think" found that Claude 3.7 Sonnet and DeepSeek-R1 verbalized decisive hints in as few as 25% of cases, and that outcome-based reinforcement learning raised faithfulness only to a plateau of roughly 28% on MMLU and 20% on GPQA — motivating our insistence that causal chains be represented as auditable graph structure, not free-text rationalization.

6. **Beauchamp & Childress's four principles are the patient-protection "world model."** Autonomy, non-maleficence, beneficence, and justice serve as the grounding source for the ethics layer — the deliberate contrast to robot world models grounded in physical dynamics and affordances.

## Details

### 1. Academic synthesis — the two literatures

**Machine-learning neuro-symbolic integration.** The field's canonical framing is Garcez & Lamb's "Neurosymbolic AI: The 3rd Wave" (*Artificial Intelligence Review* 56(11):12387–12406, 2023; arXiv 2012.05876), which argues for principled integration of neural learning with symbolic knowledge representation to deliver trust, interpretability, and accountability. Henry Kautz's taxonomy (introduced at AAAI-2020) is the most cited map of the design space: Type 1 (symbolic Neuro symbolic — standard deep learning over symbolic I/O), Type 2 (neural core loosely coupled with a symbolic solver, e.g., AlphaGo with Monte Carlo tree search), Type 3 (neural and symbolic systems co-routined on complementary tasks, e.g., the Neuro-Symbolic Concept Learner and DeepProbLog), Type 4 (symbolic knowledge compiled into the neural training set/architecture), Type 5 (logic rules mapped to embeddings inside a distributed system, e.g., Logic Tensor Networks), and Type 6 (full symbolic reasoning embedded in the neural substrate). Key concrete systems:
- **DeepProbLog** (Manhaeve et al., 2018; *Artificial Intelligence* 298:103504, 2021) extends the probabilistic logic language ProbLog with *neural predicates* and neural annotated disjunctions, so a neural network outputs probabilities over logical atoms and the whole system is trained end-to-end.
- **Logic Tensor Networks** (Badreddine, Garcez, Serafini & Spranger, *Artificial Intelligence* 303, 2022) ground first-order logic in real-valued tensors via fuzzy/differentiable logical operators ("Real Logic"), enabling reasoning over continuous domains.
- **Neural Theorem Provers** (Rocktäschel & Riedel, 2016) re-implement Prolog's backward chaining in a differentiable manner, adding *soft unification* so that similar symbols can unify.
- **Concept bottleneck models** force predictions through a layer of human-interpretable concepts; recent neuro-symbolic work (Marconato et al., NeurIPS 2023; Bortolotti et al., NeurIPS 2025) shows they are vulnerable to "reasoning shortcuts," a caution we carry into the design.
- **Abductive learning** (Zhou; Dai, Huang et al.) integrates perception with logical abduction, searching a knowledge base for hypotheses that best explain neural outputs.

**Cognitive-science neuro-symbolic thought.** The psychological literature independently motivates a hybrid architecture:
- **Dual-process theory** (Kahneman, *Thinking, Fast and Slow*, 2011; building on Wason & Evans and Stanovich & West, who coined the System 1 / System 2 labels) distinguishes fast, associative, parallel System 1 from slow, deliberate, rule-governed System 2 — the cognitive analog of neural pattern-matching disciplined by symbolic reasoning.
- **The symbol grounding problem** (Harnad, 1990) asks how the semantic interpretation of a symbol system can be intrinsic rather than parasitic; this is the foundational problem any dictionary of meaning must confront.
- **Conceptual spaces** (Gärdenfors, *Conceptual Spaces: The Geometry of Thought*, 2000) posit a geometric middle layer where concepts are convex regions over quality dimensions, bridging subsymbolic perception and symbolic language.
- **The language of thought hypothesis** (Fodor, 1975) holds that thought has a compositional, syntactic, symbol-like structure ("Mentalese").
- **Structure-mapping theory** (Gentner, 1983, *Cognitive Science* 7(2):155–170; implemented as the Structure-Mapping Engine by Falkenhainer, Forbus & Gentner, 1989) models analogy as alignment of relational structure between a base and target domain, governed by the *systematicity* principle. This is the formal engine behind our metaphor-mapping edges.
- **Perceptual symbol systems** (Barsalou, 1999) argue that concepts are grounded in modal perceptual simulations rather than amodal symbols — the cognitive warrant for our multimodal glyph layer.
- **Predictive processing** (Clark; Friston) frames the brain as a hierarchical prediction-error minimizer, relevant to how expectations propagate through layered representations.

**Conceptual metaphor and blending.** Lakoff & Johnson (*Metaphors We Live By*, 1980) established that metaphor is conceptual, not merely linguistic, and proposed the three-way typology. Grady (1997) added primary metaphors — experientially grounded atoms (e.g., AFFECTION IS WARMTH, MORE IS UP) — that combine into complex/compound metaphors. Fauconnier & Turner (*The Way We Think*, 2002) describe conceptual blending: input mental spaces, a generic space, and a blended space with emergent structure. MetaNet operationalizes CMT as a searchable repository of formal source→target frame mappings.

**Semiotics and compositional writing systems.** Peirce's trichotomy classifies signs as icon (resemblance), index (causal/physical connection), or symbol (convention) — non-exclusive relations any sign can bear. Maya hieroglyphic writing is a logosyllabic script in which the glyph block is the basic structural unit; as David Mora-Marín (*Written Language & Literacy* 6:2, 2003) puts it, "The script used a compositional form of regularized shape and size, the glyph block, as the basic structural unit of texts." Logograms (word signs with phonetic and semantic value) combine with syllabograms (CV/CVC phonetic signs) via affixes — prefixes, superfixes, subfixes, postfixes — and infixing, with **phonetic complements** (syllabograms added to disambiguate a logogram's reading). The word *b'alam* "jaguar" can be spelled purely logographically (B'ALAM), mixed (b'a-B'ALAM or B'ALAM-ma), or purely syllabographically (b'a-la-m(a)). The script reads in paired columns, left-to-right and top-to-bottom. The inventory comprises approximately 800 distinct signs, of which no more than ~500 were in use at any one time and about 300 in common use; roughly 200 logograms and 100 syllabic signs have been identified (Houston, Stuart & Robertson 2004; Coe & Van Stone, *Reading the Maya Glyphs*, 2005). This is a proven natural model for compositional multimodal symbols. Emoji constitute a contemporary parallel — a standardized-but-culturally-variable visual sign system studied semiotically (Danesi, *The Semiotics of Emoji*, 2016) and analyzed as "graphicons" realizing ideational and attitudinal meaning.

**Knowledge graphs and provenance layering.** RDF provides subject-predicate-object triples and named graphs; OWL adds ontological expressivity for classes, properties, and reasoning. In healthcare and other regulated domains, the W3C PROV-O ontology is used to store provenance as typed, queryable graph structure rather than log files. Multi-layer/multiplex graph models represent the same entity across layers with typed inter-layer edges, and edge-level metadata (confidence, provenance, evidence) can be attached via reification or property-graph attributes.

**Causal inference and verifiable reasoning.** Pearl (*Causality*, 2009) represents each variable as a function of its direct causes plus noise; do-calculus and the back-door criterion license interventional and counterfactual inference over the causal DAG. Anthropic's chain-of-thought faithfulness studies show that stated reasoning is not reliably a faithful account of a model's actual process; their "Measuring Faithfulness in Chain-of-Thought Reasoning" reports that "as models become larger and more capable, they produce less faithful reasoning on most tasks we study" — an inverse-scaling result. Constitutional AI trains models against an explicit written list of principles with self-critique. Together these motivate representing reasoning as auditable graph structure with explicit warrants.

**Patient-protection ethics as world model.** Beauchamp & Childress's *Principles of Biomedical Ethics* (first ed. 1979; 8th edition, Oxford University Press, 2019, marking the book's 40th anniversary) develops four prima facie principles — respect for autonomy, non-maleficence, beneficence, and justice — balanced via specification and reflective equilibrium. Health-AI explainability research argues that explanations must be verifiable and auditable components of clinical decision support, not merely persuasive (a synthesis of 170 studies found the dominant barrier is that "explanations are rarely treated as verifiable, auditable components of clinical decision support"), and regulators (EU AI Act; FDA Good Machine Learning Practice) classify clinical decision support as high-risk, requiring transparency and human oversight. This body of work is our grounding source: a **patient-ethics-derived world model** whose primitives are duties owed to patients, in explicit contrast to **robot/embodied-agent world models** whose primitives are physical states, dynamics, and affordances learned from interaction.

### 2. The methodology

The core design claim is that a domain-specific ("non-general, open") dictionary can be turned into an auditable neuro-symbolic artifact by (a) concatenating three typed footnotes to every entry, (b) generating supplemental artifacts from verifiable causal chains, (c) scaffolding everything as a multi-layer knowledge graph, and (d) offering multiple interpretive readings of that graph. The full scaffolding is delivered as the markdown file below.

---

## THE DELIVERABLE FILE: `neurosymbolic_patient_dictionary.md`

```markdown
# Multimodal Neuro-Symbolic Patient-Advocate Dictionary
## A Scaffolding Specification (v1.0)

> A domain-specific ("non-general, open") dictionary in which every entry is a
> node in a multi-layered knowledge graph, carries three neuro-symbolic
> footnotes, generates supplemental artifacts (an SVO triplet + 2–3
> compositional glyphs), and is typed by conceptual-metaphor theory.
> Grounding source = patient-protection ethics (Beauchamp & Childress),
> deliberately contrasted with robot use-case-derived world models.

---

## 0. Design Principles (with academic warrants)

1. **Hybrid by construction.** Neural embeddings propose; symbolic structure
   disposes. (Kautz Type 3–5; Garcez & Lamb 2023; Kahneman System 1/System 2.)
2. **Grounding is explicit, not assumed.** Every symbol links to a
   conceptual-space region and/or perceptual glyph. (Harnad 1990; Gärdenfors
   2000; Barsalou 1999.)
3. **Reasoning is auditable graph structure, not free text.** Because stated
   chains-of-thought are not reliably faithful. (Pearl SCMs; Anthropic
   faithfulness studies.)
4. **Ethics is the world model.** Grounding primitives are duties to patients.
   (Beauchamp & Childress; contrast with embodied-agent world models.)

---

## 1. The Non-General Open Dictionary — Entry Structure

An **entry** is a lexical unit specific to the patient-advocacy domain
(diagnoses, procedures, consent concepts, patient rights, care-pathway terms).
"Open" = extensible, versioned, and community-editable; "non-general" = it does
not attempt whole-language coverage.

```yaml
Entry:
  id: URI                      # stable identifier
  lemma: string                # headword
  domain_sense: string         # disambiguated patient-advocacy sense
  conceptual_space_vector: [float]   # Gärdenfors grounding (quality dims)
  neural_embedding: [float]    # subsymbolic representation
  footnotes:
    - grounding_footnote          # Type G  (see §3)
    - causal_provenance_footnote  # Type C  (see §3)
    - ethics_warrant_footnote     # Type E  (see §3)
  supplemental_artifacts:
    svo_triplet: {subject, verb, object}
    glyph_set: [glyph1, glyph2, glyph3]   # compositional, Maya-style
  metaphor_typing: {type, source_frame, target_frame}
  provenance: PROV-O record
```

---

## 2. Node & Edge Types (graph schema)

| Node type            | Layer            | Description |
|----------------------|------------------|-------------|
| `LexEntry`           | Lexical          | A dictionary headword/sense |
| `ConceptRegion`      | Grounding        | Convex region in a conceptual space |
| `Glyph`              | Symbolic/Glyph   | Compositional icon (logogram+affixes) |
| `SVOTriplet`         | Symbolic/Glyph   | Subject–verb–object proposition |
| `CausalVar`          | Causal-chain     | Node in a structural causal model |
| `CausalEdge-Node`    | Causal-chain     | Reified causal link (carries confidence) |
| `EthicsPrinciple`    | Ethics/Provenance| Autonomy / Non-maleficence / Beneficence / Justice |
| `Warrant`            | Ethics/Provenance| Justification linking a claim to a principle |
| `MetaphorMapping`    | Metaphor-typing  | Source→target frame mapping (MetaNet-style) |
| `ProvenanceRecord`   | Ethics/Provenance| PROV-O entity/activity/agent |

| Edge type            | Connects                         | Reading |
|----------------------|----------------------------------|---------|
| `grounds`            | LexEntry → ConceptRegion/Glyph   | semiotic/embedding |
| `denotes`            | Glyph → LexEntry                 | semiotic |
| `causes` (do-typed)  | CausalVar → CausalVar            | causal |
| `intervention_of`    | CausalEdge-Node → CausalVar      | causal |
| `warranted_by`       | Claim/Edge → Warrant             | ethical-audit |
| `invokes_principle`  | Warrant → EthicsPrinciple        | ethical-audit |
| `maps`               | MetaphorMapping → (src,tgt) frame| metaphor-structural |
| `similar_to`         | neural_embedding ↔ embedding     | embedding-similarity |
| `derived_from`       | any node → ProvenanceRecord      | ethical-audit |
| `annotates` (footnote)| Footnote → LexEntry             | all |

Inter-layer links are typed edges; edge metadata (confidence, provenance,
evidence) is reified (RDF named graphs / property-graph attributes) so the
metadata is itself queryable, following PROV-O practice.

---

## 3. The Three Neuro-Symbolic Footnotes

Each footnote is a *typed edge bundle* concatenated to an entry. The three
types are mutually exclusive in function and collectively exhaustive over the
three things a patient-advocate system must be able to justify: **what a term
means, what it causally implies, and why acting on it is ethically permissible.**

### Footnote Type G — Grounding Footnote
- **Definition:** Anchors the entry's symbol to non-symbolic meaning — a
  conceptual-space region, a neural embedding cluster, and one or more
  perceptual glyphs.
- **Grounds/annotates:** the *sense* of the entry (solves the local symbol
  grounding problem for this term).
- **Academic basis:** Harnad 1990; Gärdenfors 2000; Barsalou 1999; Peirce
  (icon/index/symbol).
- **Formal structure:**
  ```
  G(entry) = ⟨ conceptual_region R ⊆ QualitySpace,
               embedding_centroid v,
               {(glyph_i, peirce_type_i)} ⟩
  ```
- **Patient example (entry: "informed consent"):** R = region in a
  {comprehension, voluntariness, disclosure} quality space; glyphs = [document
  icon (icon), signature-hand (index), autonomy-circle (symbol)].

### Footnote Type C — Causal-Provenance Footnote
- **Definition:** Attaches the fragment of a structural causal model in which
  the entry participates, plus the provenance of each causal edge.
- **Grounds/annotates:** the *consequences* of the entry — what interventions
  do, under do-calculus.
- **Academic basis:** Pearl SCM/do-calculus; PROV-O; Anthropic faithfulness
  (why chains must be structural, not narrative).
- **Formal structure:**
  ```
  C(entry) = ⟨ SCM fragment (V, E, f),
               {edge → confidence},
               {edge → ProvenanceRecord} ⟩
  ```
- **Patient example (entry: "opioid analgesic"):**
  `administer(opioid) --causes--> respiratory_depression`
  (confidence 0.72; provenance = named clinical guideline); intervention
  `do(reduce_dose)` lowers the downstream risk node.

### Footnote Type E — Ethics-Warrant Footnote
- **Definition:** Records which of the four principles the entry's use implicates
  and the warrant chain linking a recommended action to those principles.
- **Grounds/annotates:** the *permissibility* of acting on the entry.
- **Academic basis:** Beauchamp & Childress (autonomy, non-maleficence,
  beneficence, justice); health-AI explainability-as-audit; Constitutional AI
  (explicit principle list).
- **Formal structure:**
  ```
  E(entry) = ⟨ {principle → polarity(+/−)},
               warrant: claim ⊢ principle,
               balancing_note (specification / reflective equilibrium) ⟩
  ```
- **Patient example (entry: "involuntary hold"):** autonomy(−),
  non-maleficence(+/−), beneficence(+); warrant records the specification that
  balances restricted autonomy against imminent-harm prevention.

---

## 4. Supplemental-Artifact Generation

For each entry, artifacts are **inferred from a patient-ethics verifiable
causal chain** and attached as nodes.

### 4.1 SVO Triplet
- **How generated:** Take the highest-confidence edge in the entry's Type-C
  footnote and read it as subject (cause node) → verb (causal relation) →
  object (effect node). Because it is extracted from the SCM, the triplet is
  verifiable by construction and traceable via `derived_from`.
- **Attachment:** `SVOTriplet` node linked to the entry by `annotates`, to the
  causal edge by `derived_from`.
- **Example (entry "delayed diagnosis"):**
  `⟨ delayed_diagnosis, worsens, patient_prognosis ⟩`.

### 4.2 Compositional Glyph Set (2–3 glyphs, Maya-style)
- **Model:** Maya logosyllabic composition — a **main sign (logogram)** carrying
  core meaning, plus **affixes/phonetic-complement signs** that modify or
  disambiguate, assembled into a single **glyph block**, read left-to-right,
  top-to-bottom.
- **How generated:**
  1. **Logogram** = icon for the entry's core concept (from Grounding footnote).
  2. **Affix 1 (superfix)** = an orientational/ontological marker encoding the
     metaphor type (e.g., an up-arrow superfix for MORE IS UP risk).
  3. **Affix 2 (phonetic-complement analog, subfix)** = an ethics-polarity
     marker (e.g., a shield subfix = non-maleficence protection) that
     disambiguates the reading, exactly as a Maya phonetic complement
     disambiguates a logogram.
- **Attachment:** each `Glyph` linked by `grounds`/`denotes`; the block records
  its internal reading order.
- **Example (entry "high fall risk"):** block = [patient-logogram] +
  [up-arrow superfix = risk-is-up] + [shield subfix = protective duty].

---

## 5. The Metaphor-Typing Layer (a crawling layer)

The metaphor layer is a set of `MetaphorMapping` nodes that **crawl the
dictionary** (traverse `LexEntry` and `Glyph` nodes) and assign each a
conceptual-metaphor type, following Lakoff & Johnson + MetaNet.

| Metaphor type   | Definition | Patient-domain example |
|-----------------|------------|------------------------|
| **Structural**  | one concept structured by another domain | ILLNESS IS WAR ("fighting cancer") |
| **Orientational**| system organized by physical orientation | HEALTH IS UP / SICKNESS IS DOWN |
| **Ontological** | abstract treated as entity/substance | PAIN IS AN OBJECT ("crushing pain") |
| **Primary** (Grady) | experientially grounded atom | MORE IS UP (dose/risk scales) |
| **Complex/Blend** (Fauconnier & Turner) | composed from primaries | THE CARE PATHWAY IS A JOURNEY |

**Crawling procedure:** for each entry, (1) extract source and target frames
from its glyphs and SVO triplet; (2) match against the metaphor repository via
Gentner structure-mapping (align relational structure, prefer systematic
mappings); (3) write a `maps` edge and set `metaphor_typing`. Emoji/icon/glyph
entries are treated as first-class nodes in this layer, so the visual signs
themselves carry metaphor types (e.g., 🛡️ subfix → ontological
PROTECTION-IS-A-BARRIER).

---

## 6. The Five Interpretive Schemes (readings / crawls)

The same graph supports multiple readings; each specifies what it reveals and
how to traverse.

1. **Causal reading.** Traverse only `causes`/`intervention_of` edges over
   `CausalVar` nodes → recovers the SCM; supports do-calculus queries
   ("what if we intervene on dose?"). *Reveals:* consequence structure.
2. **Ethical-audit reading.** Traverse `warranted_by → invokes_principle` and
   `derived_from → ProvenanceRecord` → produces a principle-by-principle audit
   trail for any recommendation. *Reveals:* legitimacy and accountability.
3. **Metaphor-structural reading.** Traverse `maps` edges → shows which
   source frames structure a term and where framing may bias understanding
   (e.g., over-militarized ILLNESS IS WAR). *Reveals:* conceptual framing.
4. **Embedding-similarity reading.** Traverse `similar_to` over neural
   embeddings / conceptual-space distance → nearest-neighbor senses, clusters,
   analogies. *Reveals:* soft semantic neighborhoods (System-1 view).
5. **Semiotic reading.** Traverse `grounds`/`denotes` over `Glyph` nodes,
   classified by Peirce's icon/index/symbol → how meaning is carried
   multimodally. *Reveals:* representational grounding.

---

## 7. Worked Example Entries

### Entry A — "informed consent"

```yaml
id: pad:informed_consent
lemma: informed consent
domain_sense: patient's voluntary, comprehending authorization of an intervention
conceptual_space_vector: [comprehension=0.9, voluntariness=0.95, disclosure=0.88]
footnotes:
  grounding (G):
    region: {comprehension, voluntariness, disclosure}
    glyphs:
      - {form: document, peirce: icon}
      - {form: signing-hand, peirce: index}
      - {form: open-circle(autonomy), peirce: symbol}
  causal_provenance (C):
    scm:
      - disclosure --enables--> comprehension    (conf 0.8, prov: guideline#12)
      - comprehension --enables--> valid_consent (conf 0.85, prov: statute#4)
    intervention: do(improve_disclosure) → raises valid_consent
  ethics_warrant (E):
    principles: {autonomy:+, beneficence:+, non_maleficence:+}
    warrant: "valid_consent ⊢ respect-for-autonomy"
    balancing_note: "specification of autonomy per reflective equilibrium"
supplemental_artifacts:
  svo_triplet: {subject: disclosure, verb: enables, object: valid_consent}
  glyph_set:
    block: [document-logogram] + [open-circle superfix = autonomy-is-freedom]
           + [checkmark subfix = validity phonetic-complement]
    reading_order: left-to-right, top-to-bottom
metaphor_typing:
  type: ontological + orientational
  mapping: CONSENT IS A POSSESSION ("give/withhold consent"); FREEDOM IS UP
```

### Entry B — "high fall risk"

```yaml
id: pad:high_fall_risk
lemma: high fall risk
domain_sense: elevated probability that a patient will fall and be injured
footnotes:
  grounding (G):
    glyphs:
      - {form: falling-figure, peirce: icon}
      - {form: hazard-triangle, peirce: symbol}
  causal_provenance (C):
    scm:
      - sedation --increases--> fall_probability (conf 0.7, prov: cohort_study#9)
      - fall_probability --causes--> injury      (conf 0.6, prov: registry#3)
    intervention: do(bed_alarm) → lowers injury
  ethics_warrant (E):
    principles: {non_maleficence:+, autonomy:-}
    warrant: "restraint-free monitoring ⊢ non-maleficence without violating autonomy"
supplemental_artifacts:
  svo_triplet: {subject: sedation, verb: increases, object: fall_probability}
  glyph_set:
    block: [patient-logogram] + [up-arrow superfix = RISK IS UP]
           + [shield subfix = protective-duty phonetic-complement]
metaphor_typing:
  type: orientational (primary: MORE IS UP)
  mapping: RISK IS UP / BAD IS DOWN (the fall)
interpretive_notes:
  causal: intervene on sedation or add monitoring
  ethical_audit: non-maleficence(+) balanced against autonomy(−) via least-restrictive-means
```

---

## 8. Contrast: Patient-Ethics vs. Robot Use-Case World Models

| Dimension          | Patient-ethics world model (THIS system) | Robot/embodied world model |
|--------------------|------------------------------------------|----------------------------|
| Grounding primitives | duties owed to patients (4 principles)  | physical states, dynamics, affordances |
| Source of truth    | clinical ethics + provenance-verified evidence | sensorimotor interaction / simulation |
| Success criterion  | legitimacy, auditability, non-maleficence | task completion, prediction accuracy |
| Failure mode guarded against | unjustified/opaque recommendation | collision, task failure |
| Verification       | ethical-audit + causal reading of graph  | rollout in simulator / real world |

Both are "world models" in that they let an agent anticipate consequences; they
differ in what the world is *made of*. This system chooses **patients-and-duties**
as its ontology, not **objects-and-forces**.
```

## Recommendations

1. **Build the graph substrate first (Stage 1).** Implement the RDF/property-graph store with named-graph provenance (PROV-O) and the node/edge types in §2 before adding any neural component. Benchmark: every edge must carry a resolvable `derived_from` provenance record. If provenance coverage falls below 100% of causal edges, do not proceed.
2. **Add the three footnotes as separately validated modules (Stage 2).** Ground (G) requires a conceptual-space or embedding pipeline; Causal (C) requires an SCM authored/curated with clinicians (do not learn causal edges purely from correlation); Ethics (E) requires a human ethicist sign-off workflow. Benchmark: causal edges must pass a do-calculus identifiability check before they can emit an SVO triplet.
3. **Treat metaphor typing and glyph generation as assistive, not authoritative (Stage 3).** Because concept-based models exhibit reasoning shortcuts and CoT is not reliably faithful, glyphs and metaphor tags should be reviewed, not trusted blindly. Benchmark: metaphor mislabeling rate on a held-out clinician-annotated set below a pre-agreed threshold.
4. **Gate deployment on the ethical-audit reading.** No recommendation reaches a patient or clinician unless the ethical-audit crawl returns a complete warrant chain to at least one principle and flags any principle with negative polarity for human review. This operationalizes the EU AI Act "high-risk" and FDA transparency expectations.
5. **Keep the robot-world-model contrast explicit in governance docs.** State that grounding is ethics-derived, so evaluators do not mistakenly apply task-completion metrics where legitimacy metrics are required.

**Thresholds that change the plan:** if clinician review shows the SCM edges are not identifiable or are contested, downgrade C-footnotes from "verifiable causal chains" to "evidence-linked associations" and relabel SVO triplets accordingly. If glyph comprehension testing with real patients shows ambiguity, reduce to a single logogram + one ethics-polarity affix.

## Caveats
- **Faithfulness is not guaranteed by structure alone.** Representing reasoning as a graph makes it auditable but does not prove the neural components' internal computation matches the graph; Anthropic found reasoning models verbalized decisive hints in as few as 25% of cases and that faithfulness plateaus even under outcome-based RL (~28% MMLU, ~20% GPQA). The graph is an accountability instrument, not a mind-reading one.
- **Causal claims are only as good as their provenance.** Pearl's framework infers effects *given* a correct causal DAG; a wrong DAG yields confident wrong answers. Causal edges must be clinician-curated and marked with confidence.
- **Metaphor framing can harm.** Structural metaphors like ILLNESS IS WAR are known to shape patient experience; the metaphor layer should surface framing for critique, not entrench it.
- **Maya-glyph analogy is structural, not literal.** We borrow the compositional logogram+affix+phonetic-complement principle (Mora-Marín 2003; Coe & Van Stone 2005); we are not proposing to use actual Maya signs, which are a living cultural heritage with specific meanings.
- **Concept bottleneck / neuro-symbolic shortcuts.** The literature (Marconato et al.; Bortolotti et al.) documents that concept layers can be satisfied by spurious shortcuts; the design must test for this rather than assume interpretability.
- **Some foundational sources are books not fully quotable online** (Gärdenfors 2000; Fodor 1975; Barsalou 1999; Kahneman 2011); their claims here reflect standard secondary summaries and should be verified against primary editions before publication.
- **Sign-count and logogram/syllabogram proportions vary by catalog** because many of the ~800 Maya signs are allographs/variants of the same value; the ~200 logogram / ~100 syllabogram figures trace to Houston, Stuart & Robertson (2004) and should be cited to the primary scholars rather than aggregator pages.