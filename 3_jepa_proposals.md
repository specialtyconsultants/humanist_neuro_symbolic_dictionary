# Fitting a Multimodal Neuro-Symbolic Patient-Advocate Dictionary into JEPA / H-JEPA — Three Graduated Architectural Proposals

## TL;DR
- **Three graduated designs are viable, and the moderate one wins.** Proposal 1 keeps LeCun's full six-module H-JEPA (configurator, world model, cost, memory, actor, hierarchical planning) and mounts the dictionary as its target representation, its §4.5.2 prediction heads, and its §4.9 key-value memory; Proposal 2 keeps only a JEPA *encoder* and hands reasoning to the symbolic dictionary (Kautz Type-3); Proposal 3 strips JEPA to a single non-hierarchical grounding encoder (I-JEPA/LeJEPA as a frozen backbone).
- **The recommended design for patient-protection legitimacy is Proposal 2.** It uses JEPA for what it is empirically good at (robust, augmentation-free multimodal grounding) while keeping every causal and ethical decision symbolic, auditable and provenance-bearing — which is decisive because "active-agency" data collection on patients is ethically impermissible, removing the very data stream that grounds V-JEPA-style world models.
- **The Beauchamp–Childress ethics warrant can be mapped onto LeCun's immutable Intrinsic Cost, but only as a hard floor, not a full ethical reasoner.** LeCun requires the Intrinsic Cost to be immutable to prevent behavioral drift; the four principles are *prima facie* and require balancing/specification via reflective equilibrium, so a fixed scalar cost captures the guardrail but discards the deliberation ethics actually requires.

## Key Findings

1. **JEPA generalizes well past pixels — including to graphs, clinical data, and explicit neuro-symbolic rules — so mounting a dictionary on it is not a category error.** I-JEPA (Assran et al., CVPR 2023) learns semantic image features by predicting *representations* of masked target blocks from a context block, with no pixel decoder; V-JEPA 2 (Assran et al., arXiv:2506.09985, June 2025) extends this to a video *world model*. Graph-JEPA (Skenderi et al., TMLR) applies the paradigm to graph-level representation learning, and RiJEPA ("neuro-symbolic JEPA," Huang & Raza, arXiv:2603.13265, 2026) injects symbolic rules into JEPA via energy-based constraints and reports a clinical use case, claiming 100% zero-shot logical accuracy with distance-based geometric justification. This directly demonstrates the feasibility of the symbolic-anchoring idea at the heart of Proposals 1–2.

2. **The non-contrastive collapse theory tells us exactly how to anchor a JEPA to a fixed dictionary without collapse.** VICReg (Bardes, Ponce & LeCun, ICLR 2022) prevents collapse with a per-dimension variance floor plus covariance decorrelation plus an invariance term; Barlow Twins (Zbontar et al., ICML 2021) drives the embedding cross-correlation matrix toward the identity. Most importantly, LeJEPA (Balestriero & LeCun, arXiv:2511.08544, Nov 2025) proves the isotropic Gaussian is the optimal embedding distribution for minimizing downstream prediction risk and enforces it with Sketched Isotropic Gaussian Regularization (SIGReg), which runs in linear time, uses a single tunable hyperparameter, needs no stop-gradient or teacher-student, is validated across 60+ architectures, and has a core implementation of about 50 lines of code — making the minimal Proposal 3 cheap and provably collapse-resistant.

3. **A dictionary "prediction head" does NOT by itself guarantee the JEPA embedding *means* what the symbol says — this is the crux of auditability.** Marconato, Teso, Vergari & Passerini ("Not All Neuro-Symbolic Concepts Are Created Equal," NeurIPS 2023) characterize *reasoning shortcuts* as unintended optima: a model can attain high task accuracy while learning concepts with unintended semantics, identifying four conditions under which this arises. Their follow-up BEARS (UAI 2024) makes models aware of these shortcuts via uncertainty. Consequence: LeCun's §4.5.2 prediction-head hook is necessary but insufficient for provenance completeness, and the more decision-making we push into opaque JEPA embeddings (Proposal 1 → 3 reversed), the harder certification becomes.

