"""EntryBuilder -- assemble a dictionary entry, and refuse to assemble a dishonest one.

Four gates run at `build()`. They are the whole reason a vendor-authored entry
is worth reading, so none of them is configurable off:

  1. PROVENANCE   every edge declares a tier; the tier caps its confidence.
  2. CONFLICT     a positive polarity needs one independent-tier edge. Adverse
                  polarities need none -- testimony against interest is credible
                  on its own, and requiring corroboration before a vendor may
                  report its own failure would suppress the contributions that
                  matter most.
  3. WARRANT      warrants may only cite claims that exist in the domain's
                  rules.yaml, and only for terms the telemetry found MET. A
                  claimed-but-unmet term is dropped and the reason recorded.
                  An unreachable harm gets `warrants: []` and escalates. The
                  engine never manufactures permissibility.
  4. RATIFICATION every contributed entry is `provisional`. A vendor cannot
                  ratify its own entry, and only ratified entries may feed
                  institution-level aggregation.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

from .config import ALL_TERMS, ContributorConfig
from .derive import Status, TermFinding, assess, derive_edges
from .observer import ObservationLog
from .provenance import (POSITIVE_CLAIM_REQUIRES_INDEPENDENT, ProvenanceError,
                         check_confidence, parse)
from .vocabulary import Vocabulary


class GateViolation(Exception):
    """A gate refused the entry. The message says which and why."""


@dataclass
class DomainNorms:
    principles: set[str]
    proposed: set[str]
    claims: dict[str, set[str]]        # claim -> principles it may discharge
    glyph_forms: set[str]
    logograms: set[str]
    superfixes: set[str]
    subfixes: set[str]

    @classmethod
    def load(cls, domain: str, root: str = ".") -> "DomainNorms":
        base = os.path.join(root, "domains", domain)
        def y(*p):
            path = os.path.join(base, *p)
            if not os.path.exists(path):
                raise GateViolation(
                    f"cannot find {path}. `dictionary_root` must point at a "
                    f"checkout of the dictionary repo -- the gates are enforced "
                    f"against that domain's real norms, not against a copy "
                    f"shipped inside the vendor product."
                )
            return yaml.safe_load(open(path, encoding="utf-8")) or {}
        pr = y("norms", "principles.yaml")["principles"]
        rules = y("norms", "rules.yaml")["warrants"]
        gl = y("glyphs", "vocab.yaml")
        claims: dict[str, set[str]] = {}
        for w in rules:
            claims.setdefault(w["claim"], set()).add(w["principle"])
        return cls(
            principles={p["id"] for p in pr},
            proposed={p["id"] for p in pr if p.get("proposed")},
            claims=claims,
            glyph_forms={v["form"] for v in gl.get("logograms", {}).values()},
            logograms=set(gl.get("logograms", {})),
            superfixes=set(gl.get("superfixes", {})),
            subfixes=set(gl.get("subfixes", {})),
        )


@dataclass
class BuildReport:
    """What the gates did. Print it; it is the audit trail for the entry."""
    withdrawn_warrants: list[tuple[str, str]] = field(default_factory=list)
    unregistered_nodes: list[tuple[str, str]] = field(default_factory=list)
    renamed_nodes: list[tuple[str, str]] = field(default_factory=list)
    escalated: bool = False
    needs_grounding: list[str] = field(default_factory=list)
    touches_proposed_principles: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = []
        for term, why in self.withdrawn_warrants:
            out.append(f"WARRANT WITHDRAWN  {term}: {why}")
        for sub, canon in self.renamed_nodes:
            out.append(f"NODE RENAMED       {sub} -> {canon}")
        for node, sugg in self.unregistered_nodes:
            out.append(f"NODE UNREGISTERED  {node}" + (f"  (did you mean {sugg}?)" if sugg else ""))
        for p in self.needs_grounding:
            out.append(f"NEEDS GROUNDING    {p}")
        for p in self.touches_proposed_principles:
            out.append(f"PROPOSED PRINCIPLE {p}: entry must escalate, not resolve")
        if self.escalated:
            out.append("ESCALATED          warrants: [] -- no rule reaches this harm; "
                       "a human normative decision is required before ratification")
        return out


class EntryBuilder:
    """Fluent assembly. Nothing is validated until `build()`."""

    def __init__(self, config: ContributorConfig, *, lemma: str, domain_sense: str):
        self.config = config
        self.norms = DomainNorms.load(config.domain, config.dictionary_root)
        self.vocab = Vocabulary.load(config.domain, config.dictionary_root)
        self.lemma = lemma
        self.domain_sense = domain_sense.strip()
        self._region: list[str] = []
        self._glyphs: list[dict] = []
        self._edges: list[dict] = []
        self._interventions: list[str] = []
        self._polarity: dict[str, str] = {}
        self._claimed_warrants: list[str] = []
        self._balancing = ""
        self._svo: dict | None = None
        self._glyph_block: dict | None = None
        self._metaphor = ""
        self._findings: list[TermFinding] = []

    # -- Type G ------------------------------------------------------------
    def grounding(self, *, conceptual_region: list[str], glyphs: list[dict]):
        self._region, self._glyphs = list(conceptual_region), list(glyphs)
        return self

    # -- Type C ------------------------------------------------------------
    def edge(self, cause: str, relation: str, effect: str, *,
             confidence: float, provenance: str):
        self._edges.append({"cause": cause, "relation": relation, "effect": effect,
                            "confidence": confidence, "provenance": provenance})
        return self

    def intervention(self, text: str):
        self._interventions.append(text)
        return self

    def from_observations(self, log: ObservationLog, *, threshold: float | None = None):
        """Derive edges and term findings from a closed observation window."""
        from .derive import DEFAULT_THRESHOLD
        self._findings = assess(self.config, log, threshold or DEFAULT_THRESHOLD)
        self._edges.extend(derive_edges(self.config, log, self._findings))
        return self

    # -- Type E ------------------------------------------------------------
    def polarity(self, **principle_to_sign: str):
        self._polarity.update(principle_to_sign)
        return self

    def claim_warrant(self, term: str):
        """Claim a governance term as a warrant. It survives only if the
        telemetry found it MET and the domain's rules recognise the claim."""
        self._claimed_warrants.append(term)
        return self

    def balancing_note(self, text: str):
        self._balancing = text.strip()
        return self

    # -- supplemental ------------------------------------------------------
    def svo(self, subject: str, verb: str, obj: str, derived_from: str):
        self._svo = {"subject": subject, "verb": verb, "obj": obj,
                     "derived_from": derived_from}
        return self

    def glyph_block(self, logogram: str, superfix: str = "", subfix: str = ""):
        self._glyph_block = {"logogram": logogram, "superfix": superfix, "subfix": subfix}
        return self

    def metaphor(self, text: str):
        self._metaphor = text
        return self

    # -- build -------------------------------------------------------------
    def build(self) -> tuple[dict, BuildReport]:
        r = BuildReport()
        if not self._edges:
            raise GateViolation(
                "entry has no causal edges. An entry with no Type-C footnote is a "
                "definition, and the dictionary already has one of those for every "
                "term it does not need."
            )

        # GATE 1 -- provenance tiers cap confidence.
        tiers = []
        for e in self._edges:
            try:
                check_confidence(e["provenance"], e["confidence"])
            except ProvenanceError as exc:
                raise GateViolation(f"edge {e['cause']} -> {e['effect']}: {exc}") from exc
            tier, ident, section = parse(e["provenance"])
            tiers.append(tier)
            if section == "needs_grounding":
                r.needs_grounding.append(e["provenance"])

        # GATE 2 -- conflict of interest on positive polarities.
        if POSITIVE_CLAIM_REQUIRES_INDEPENDENT:
            positives = [p for p, s in self._polarity.items() if s.startswith("+") and s != "+/-"]
            if positives and not any(t.independent for t in tiers):
                raise GateViolation(
                    f"entry asserts positive polarity on {positives} with no "
                    f"independent-tier edge. Tiers present: "
                    f"{sorted({t.name for t in tiers})}. A vendor reporting that its "
                    f"own deployment harmed someone is testifying against interest "
                    f"and is believed; a vendor reporting that it worked needs "
                    f"somebody else to say so. Commission an `audit:` tier finding, "
                    f"cite `acad:`/`press:`/`regulator:`, or drop the positive pole."
                )

        # GATE 3 -- warrants are earned, not declared.
        warrants: list[dict] = []
        by_term = {f.term: f for f in self._findings}
        for term in self._claimed_warrants:
            if term not in ALL_TERMS:
                raise GateViolation(f"unknown governance term {term!r}")
            principle = ALL_TERMS[term][1]
            if term not in self.norms.claims:
                raise GateViolation(
                    f"no rule in domains/{self.config.domain}/norms/rules.yaml "
                    f"defines the claim {term!r}. Propose the rule upstream first; "
                    f"a warrant the norm set does not recognise is the engine "
                    f"manufacturing permissibility."
                )
            if principle not in self.norms.claims[term]:
                raise GateViolation(
                    f"claim {term!r} does not bind principle {principle!r} in this "
                    f"domain's rules (it binds {sorted(self.norms.claims[term])})"
                )
            finding = by_term.get(term)
            if finding is None:
                r.withdrawn_warrants.append(
                    (term, "no observation window assessed it; call "
                           "`from_observations()` or drop the claim"))
                continue
            if finding.status is not Status.MET:
                r.withdrawn_warrants.append(
                    (term, f"{finding.status.value}"
                           + (f" (observed {finding.observed}, n={finding.n})"
                              if finding.observed is not None else "")
                           + (f" -- {finding.detail}" if finding.detail else "")))
                continue
            warrants.append({"claim": term, "principle": principle})

        if not warrants:
            r.escalated = True

        for p in self._polarity:
            if p not in self.norms.principles:
                raise GateViolation(
                    f"principle {p!r} is not declared in this domain "
                    f"({sorted(self.norms.principles)})")
            if p in self.norms.proposed:
                r.touches_proposed_principles.append(p)

        # GATE 4 -- node vocabulary.
        for e in self._edges:
            for key in ("cause", "effect"):
                res = self.vocab.resolve(e[key])
                if res.registered:
                    if res.renamed:
                        r.renamed_nodes.append((res.submitted, res.canonical))
                    e[key] = res.canonical
                else:
                    r.unregistered_nodes.append((res.submitted, res.suggestion))

        # glyph refs
        for g in self._glyphs:
            if g["form"] not in self.norms.glyph_forms:
                raise GateViolation(
                    f"glyph form {g['form']!r} is not declared in this domain's "
                    f"glyphs/vocab.yaml. Add it upstream in the same PR.")
        if self._glyph_block:
            gb = self._glyph_block
            for key, allowed in (("logogram", self.norms.logograms),
                                 ("superfix", self.norms.superfixes),
                                 ("subfix", self.norms.subfixes)):
                if gb.get(key) and gb[key] not in allowed:
                    raise GateViolation(f"glyph_block {key} {gb[key]!r} undeclared")

        if self._svo:
            provs = {e["provenance"] for e in self._edges}
            if self._svo["derived_from"] not in provs:
                raise GateViolation(
                    f"svo.derived_from {self._svo['derived_from']!r} matches no edge "
                    f"provenance in this entry. The SVO triplet is read OFF an edge; "
                    f"it is not an independent assertion.")

        # A contributed entry is an INSTANCE of a lemma, not a competing
        # definition of it. Ten deployments of the same category will produce
        # ten entries for `unreviewed_eligibility_determination`, and they must
        # not collide on one URI or silently overwrite the hand-written lemma
        # they are evidence for. The fragment carries the deployment; the
        # `instance_of` field carries the lemma the evidence attaches to, which
        # is what an institution-level aggregation would later group on.
        lemma_id = f"{_prefix(self.config.domain)}:{_slug(self.lemma)}"
        entry = {
            "id": f"{lemma_id}#{self.config.vendor_id}/{self.config.deployment_id}",
            "instance_of": lemma_id,
            "lemma": self.lemma,
            "domain": self.config.domain,
            "domain_sense": self.domain_sense,
            # GATE 4 -- ratification is not the contributor's to give.
            "status": "provisional",
            "contributed_by": {
                "vendor_id": self.config.vendor_id,
                "product": self.config.product,
                "deployment_id": self.config.deployment_id,
                "category": self.config.category,
                "docket_reference": self.config.docket_reference or None,
                "terms_selected": sorted(self.config.governance_terms),
            },
            "grounding": {"conceptual_region": self._region, "glyphs": self._glyphs},
            "causal": {"edges": self._edges, "interventions": self._interventions},
            "ethics": {
                "principle_polarity": self._polarity,
                "warrants": warrants,
                "balancing_note": self._balancing,
            },
            "svo": self._svo,
            "glyph_block": self._glyph_block,
            "metaphor_type": self._metaphor,
            "provenance": f"runtime:{self.config.deployment_id}",
            "term_findings": [
                {"term": f.term, "principle": f.principle, "status": f.status.value,
                 "observed": f.observed, "n": f.n, "detail": f.detail}
                for f in self._findings
            ],
        }
        return entry, r


_PREFIXES = {"gov_procurement": "gpr", "patient_advocacy": "pad",
             "agri_microfinance": "agm"}


def _prefix(domain: str) -> str:
    return _PREFIXES.get(domain, domain[:3])


def _slug(lemma: str) -> str:
    return "_".join(lemma.lower().replace("-", " ").split())
