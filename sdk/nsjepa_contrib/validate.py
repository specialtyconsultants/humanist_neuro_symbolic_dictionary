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


def validate_entry(entry: dict, root: str = ".", where: str = "<entry>") -> list[Finding]:
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

    if entry.get("contributed_by") and entry.get("status") != "provisional":
        err("a contributed entry must be `provisional`; ratification is the "
            "domain owner's, not the contributor's")

    edges = entry["causal"]["edges"]
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
        if section == "needs_grounding":
            warn(f"{label}: open grounding target at confidence {e['confidence']}")
        if e["confidence"] >= 0.85 and not tier.independent and not tier.measured:
            warn(f"{label}: {e['confidence']} on non-independent tier '{tier.name}'")
        for key in ("cause", "effect"):
            res = vocab.resolve(e[key])
            if not res.registered:
                warn(f"node {e[key]!r} is unregistered in domains/{domain}/vocab/nodes.yaml"
                     + (f"; nearest is {res.suggestion!r}" if res.suggestion else ""))

    ethics = entry.get("ethics") or {}
    for p in (ethics.get("principle_polarity") or {}):
        if p not in norms.principles:
            err(f"principle {p!r} undeclared in this domain")
        elif p in norms.proposed:
            warn(f"principle {p!r} is `proposed`; entry must escalate, not resolve")
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


def validate_tree(root: str = ".", pattern: str = "contrib/**/*.entry.yaml") -> list[Finding]:
    out: list[Finding] = []
    for path in sorted(glob.glob(os.path.join(root, pattern), recursive=True)):
        out.extend(validate_file(path, root=root))
    return out


def has_errors(findings: list[Finding]) -> bool:
    return any(f.level is Level.ERROR for f in findings)