4. **The "active agency" asymmetry is the strongest single argument for keeping the symbolic dictionary.** LeCun's §4.10 lists five modes of information gathering — passive observation, active foveation, passive agency, active egomotion, and active agency (the last being "sensory streams that are influenced by the agent's actions… [bringing] the exploration-exploitation dilemma to the forefront"). V-JEPA 2 was grounded in exactly this way: pre-trained on over 1 million hours of internet video, then post-trained on less than 62 hours of unlabeled robot videos from the Droid dataset and deployed zero-shot on Franka arms without task-specific reward (Assran et al., arXiv:2506.09985). A patient advocate is confined to modes 1–3; interventional experiments on patients to improve a world model are impermissible. Its causal knowledge must therefore come from the dictionary's provenance-bearing Type-C SCM fragments (Pearl-style do-calculus with edge→confidence and edge→ProvenanceRecord), not from self-supervised interventional learning.

5. **LeCun himself would prefer to dissolve the symbols — and says why — which is exactly what these proposals must resist for this use case.** In §8.3.3 ("Do We Need Symbols for Reasoning?") he writes that "the efficiency advantage of gradient-based search methods over gradient-free search methods motivates us to find ways for the world-model training procedure to find hierarchical representations with which the planning/reasoning problem constitutes a continuous relaxation of an otherwise discrete problem." For patient protection the calculus inverts: auditability and provenance dominate efficiency, so we deliberately keep discreteness where LeCun would relax it.

## Details

### The central design tension, resolved
LeCun's architecture is end-to-end differentiable and non-generative (energy = D(s_y, Pred(s_x,z)), a distance in *representation* space), and JEPA's whole point is to discard hard-to-predict detail. The dictionary is discrete, auditable and provenance-bearing. The resolution across all three proposals is the same principle applied at three intensities: **use JEPA for grounding (its genuine strength) and keep causal/ethical structure symbolic and co-resident (never dissolved into the embedding).** The three proposals differ only in how much of LeCun's *machinery around* the encoder is retained.

On the two specific integration options the requester flagged: option (a) — the dictionary's `conceptual_space_vector`/`neural_embedding` as the JEPA target space s_x, s_y — is the backbone of all three. Option (b) — the dictionary as a §4.5.2 prediction head — is central to Proposal 1: LeCun proposes "adding prediction heads that take s̃y as input and are trained to predict variables that are easily derived from the data and known to be relevant to the task," which is precisely how the dictionary biases the encoder toward advocacy-relevant structure. Option (c) — the dictionary as the §4.9 key-value world-state memory (Mem(q)=Σ_j c_j v_j with Match/Normalize/Update, sparse updates so "only the part of the world-state memory affected by the event is to be updated") — maps entry-URIs to memory slots and is used in Proposals 1–2. Option (d) — metaphor/glyph layer as JEPA-2 over a lexical JEPA-1 — is Proposal 1's hierarchy. Option (e) — Type-C SCM fragment as Pred(s,a,z) — is used in Proposals 1–2. Option (f) — Type-E warrant as Intrinsic Cost/Critic — is used in Proposals 1–2 and discussed critically below.

---

### PROPOSAL 1 — "H-JEPA-Advocate (Full Fidelity)"

**One-line thesis:** Preserve the entire six-module H-JEPA and mount the dictionary as (a) the target representation of a two-level H-JEPA, (b) §4.5.2 prediction heads that keep the embeddings auditable, and (c) the §4.9 key-value world-state memory — with the Beauchamp–Childress ethics warrant hard-wired as the immutable Intrinsic Cost.

**Architecture sketch (LeCun notation: ● observed, ○ latent, red = energy term, rounded = deterministic fn):**

