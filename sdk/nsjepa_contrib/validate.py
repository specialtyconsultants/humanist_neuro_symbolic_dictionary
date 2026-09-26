"""Standalone validation of entry files -- the same checks a maintainer runs.

`build()` gates an entry the SDK assembled. This validates entries that already
exist on disk, whoever wrote them, so a vendor can run the receiving side's
check before submitting and a maintainer can run one command over a whole
contrib tree.

Findings are graded. ERROR blocks a merge. WARN does not: an honestly-marked
weak edge and an unregistered node are contributions that need attention, not
defects, and a tool that fails the build over them teaches contributors to
launder them into something that passes.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from enum import Enum

import yaml

from . import audit as _audit
from .builder import DomainNorms
from .provenance import ProvenanceError, check_confidence, parse
from .vocabulary import Vocabulary


class Level(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"


@dataclass
class Finding:
    level: Level
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.value:<5} {self.where}: {self.message}"


def validate_file(path: str, root: str = ".") -> list[Finding]:
    entry = yaml.safe_load(open(path, encoding="utf-8"))
    return validate_entry(entry, root=root, where=os.path.basename(path))


def validate_entry(entry: dict, root: str = ".", where: str = "<entry>",
                   recurring_nodes: set[str] | None = None) -> list[Finding]:
    """Validate one entry.

    `recurring_nodes` is the set of node names that appear in more than one
    entry in the corpus being checked. When it is supplied, an unregistered node
    is reported only if it is in that set. A node used once is local vocabulary
    and nobody's convergence depends on it; a warning that fires on every entry
    is a warning nobody reads, and the whole reason the registry exists is that
    the convergence property dies SILENTLY. Reporting it everywhere would be a
    different way of not reporting it.
    """
    out: list[Finding] = []

    def err(msg): out.append(Finding(Level.ERROR, where, msg))
    def warn(msg): out.append(Finding(Level.WARN, where, msg))

    for required in ("id", "lemma", "domain", "domain_sense", "causal", "ethics"):
        if not entry.get(required):
            err(f"missing required field {required!r}")
    if not entry.get("causal", {}).get("edges"):
        err("no causal edges")
    if out and any(f.level is Level.ERROR for f in out):
        return out

    domain = entry["domain"]
    try:
        norms = DomainNorms.load(domain, root)
    except Exception as exc:
        err(f"cannot load domain norms: {exc}")
        return out
    vocab = Vocabulary.load(domain, root)
    _attestations = _audit.load_all(root)

    if entry.get("contributed_by") and entry.get("status") != "provisional":
        err("a contributed entry must be `provisional`; ratification is the "
            "domain owner's, not the contributor's")

    edges = entry["causal"]["edges"]
    seen_unregistered: set[str] = set()
    provs = set()
    for e in edges:
        label = f"{e.get('cause')} --{e.get('relation')}--> {e.get('effect')}"
        try:
            check_confidence(e["provenance"], e["confidence"])
            tier, _, section = parse(e["provenance"])
        except (ProvenanceError, KeyError) as exc:
            err(f"{label}: {exc}")
            continue
        provs.add(e["provenance"])
        # The receiving side repeats the builder's audit resolution rather than
        # trusting that it ran. A contribution can arrive by any route — an
        # air-gapped bundle, a hand-edited file, a fork of an older SDK — and
        # the tier that can carry a positive polarity is the one worth checking
        # twice.
        if tier.name == "audit":
            try:
                att, term = _audit.resolve(
                    e["provenance"], _attestations,
                    citing_vendor_id=(entry.get("contributed_by") or {}).get("vendor_id"))
            except _audit.AttestationError as exc:
                err(f"{label}: {exc}")
            else:
                if att.deployment_id != (entry.get("contributed_by") or {}).get(
                        "deployment_id", att.deployment_id):
                    err(f"{label}: {att.id} attests deployment "
                        f"{att.deployment_id!r}, not this entry's")
        if section == "needs_grounding":
            warn(f"{label}: open grounding target at confidence {e['confidence']}")
        if e["confidence"] >= 0.85 and not tier.independent and not tier.measured:
            warn(f"{label}: {e['confidence']} on non-independent tier '{tier.name}'")
        for key in ("cause", "effect"):
            res = vocab.resolve(e[key])
            if res.registered or e[key] in seen_unregistered:
                continue
            base = e[key].split(vocab.separator)[0]
            if recurring_nodes is not None and base not in recurring_nodes:
                continue
            seen_unregistered.add(e[key])
            warn(f"node {e[key]!r} recurs across entries and is unregistered in "
                 f"domains/{domain}/vocab/nodes.yaml"
                 + (f"; nearest is {res.suggestion!r}" if res.suggestion else ""))

    ethics = entry.get("ethics") or {}
    contributed = bool(entry.get("contributed_by"))
    adverse_to = set(ethics.get("adverse_to") or [])
    if contributed and not adverse_to:
        err("contributed entry does not declare ethics.adverse_to. The "
            "independence requirement keys on who the findings cut against, and "
            "a default would decide the question the contributor must answer")
    against_submitter = (not contributed) or ("vendor" in adverse_to)

    by_id = {e.get("id"): e for e in edges if e.get("id")}
    if len(by_id) != len(edges):
        err("every causal edge needs a unique `id`, so the ethics footnote can "
            "cite the edges that earn each polarity")

    for p, claim in (ethics.get("principle_polarity") or {}).items():
        if p not in norms.principles:
            err(f"principle {p!r} undeclared in this domain")
            continue
        if p in norms.proposed:
            warn(f"principle {p!r} is `proposed`; entry must escalate, not resolve")
        if not isinstance(claim, dict):
            err(f"polarity {p}={claim!r} names no supporting edges. Write it as "
                f"{{polarity: {claim!r}, supported_by: [e1, ...]}} -- an "
                f"unsupported normative claim is the one thing in this schema "
                f"that nothing else can check")
            continue
        support = list(claim.get("supported_by") or [])
        sign = claim.get("polarity")
        if not support:
            err(f"polarity {p}={sign!r} has an empty supported_by")
            continue
        missing = [e for e in support if e not in by_id]
        if missing:
            err(f"polarity {p} cites edge(s) {missing} that do not exist here")
            continue
        positive = sign == "+"
        if not positive and against_submitter:
            continue
        ok = []
        for eid in support:
            try:
                tier, _, _ = parse(by_id[eid]["provenance"])
            except ProvenanceError:
                continue
            if tier.independent and (tier.can_support_positive or not positive):
                ok.append(tier.name)
        if not ok:
            why = ("is positive" if positive
                   else f"is not adverse to the submitter (adverse_to={sorted(adverse_to)})")
            err(f"polarity {p}={sign!r} {why} and rests only on non-independent "
                f"support. Commission an `audit:` finding under "
                f"`independent_governance_audit`, cite "
                f"`acad:`/`press:`/`regulator:`/`court:`, or drop the claim")

    # ---- correction and retirement -----------------------------------------
    status = entry.get("status")
    if status == "retired" and not (entry.get("retired_reason") or "").strip():
        err("a retired entry must carry `retired_reason`. Retirement without a "
            "stated reason is deletion with extra steps, and the corpus cannot "
            "learn from it")
    if entry.get("superseded_by") and status != "retired":
        err("an entry with `superseded_by` must be `retired`; two live entries "
            "making the same claim is how a corrected finding keeps circulating")
    if status == "provisional" and contributed and not entry.get("review_by"):
        err("a provisional contributed entry must carry `review_by` (ISO date). "
            "It names a vendor, a deployment, and usually an agency, and a "
            "provisional finding about a real party is a claim with no expiry "
            "unless somebody writes one down")
    elif status == "provisional" and not entry.get("review_by"):
        warn("provisional with no `review_by`. Set one if this entry names a "
             "living person or an identifiable institution")

    warrants = ethics.get("warrants")
    if warrants is None:
        err("ethics.warrants is missing; an empty list is the escalation signal "
            "and must be explicit")
    elif warrants == []:
        warn("warrants: [] -- escalated; no rule reaches this harm")
    else:
        for w in warrants:
            if w["claim"] not in norms.claims:
                err(f"warrant claim {w['claim']!r} has no rule in this domain")
            elif w["principle"] not in norms.claims[w["claim"]]:
                err(f"claim {w['claim']!r} does not bind {w['principle']!r}")

    for g in (entry.get("grounding") or {}).get("glyphs", []):
        if g.get("form") not in norms.glyph_forms:
            err(f"glyph form {g.get('form')!r} undeclared")
    gb = entry.get("glyph_block") or {}
    for key, allowed in (("logogram", norms.logograms), ("superfix", norms.superfixes),
                         ("subfix", norms.subfixes)):
        if gb.get(key) and gb[key] not in allowed:
            err(f"glyph_block {key} {gb[key]!r} undeclared")

    svo = entry.get("svo") or {}
    if svo.get("derived_from") and svo["derived_from"] not in provs:
        err(f"svo.derived_from {svo['derived_from']!r} matches no edge provenance")

    if not (ethics.get("balancing_note") or "").strip():
        warn("no balancing_note. Every entry here has a competing good worth "
             "conceding; an entry with none is usually one that has not looked")

    return out


def recurring_nodes(root: str = ".", patterns: tuple[str, ...] =
                    ("domains/*/entries/*.entry.yaml", "contrib/**/*.entry.yaml")
                    ) -> set[str]:
    """Node names appearing in more than one entry anywhere in the corpus."""
    from collections import defaultdict
    seen: dict[str, set[str]] = defaultdict(set)
    for pattern in patterns:
        for path in glob.glob(os.path.join(root, pattern), recursive=True):
            try:
                e = yaml.safe_load(open(path, encoding="utf-8"))
                for ed in (e.get("causal") or {}).get("edges", []):
                    for k in ("cause", "effect"):
                        seen[str(ed[k]).split("@")[0]].add(e.get("id", path))
            except Exception:
                continue
    return {n for n, v in seen.items() if len(v) > 1}


def validate_tree(root: str = ".", pattern: str = "contrib/**/*.entry.yaml") -> list[Finding]:
    out: list[Finding] = []
    recurring = recurring_nodes(root)
    for path in sorted(glob.glob(os.path.join(root, pattern), recursive=True)):
        entry = yaml.safe_load(open(path, encoding="utf-8"))
        out.extend(validate_entry(entry, root=root, where=os.path.basename(path),
                                  recurring_nodes=recurring))
    return out


def has_errors(findings: list[Finding]) -> bool:
    return any(f.level is Level.ERROR for f in findings)
