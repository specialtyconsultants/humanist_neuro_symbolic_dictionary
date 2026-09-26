"""EntryBuilder -- assemble a dictionary entry, and refuse to assemble a dishonest one.

Four gates run at `build()`. They are the whole reason a vendor-authored entry
is worth reading, so none of them is configurable off:

  1. PROVENANCE   every edge declares a tier; the tier caps its confidence.
  2. CONFLICT     every polarity names the edges that earn it, and a claim needs
                  INDEPENDENT support unless it is adverse to the submitter.
                  Testimony against interest is credible on its own; a negative
                  finding aimed at somebody else is not testimony against
                  interest merely because it is negative.
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

from . import audit as _audit
from ._io import read_yaml
from .config import ALL_TERMS, ContributorConfig
from .derive import Status, TermFinding, assess, derive_edges
from .observer import ObservationLog
from .provenance import ProvenanceError, check_confidence, parse
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
    def load(cls, domain: str, root: str = ".") -> DomainNorms:
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
            return read_yaml(path) or {}
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
    cited_attestations: list[tuple[str, str, str]] = field(default_factory=list)
    touches_proposed_principles: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = []
        for term, why in self.withdrawn_warrants:
            out.append(f"WARRANT WITHDRAWN  {term}: {why}")
        for sub, canon in self.renamed_nodes:
            out.append(f"NODE RENAMED       {sub} -> {canon}")
        for node, sugg in self.unregistered_nodes:
            out.append(f"NODE UNREGISTERED  {node}" + (f"  (did you mean {sugg}?)" if sugg else ""))
        for aid, term, org in self.cited_attestations:
            out.append(f"AUDIT RESOLVED     {term} <- {aid} ({org})")
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
        self._polarity: dict[str, dict] = {}
        self._derived_support: dict[str, list[str]] = {}
        self._adverse_to: list[str] | None = None
        self._attestations = _audit.load_all(config.dictionary_root)
        self._cited_audits: dict[str, str] = {}      # attestation id -> term
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
             confidence: float, provenance: str, id: str = ""):
        """Add a causal edge. Returns self; the id is auto-assigned if omitted.

        Use `last_edge_id()` to cite it from a polarity claim."""
        self._edges.append({"id": id or f"e{len(self._edges) + 1}",
                            "cause": cause, "relation": relation, "effect": effect,
                            "confidence": confidence, "provenance": provenance})
        return self

    def last_edge_id(self) -> str:
        return self._edges[-1]["id"]

    def intervention(self, text: str):
        self._interventions.append(text)
        return self

    def from_observations(self, log: ObservationLog, *, threshold: float | None = None):
        """Derive edges and term findings from a closed observation window.

        Telemetry produces the edges AND the polarity claims those edges earn,
        already linked. A term found NOT_MET is an adverse finding on the
        principle it was meant to discharge, and the edges derived from that
        failure are exactly its support — so there is no step at which a person
        writes down a normative conclusion the graph does not reach.
        """
        from .derive import DEFAULT_THRESHOLD
        self._findings = assess(self.config, log, threshold or DEFAULT_THRESHOLD)
        before = len(self._edges)
        derived = derive_edges(self.config, log, self._findings)
        for i, e in enumerate(derived, start=before + 1):
            e["id"] = f"e{i}"
        self._edges.extend(derived)
        failed = {f.principle for f in self._findings if f.status is Status.NOT_MET}
        for principle in failed:
            self._derived_support.setdefault(principle, [])
            self._derived_support[principle].extend(e["id"] for e in derived)
        return self

    # -- Type E ------------------------------------------------------------
    def claim(self, principle: str, sign: str, *, because: list[str] | None = None):
        """Assert a polarity, naming the edges that earn it.

        `because` holds edge ids from this entry. It is not bookkeeping. Before
        it existed, Type G was checkable against the glyph vocabulary and Type C
        against its provenance tiers, while Type E was an assertion sitting next
        to the graph with no link to it — the only footnote a reader had to take
        on faith. A claim with nothing behind it is refused at build.
        """
        entry = self._polarity.setdefault(principle, {"polarity": sign,
                                                      "supported_by": []})
        entry["polarity"] = sign
        for eid in (because or []):
            if eid not in entry["supported_by"]:
                entry["supported_by"].append(eid)
        return self

    def polarity(self, **principle_to_sign: str):
        """Shorthand for `claim` with no explicit support. Kept because a
        contributor will reach for it; it builds only where `from_observations`
        supplied the support, and otherwise fails the gate saying so."""
        for principle, sign in principle_to_sign.items():
            self.claim(principle, sign)
        return self

    def audit_edge(self, cause: str, relation: str, effect: str, *,
                   attestation_id: str, term: str, confidence: float):
        """Add an edge resting on a third-party attestation filed separately.

        This is the only supported way to produce an `audit:` tier edge. The
        attestation is resolved against the repository at build time; it is not
        supplied by the caller, cannot be constructed by the caller, and is
        refused when its author is the vendor citing it. Before this existed the
        gate checked the string prefix, and a vendor could mint independent
        support for a favourable claim by writing the word `audit:`.
        """
        att = self._attestations.get(attestation_id)
        if att is None:
            raise GateViolation(
                f"no attestation {attestation_id!r} under "
                f"{_audit.AUDIT_DIR}/ in {self.config.dictionary_root!r}. The "
                f"assessor files it themselves, as their own pull request; you cite "
                f"it. Known: {sorted(self._attestations) or '(none)'}")
        prov = att.provenance_for(term)
        self._cited_audits[attestation_id] = term
        return self.edge(cause, relation, effect, confidence=confidence,
                         provenance=prov)

    def adverse_to(self, *parties: str):
        """Who this entry's findings cut against: vendor, operator, resident.

        Required on every contributed entry, and deliberately not defaulted.
        The independence requirement keys on it, because testimony against
        interest is credible on its own and a submitter's finding that is
        adverse only to somebody ELSE is not testimony against interest merely
        because it is phrased negatively. A vendor reporting "the county
        configured us to deprive first" files a negative finding that is
        favourable to the vendor, and it needs corroboration like any other
        favourable claim.
        """
        allowed = {"vendor", "operator", "resident"}
        bad = set(parties) - allowed
        if bad:
            raise GateViolation(f"unknown adverse_to parties {sorted(bad)}; "
                                f"one or more of {sorted(allowed)}")
        self._adverse_to = sorted(set(parties))
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
            tier, _ident, section = parse(e["provenance"])
            tiers.append(tier)
            if section == "needs_grounding":
                r.needs_grounding.append(e["provenance"])
            # An `audit:` edge is independent support, so it is the tier with a
            # reason to be forged. Resolve every one against an attestation
            # actually present in the repository and filed by somebody else.
            if tier.name == "audit":
                try:
                    att, term = _audit.resolve(
                        e["provenance"], self._attestations,
                        citing_vendor_id=getattr(self.config, "vendor_id", None))
                except _audit.AttestationError as exc:
                    raise GateViolation(str(exc)) from exc
                r.cited_attestations.append((att.id, term, att.auditor_org))

        # GATE 2 -- every polarity is earned by named edges, and a claim needs
        # INDEPENDENT support unless it is adverse to the party submitting it.
        #
        # The rule used to be stated on the sign of the claim: positives need
        # corroboration, negatives do not. That has a hole. A vendor reporting
        # "the county configured us to deprive first" is filing a NEGATIVE
        # finding that is adverse to the operator and favourable to the vendor,
        # and it sailed through at face value — which is precisely the
        # contribution a vendor has an incentive to file.
        if self._adverse_to is None:
            raise GateViolation(
                "entry does not declare `adverse_to`. Say who these findings cut "
                "against — any of vendor, operator, resident. It is not defaulted "
                "because the independence requirement keys on it, and a default "
                "would decide the question the contributor is supposed to answer."
            )
        by_id = {e["id"]: e for e in self._edges}
        # Derived from who is filing. It was hardcoded to "vendor", which made an
        # auditor submission structurally impossible to represent: an assessor's
        # findings are never adverse to the assessor, so every claim they filed
        # would have demanded independent support that they themselves were.
        submitter = getattr(self.config, "role", "vendor")
        against_submitter = submitter in self._adverse_to
        for principle, claim in self._polarity.items():
            support = claim["supported_by"] + self._derived_support.get(principle, [])
            support = list(dict.fromkeys(support))
            claim["supported_by"] = support
            if not support:
                raise GateViolation(
                    f"polarity {principle}={claim['polarity']!r} names no supporting "
                    f"edge. Cite the edges that earn it with "
                    f"`.claim({principle!r}, {claim['polarity']!r}, because=[...])`, "
                    f"or drop the claim. An unsupported normative assertion is the "
                    f"one thing in this schema nothing else can check."
                )
            missing = [e for e in support if e not in by_id]
            if missing:
                raise GateViolation(
                    f"polarity {principle} cites edge(s) {missing} that do not "
                    f"exist in this entry")
            positive = claim["polarity"] == "+"
            needs_independent = positive or not against_submitter
            if not needs_independent:
                continue
            usable = [by_id[e] for e in support]
            ok = []
            for e in usable:
                tier, _, _ = parse(e["provenance"])
                if tier.independent and (tier.can_support_positive or not positive):
                    ok.append(tier.name)
            if not ok:
                why = ("is positive" if positive else
                       f"is not adverse to the submitter (adverse_to="
                       f"{self._adverse_to})")
                raise GateViolation(
                    f"polarity {principle}={claim['polarity']!r} {why}, so it needs "
                    f"independent support, and its edges are all on "
                    f"{sorted({parse(by_id[e]['provenance'])[0].name for e in support})}. "
                    f"Commission an `audit:` finding under "
                    f"`independent_governance_audit`, cite "
                    f"`acad:`/`press:`/`regulator:`/`court:`, or drop the claim. "
                    f"Note that `analytic:` is independent and cannot support a "
                    f"positive polarity: defining your way to a favourable ethics "
                    f"footnote is the failure this excludes."
                )

        # GATE 3 -- warrants are earned, not declared.
        warrants: list[dict] = []
        by_term = {f.term: f for f in self._findings}
        for term in self._claimed_warrants:
            if term not in ALL_TERMS:
                raise GateViolation(f"unknown governance term {term!r}")
            principle = ALL_TERMS[term].principle
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
                    (term, ("no observation window assessed it; call "
                            "`from_observations()` or drop the claim")))
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
                "adverse_to": self._adverse_to,
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