```
              ┌──────────────── CONFIGURATOR ────────────────┐
              │ selects active interpretive scheme (causal /   │
              │ ethical-audit / metaphor / similarity /        │
              │ semiotic); sets cost weights                   │
              ▼                                                ▼
● x (case:        PERCEPTION      s_x[1] lexical/embedding (JEPA-1)
  record,   ────►  (encoder)  ──►     │
  consent,                            ▼
  note,                       Pred1(s_x[1], ○z1) ──[red D()]──► s_y[1]
  glyph)                              │   z1 = discrete causal-edge choice
                                      ▼
                              s_x[2] metaphor/SVO/glyph (JEPA-2)
                                      │
                              Pred2(s_x[2], ○z2) ──[red D()]──► s_y[2]
                                      │   z2 = discrete metaphor type
   ┌──────────────────────────────────┼────────────────────────────┐
   │ WORLD MODEL = Type-C SCM predictor + Ego/World split            │
   │ KEY-VALUE MEMORY (§4.9): Mem(q)=Σ_j c_j v_j; entries=slots;     │
   │ sparse Update(r,v,c)=cr+(1−c)v; new slot if q distant from keys │
   └──────────────────────────────────┼────────────────────────────┘
                                       ▼
   COST = INTRINSIC COST (immutable) ● Type-E warrant, {principle→polarity}
        + TRAINABLE CRITIC (○) predicted future ethics/utility cost
                                       ▼
                    ACTOR (Mode-2 planning; Mode-1 compiled advice)
```

**Component-by-component mapping**

| LeCun module | Dictionary element | What happens to it |
|---|---|---|
| Configurator | The five interpretive schemes | Becomes a concrete scheme-selector + cost-weight setter; the "most mysterious" module is finally pinned down |
| Perception | Case → `conceptual_space_vector` + `neural_embedding` | Encodes multimodal case into dictionary-aligned s_x |
| World model JEPA-1 | Lexical/embedding layer; Type-C SCM as Pred(s,a,z) | Short-horizon clinical-state prediction in representation space |
| World model JEPA-2 | Metaphor/glyph/SVO layer | Longer-horizon care-pathway abstraction (discards detail per LeCun) |
| Key-value memory (§4.9) | Dictionary entries (URI-keyed) | Each entry a memory slot; only affected slots updated |
| Intrinsic Cost (immutable) | Type-E Ethics-Warrant; four principles | Hard-wired ethical floor; claim ⊢ principle |
| Trainable Critic | Learned utility / predicted future ethics cost | Trained from stored (state, cost) episodes |
| Short-term memory | PROV-O provenance trace of current case | Stores state/cost history for the critic |
| Actor | Recommendation generator | Mode-2 deliberation with receding horizon |

**What is dropped and why / what is lost:** Almost nothing is dropped — this is the fidelity anchor of the series. The only genuine simplification is that the actor's *effectors* are advisory (it emits recommendations, not physical actions), and hierarchical planning under uncertainty is run in simulation over care-pathway representations rather than the world. *What is lost:* very little architecturally, but the cost is maximal engineering surface and the hardest certification story.

**Latent-variable / regularization story:** Two low-cardinality discrete latents — z1 = causal-edge choice, z2 = metaphor type (structural/orientational/ontological/Grady-primary/blend). Both satisfy LeCun's requirement to "minimize the information content of z" and match his k^t planning-tree picture; planning uses directed search/pruning (MCTS-like) as LeCun specifies for the k^t trajectory explosion. Continuous s_x, s_y are regularized against collapse by VICReg (variance/covariance/invariance) or, preferably, LeJEPA's SIGReg isotropic-Gaussian target; discrete latents are regularized by cardinality alone.

**Mode-1/Mode-2:** Mode-2 = full deliberative planning over care pathways using the SCM world model and ethics cost. Mode-1 = amortized/compiled quick advice for recurring cases, **gated by the ethical-audit reading**: any Mode-1 output with negative ethics polarity is vetoed back to Mode-2.

**Five interpretive schemes:** All five survive intact (uniquely). Causal = SCM world model; ethical-audit = intrinsic cost; metaphor-structural = JEPA-2; embedding-similarity = s_x/s_y distances; semiotic = glyph/Peirce layer in perception.

**Three footnotes:** Type G → perception encoder target (conceptual-space region + embedding centroid + Peirce-typed glyphs); Type C → world-model predictor; Type E → intrinsic cost. Clean and complete.

**Collapse risks & training criteria:** Highest surface → most collapse-prone at the JEPA joints. Apply all four LeCun criteria (maximize info of s_x about x; of s_y about y; predictability of s_y from s_x; minimize info of z); use VICReg or SIGReg. Reasoning-shortcut risk (Marconato et al., NeurIPS 2023) is acute here: a prediction head can hit near-100% accuracy while the embedding encodes unintended semantics; mitigate with BEARS-style uncertainty and by keeping SCM edges symbolic, not learned.

**Auditability:** Highest of the three, with a caveat — JEPA discards unpredictable detail, so the embedding is *not* a faithful provenance record. Auditability holds only because the symbolic dictionary sits *beside* the embeddings (URI-keyed, provenance-bearing slots); the embeddings are advisory, the symbols are the record of truth.

**Worked trace — "high fall risk":** Perception encodes the case into s_x aligned to the "high fall risk" entry's conceptual-space vector. JEPA-1 predicts near-term state (mobility decline) via z1 = (sedation → gait instability, confidence 0.8). JEPA-2 predicts the care-pathway abstraction; metaphor latent z2 = orientational ("decline = down"). Key-value memory updates only the fall-risk and medication slots (sparse Update). Intrinsic cost checks non-maleficence (polarity −) against a proposed sedation order; critic predicts future harm; actor recommends a fall-prevention protocol and flags the sedation order for review. Every step resolves to a URI-keyed, provenance-bearing entry.

---

### PROPOSAL 2 — "JEPA-Encoder + Symbolic Reasoner (Moderate)" — RECOMMENDED

**One-line thesis:** Keep a single (optionally 2-level) JEPA as a *perception encoder only*, drop the actor/critic/hierarchical-planning machinery, and hand off to the symbolic dictionary as an external reasoner — a Kautz Type-3 neuro-symbolic system.

**Architecture sketch:**

```
● case ──► JEPA ENCODER ──► s_x  (grounding only; Type G)
             │  VICReg/SIGReg anti-collapse
             ▼
        [handoff to SYMBOLIC DICTIONARY / knowledge graph]
             │
   Type-C SCM query (do-calculus, edge→confidence, edge→ProvenanceRecord)
             │
   Type-E ETHICS FILTER (Beauchamp-Childress {principle→polarity}, warrant ⊢)
             │
             ▼
        Recommendation + full graph trace
```

**What is dropped and why:**
- **Actor + Mode-2 planning + hierarchical k^t search** — dropped because a patient advocate advises rather than acts; no effector loop and no exploration, so model-predictive control over action sequences is unnecessary.
- **Trainable Critic** — dropped because reward is doubly problematic here: there is no reward signal from patients and learning one would be unethical (cf. Vamplew, Smith, Källström et al., "Scalar reward is not enough," *Autonomous Agents and Multi-Agent Systems* 36, 2022, arXiv:2112.15422, which argues scalar reward carries "unacceptable risks of unsafe or unethical behaviour").
- **Configurator as dynamic reconfigurer** — reduced to a static scheme-selector.

**What is lost:** Long-horizon care-pathway planning and skill compilation (no Mode-1 amortization). The system becomes reactive-plus-symbolic-reasoning rather than planning.

| LeCun module | Fate | Dictionary element |
|---|---|---|
| Perception/World-model encoder | KEPT (JEPA) | produces s_x for lexical + (optional) metaphor layers |
| Predictor | KEPT (thin, training-time) | Type-C SCM as the symbolic predictor at inference |
| Intrinsic Cost | KEPT as symbolic checker | Type-E ethics warrant applied post-hoc |
| Critic | DROPPED | — |
| Actor / planning | DROPPED | symbolic query over the knowledge graph |
| Key-value memory | KEPT | dictionary entries |
| Configurator | Reduced | static scheme choice |

**Latent variable:** Single discrete latent z = causal-edge choice. Metaphor typing becomes a downstream symbolic crawl (Gentner structure-mapping) rather than a JEPA-2 latent.

**Mode-1/Mode-2:** Mode-2 only, implemented *symbolically* (graph query + do-calculus), not by energy minimization over actions. The ethical-audit reading is a hard output filter.

**Five interpretive schemes:** All five survive, but causal/metaphor/semiotic run in the symbolic layer; only embedding-similarity lives in JEPA. This is arguably *more* auditable than Proposal 1 because reasoning is explicitly symbolic.

**Three footnotes:** Type G → JEPA encoder target; Type C → symbolic predictor; Type E → symbolic ethics filter. JEPA owns only grounding.

**Collapse & training:** Only the encoder can collapse; VICReg / Barlow-Twins / SIGReg on s_x suffices. No planning tree → no k^t explosion. Reasoning shortcuts are less dangerous because the SCM is symbolic and provenance-checked.

**Auditability:** Very high — the embedding is confined to grounding; all causal and ethical reasoning is symbolic and provenance-bearing.

**Worked trace — "informed consent":** JEPA encodes the consent document into s_x near the "informed consent" conceptual region (Type G grounding; Peirce symbol/index typing of the signature glyph). The symbolic layer runs Type-C: `capacity → valid_consent` (confidence, provenance). The Type-E ethics filter checks autonomy (polarity +) and confirms the warrant chain `claim ⊢ autonomy`. Output: "consent valid/invalid" with full graph trace. JEPA never touches the ethics.

---

### PROPOSAL 3 — "Single-JEPA Grounding Probe (Minimal)"

**One-line thesis:** A single non-hierarchical, non-actor JEPA whose only job is to map multimodal case inputs into the dictionary's conceptual-space/embedding coordinates (option (a)); all reasoning — causal, ethical, metaphor — lives entirely outside in the symbolic dictionary. JEPA is reduced to a collapse-resistant similarity encoder (essentially I-JEPA/LeJEPA as a frozen backbone).

**Architecture sketch:**

```
● case ──► SINGLE JEPA ENCODER ──► s_x ──► nearest dictionary region
              │ SIGReg (isotropic Gaussian, collapse-free by construction)
              ▼
        return matched entry + {Type G, Type C, Type E} footnotes
        (all reasoning done externally by the symbolic store)
```

**What is dropped and why:** Everything except perception + one predictor + non-contrastive regularizer. Configurator, world-model hierarchy, critic, actor, planning, and short-term memory as a cost-tuning device — all dropped, because the minimal viable contribution of JEPA to a patient advocate is robust, augmentation-free grounding of heterogeneous inputs (text, glyph, image) into a shared space.

**What is lost:** All prediction of future world states; all planning; all Mode-2 deliberation; any notion of the ethics module as an *architectural* guardrail (ethics becomes purely external post-processing). The "JEPA as world model" claim is abandoned — appropriately, since a duty-grounded world model cannot be learned from impermissible interventional data anyway.

| LeCun module | Fate |
|---|---|
| Perception encoder | KEPT (the whole system) |
| Predictor | KEPT (single, training-time only) |
| Everything else | DROPPED |
| Intrinsic Cost / Ethics | Wholly external symbolic checker |

**Latent variable:** z minimized to near-zero information (LeJEPA/SIGReg isotropic-Gaussian target); no discrete planning latent because there is no planning.

**Mode-1/Mode-2:** Neither in LeCun's sense — a pure encoder; "reasoning" is the dictionary's job.

**Five interpretive schemes:** Only embedding-similarity survives inside the model. Causal, ethical-audit, metaphor-structural and semiotic migrate entirely to the symbolic layer. This is the largest loss of JEPA-native readings.

**Three footnotes:** Only Type G relates to JEPA (its embedding centroid = the encoder target). Type C and Type E are entirely external.

**Collapse & training:** Simplest and most robust — a single encoder; SIGReg guarantees non-collapse by construction (isotropic Gaussian is proven optimal for downstream prediction risk), with a core implementation of ~50 lines of code (Balestriero & LeCun, arXiv:2511.08544). Reasoning shortcuts are irrelevant because JEPA makes no task decision.

**Auditability:** Paradoxically the highest *end-to-end* auditability, because JEPA is confined to a similarity function and every consequential decision is symbolic and provenance-bearing — but the lowest JEPA-fidelity.

**Worked trace — "high fall risk":** The encoder maps a new case to the nearest dictionary region and returns "high fall risk (similarity 0.91)" plus the three footnotes retrieved from the symbolic store. All causal/ethical reasoning is done by the dictionary. JEPA is a grounding lookup.

---

### Cross-cutting comparison

| Dimension | P1 Full H-JEPA | P2 Encoder + Reasoner (rec.) | P3 Minimal |
|---|---|---|---|
| Fidelity to LeCun | Highest | Moderate | Lowest |
| Fidelity to dictionary | High (co-resident) | Highest | High (symbol-dominant) |
| Auditability | High, with embedding caveat | Very high | Highest end-to-end |
| Trainability | Hardest | Moderate | Easiest |
| Data requirements | Highest | Moderate | Lowest |
| Engineering cost | Highest | Moderate | Lowest |
| What breaks first | JEPA joints collapse / reasoning shortcuts | encoder collapse | nothing structural; capability ceiling |

## Recommendations

**Adopt Proposal 2 now.** It captures JEPA's genuine, empirically demonstrated strength — robust multimodal grounding (I-JEPA, CVPR 2023; LeJEPA, 2025) — while keeping causal and ethical reasoning symbolic, auditable and provenance-bearing. This matters specifically for patient protection because (a) active-agency data collection on patients is impermissible, removing the data stream that grounds learned world models, and (b) opaque chain-of-thought reasoning is unacceptable in high-stakes care, and reasoning models "don't always say what they think" (Chen et al., Anthropic, arXiv:2505.05410, 2025).

**Staged plan and the thresholds that change it:**
1. **Ship Proposal 3 first as the MVP / safety fallback.** Use LeJEPA/SIGReg to guarantee a collapse-free grounding encoder in ~50 lines; wire all Type-C/Type-E reasoning to the symbolic store. Ship this if you need a certifiable system fast or if regulators require that no learned component participate in any consequential decision.
2. **Promote to Proposal 2** once the grounding encoder is stable and the knowledge graph's Type-C provenance coverage is high enough to answer real advocacy queries. This is the default production target.
3. **Escalate to Proposal 1 only if two thresholds are met:** (a) a validated, provenance-preserving method keeps JEPA embeddings faithful to symbolic semantics — i.e., defeats reasoning shortcuts (Marconato et al., NeurIPS 2023; BEARS, UAI 2024), measured by concept-leakage/identifiability metrics on held-out advocacy cases; and (b) a *legitimate simulation environment* (e.g., synthetic patient trajectories, never live patients) permits hierarchical planning without touching real patients. Absent both, Proposal 1's JEPA joints add collapse and shortcut risk that cannot be certified for deployment.
4. **Regression trigger:** fall back from 2 to 3 if encoder collapse or grounding instability cannot be controlled by VICReg/SIGReg, or if audits reveal the embedding is silently driving decisions that should be symbolic.

**On the ethics↔Intrinsic-Cost mapping (do this deliberately, with eyes open):** Encode the Type-E warrant / Beauchamp–Childress principles as the immutable Intrinsic Cost to obtain a hard, drift-proof ethical *floor* (LeCun requires the Intrinsic Cost to be immutable precisely to prevent behavioral drift). Do **not** treat it as the whole ethical reasoner: keep specification/balancing/reflective-equilibrium in the symbolic Type-E layer, where it can be inspected and contested. Let the Trainable Critic predict *future* utility only within the fixed ethical floor — never let it relax the floor.

## Caveats
- **CoT-faithfulness is not guaranteed by structure alone.** Anthropic's Chen et al. (arXiv:2505.05410, 2025) found Claude 3.7 Sonnet and DeepSeek R1 often fail to verbalize cues that changed their answers; an auditable *graph* structure mitigates but does not eliminate this, because the mapping from JEPA embedding to symbol can itself be a reasoning shortcut.
- **Causal claims are only as good as their provenance.** The Type-C SCM edges carry confidence and ProvenanceRecords; the system's trustworthiness is bounded by the quality of those records, not by JEPA.
- **Reasoning shortcuts are a first-class risk in Proposal 1.** A dictionary prediction head can achieve high accuracy with unintended concept semantics (Marconato et al., NeurIPS 2023; Bortolotti et al.), so the §4.5.2 hook does not by itself deliver interpretable grounding.
- **The immutable-cost ↔ ethics mapping is imperfect.** Beauchamp–Childress principles are *prima facie* and demand balancing; a fixed scalar cost loses that deliberation. It is a guardrail, not a moral agent.
- **The Maya-glyph analogy is structural, not literal**, and metaphor framing can itself harm (a documented risk in the source dictionary); the metaphor-typing layer must be auditable and overridable.
- **Scope:** consistent with the source deliverable, the center of gravity is patient protection, ethics and legitimacy; government-procurement and citizen-facing aspects are deliberately excluded.
- **Source-version note:** LeCun's position paper remains at v0.9.2 (2022-06-27); subsequent work (I-JEPA 2023, V-JEPA/V-JEPA 2 2024–2025, LeJEPA 2025) refines the *encoder/collapse* story but does not revise the six-module cognitive architecture, so the mappings above remain faithful to the specified source.

---

### Appendix — downloadable Markdown file

The complete deliverable is provided below as a single self-contained Markdown document. Copy the block between the markers into a file named `jepa-patient-advocate-proposals.md`.

````markdown
# Fitting a Multimodal Neuro-Symbolic Patient-Advocate Dictionary into JEPA / H-JEPA
## Three Graduated Architectural Proposals

> Source A: Yann LeCun, "A Path Towards Autonomous Machine Intelligence," v0.9.2, 2022-06-27.
> Source B: "Neuro-Symbolic Thought and a Multimodal Neuro-Symbolic Dictionary for Patient-Advocate AI."
> Scope: patient protection, ethics, legitimacy. Government/citizen-facing aspects excluded.

## 0. Academic synthesis
The tension is real: LeCun's architecture is anti-symbolic and end-to-end differentiable
(§8.3.3 prefers "continuous relaxation of an otherwise discrete problem" and gradient-based
search), while the dictionary is discrete, auditable and provenance-bearing. Reconciliation
rests on three literatures: (1) JEPA generalizes past pixels — I-JEPA (Assran et al., CVPR
2023), V-JEPA 2 (arXiv:2506.09985, 2025), Graph-JEPA (Skenderi et al., TMLR), and RiJEPA
neuro-symbolic JEPA (Huang & Raza, arXiv:2603.13265, 2026, with a clinical use case);
(2) non-contrastive collapse theory — VICReg (Bardes, Ponce & LeCun, ICLR 2022), Barlow
Twins (Zbontar et al., ICML 2021), LeJEPA (Balestriero & LeCun, arXiv:2511.08544, 2025,
isotropic-Gaussian SIGReg, ~50 LOC); (3) reasoning-shortcut theory — Marconato et al.
(NeurIPS 2023) + BEARS (UAI 2024), which show a prediction head does not guarantee intended
semantics. Kautz's taxonomy is the ruler: P1 ≈ Type-6, P2 = Type-3, P3 → Type-1/2.

Decisive asymmetry: LeCun's five modes of information gathering (passive observation, active
foveation, passive agency, active egomotion, active agency) include "active agency," which is
ethically impermissible on patients. The data stream that grounds V-JEPA 2 (>1M h video + <62 h
robot interaction, Droid) has no analog; causal knowledge must come from provenance-bearing
Type-C SCM fragments, not learned interventions.

## 1. Proposal 1 — H-JEPA-Advocate (Full Fidelity)
Thesis: keep the full six-module H-JEPA; dictionary = (a) target representation of a 2-level
H-JEPA, (b) §4.5.2 prediction heads, (c) §4.9 key-value memory; Type-E warrant = immutable
Intrinsic Cost.
- Configurator = interpretive-scheme selector; Perception = case→conceptual_space_vector +
  neural_embedding; World model JEPA-1 = lexical/embedding + Type-C SCM Pred(s,a,z);
  JEPA-2 = metaphor/SVO/glyph; Memory (§4.9) = URI-keyed slots, sparse Update(r,v,c)=cr+(1−c)v;
  Intrinsic Cost = Type-E {principle→polarity}; Critic = learned future cost; Actor = Mode-2.
- Latents: z1 = causal-edge choice (discrete), z2 = metaphor type (discrete). Anti-collapse:
  VICReg or SIGReg on s_x,s_y; planning uses MCTS-like pruning of the k^t tree.
- Mode-1 compiled advice gated by ethical-audit reading (negative polarity → veto to Mode-2).
- All five interpretive schemes survive. Type G→perception, Type C→world model, Type E→cost.
- Auditability high but embeddings are not provenance records; symbols sit beside them.
- Worked trace "high fall risk": see body.

## 2. Proposal 2 — JEPA-Encoder + Symbolic Reasoner (Moderate) [RECOMMENDED]
Thesis: JEPA as encoder only (Type G grounding); drop actor/critic/planning; symbolic
dictionary does causal + ethical reasoning (Kautz Type-3).
- Dropped: actor, Mode-2 energy planning, k^t search (advisor, not actor); trainable critic
  (no ethical reward; cf. Vamplew et al. 2022, "Scalar reward is not enough"); configurator
  reduced to static scheme choice.
- Lost: long-horizon planning + Mode-1 compilation.
- Latent: single z = causal-edge choice. Metaphor typing = downstream Gentner crawl.
- Five schemes survive; only embedding-similarity inside JEPA. Type G→encoder, C→symbolic
  predictor, E→symbolic ethics filter.
- Collapse: only encoder (VICReg/Barlow/SIGReg). Auditability very high.
- Worked trace "informed consent": encode→region (Type G); capacity→valid_consent (Type C);
  autonomy check + claim⊢autonomy (Type E); output with full graph trace.

## 3. Proposal 3 — Single-JEPA Grounding Probe (Minimal)
Thesis: one non-hierarchical, non-actor JEPA mapping cases to dictionary coordinates; all
reasoning external.
- Dropped: everything except perception + one predictor + regularizer.
- Lost: world-state prediction, planning, Mode-2, ethics-as-architecture.
- Latent: z≈0 info (SIGReg isotropic Gaussian, ~50 LOC, collapse-free by construction).
- Only embedding-similarity survives internally; only Type G relates to JEPA.
- Highest end-to-end auditability, lowest JEPA fidelity.
- Worked trace "high fall risk": nearest-region lookup + retrieved footnotes.

## 4. Cross-cutting comparison
| Dimension | P1 | P2 (rec.) | P3 |
|---|---|---|---|
| Fidelity to LeCun | Highest | Moderate | Lowest |
| Fidelity to dictionary | High | Highest | High |
| Auditability | High (caveat) | Very high | Highest e2e |
| Trainability | Hardest | Moderate | Easiest |
| Data requirements | Highest | Moderate | Lowest |
| Engineering cost | Highest | Moderate | Lowest |
| Breaks first | JEPA joints / shortcuts | encoder collapse | capability ceiling |

## 5. Recommendation
Adopt P2 now; ship P3 as MVP/fallback; escalate to P1 only if (a) reasoning shortcuts are
defeated with a provenance-preserving embedding-faithfulness method and (b) a legitimate
simulation environment enables planning without live patients. Encode Beauchamp-Childress as
the immutable Intrinsic Cost = hard floor only; keep balancing/specification symbolic.

## 6. Caveats
CoT-faithfulness not guaranteed by structure (Anthropic, arXiv:2505.05410); causal claims only
as good as provenance; reasoning shortcuts (Marconato et al., NeurIPS 2023); ethics-as-scalar
loses reflective-equilibrium balancing; Maya-glyph analogy is structural not literal; metaphor
framing can harm. LeCun paper remains v0.9.2; later JEPA work refines encoders, not the
six-module architecture.
````