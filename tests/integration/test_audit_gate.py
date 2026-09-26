"""Deployment gate: nothing leaves this system without a warrant chain and provenance.

Enforced in CI (see .github/workflows/ci.yml). This was a single `xfail`
placeholder raising `AssertionError("wire to core.norms + services.audit once
implemented")`. It passed because failing was expected, so the one CI job that
went green checked nothing at all.

The engine still does not exist — `core/norms/engine.py` and `warrant.py` are
empty files and there are no recommendations to gate. The invariant, though, is
checkable one layer down and always was: the corpus is what a recommendation
would be derived FROM, and an unwarranted entry yields an unwarranted
recommendation however careful the engine is. So the gate runs over the corpus
now, and the recommendation half at the bottom activates by itself the moment
`eval/audit_traces/` contains anything.

DELIBERATELY NOT `nsjepa_contrib.validate`. That is the contributor's tool: it
grades findings WARN/ERROR, tolerates honestly-marked weakness, and is advisory
by design. This is the deployment gate. It depends on `core/` only — no vendor
SDK installed, and no vendor SDK able to relax it — it has no warning level, and
every assertion here is a hard fail.
"""
from __future__ import annotations

import glob
import json
import os

import pytest
import yaml


def _read_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)

from core.schemas.provenance import ProvenanceError, load_tiers, parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENTRY_GLOBS = ("domains/*/entries/*.entry.yaml", "contrib/**/*.entry.yaml")
TIERS = load_tiers()


def _entries():
    for pattern in ENTRY_GLOBS:
        for path in sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True)):
            entry = _read_yaml(path)
            if entry and (entry.get("causal") or {}).get("edges"):
                yield os.path.relpath(path, ROOT).replace("\\", "/"), entry


ENTRIES = list(_entries())
IDS = [p for p, _ in ENTRIES]


def _norms(domain):
    base = os.path.join(ROOT, "domains", domain, "norms")
    principles = _read_yaml(os.path.join(base, "principles.yaml"))["principles"]
    rules = _read_yaml(os.path.join(base, "rules.yaml"))["warrants"]
    claims: dict[str, set[str]] = {}
    for w in rules:
        claims.setdefault(w["claim"], set()).add(w["principle"])
    return {p["id"] for p in principles}, claims


def test_the_corpus_is_not_empty():
    """A gate over nothing is the placeholder this replaced."""
    assert ENTRIES, "no entries found; every assertion below would pass vacuously"


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_every_edge_carries_a_gradeable_provenance(path, entry):
    for e in entry["causal"]["edges"]:
        label = f"{e.get('cause')} -> {e.get('effect')}"
        assert e.get("id"), f"{label}: edge has no id, so no polarity can cite it"
        try:
            tier, _identifier, _section = parse(e["provenance"], TIERS)
        except ProvenanceError as exc:
            pytest.fail(f"{label}: {exc}")
        assert e["confidence"] <= tier.ceiling, (
            f"{label}: {e['confidence']} exceeds the {tier.name} ceiling {tier.ceiling}")


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_edge_ids_are_unique(path, entry):
    ids = [e.get("id") for e in entry["causal"]["edges"]]
    assert len(ids) == len(set(ids)), f"duplicate edge ids: {ids}"


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_every_polarity_is_earned_by_named_edges(path, entry):
    """The warrant chain, at the one place it can break without anyone noticing."""
    by_id = {e["id"]: e for e in entry["causal"]["edges"] if e.get("id")}
    for principle, claim in (entry["ethics"].get("principle_polarity") or {}).items():
        assert isinstance(claim, dict), (
            f"{principle}={claim!r} is a bare polarity naming no supporting edges")
        support = claim.get("supported_by") or []
        assert support, f"{principle} has an empty supported_by"
        missing = [s for s in support if s not in by_id]
        assert not missing, f"{principle} cites nonexistent edges {missing}"

        if claim.get("polarity") != "+":
            continue
        tiers = [parse(by_id[s]["provenance"], TIERS)[0] for s in support]
        assert any(t.independent and t.can_support_positive for t in tiers), (
            f"{principle} is positive and rests only on "
            f"{sorted({t.name for t in tiers})}; a positive claim needs "
            f"independent, non-analytic support")


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_warrants_resolve_or_escalate_explicitly(path, entry):
    """A missing warrants key is the failure. An empty list is the escalation."""
    principles, claims = _norms(entry["domain"])
    warrants = entry["ethics"].get("warrants")
    assert warrants is not None, (
        "ethics.warrants is missing. An empty list is the escalation signal and "
        "must be explicit — a missing key is indistinguishable from an oversight")
    for w in warrants:
        assert w["claim"] in claims, f"warrant {w['claim']!r} has no rule in this domain"
        assert w["principle"] in claims[w["claim"]], (
            f"{w['claim']!r} does not bind {w['principle']!r}")
    for p in (entry["ethics"].get("principle_polarity") or {}):
        assert p in principles, f"principle {p!r} undeclared in {entry['domain']}"


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_contributed_entries_are_provisional_and_expire(path, entry):
    if not entry.get("contributed_by"):
        return
    assert entry.get("status") == "provisional", (
        "a contributed entry must be provisional; ratification belongs to the "
        "domain owner, and only ratified entries may feed institution-level "
        "aggregation")
    assert entry.get("review_by"), (
        "a provisional contributed entry must carry review_by. It names a vendor, "
        "a deployment and usually an agency, and such a claim has no expiry unless "
        "somebody writes one down")


@pytest.mark.parametrize("path,entry", ENTRIES, ids=IDS)
def test_audit_tier_edges_cite_a_real_attestation(path, entry):
    """`audit:` is the tier that can carry a positive polarity, so it is the tier
    with a reason to be forged. The engine repeats the resolution rather than
    trusting that the contributor's toolchain ran."""
    vendor = (entry.get("contributed_by") or {}).get("vendor_id")
    attestations = {}
    for p in glob.glob(os.path.join(ROOT, "contrib", "audits", "**", "*.audit.yaml"),
                       recursive=True):
        att = _read_yaml(p) or {}
        if att.get("id"):
            attestations[att["id"]] = att

    for e in entry["causal"]["edges"]:
        tier, identifier, section = parse(e["provenance"], TIERS)
        if tier.name != "audit":
            continue
        att_id = f"audit:{identifier}"
        att = attestations.get(att_id)
        assert att is not None, (
            f"{e['provenance']} cites no attestation on file; "
            f"known {sorted(attestations) or '(none)'}")
        assert section, f"{e['provenance']} names no term"
        verdicts = {f["term"]: f["verdict"] for f in att.get("findings", [])}
        assert section in verdicts, f"{att_id} makes no finding on {section!r}"
        assert verdicts[section] != "inconclusive", (
            f"{att_id} records {section!r} as inconclusive; that is not support")
        assert att.get("auditor_id") != vendor, (
            f"{att_id} was filed by the vendor citing it")
        ind = att.get("independence") or {}
        assert ind.get("engaged_by") == "issuing_body", (
            f"{att_id} was engaged by {ind.get('engaged_by')!r}; only an assessment "
            f"engaged and paid by the issuing body enters at the audit tier")


# --- the recommendation layer, activating by itself -------------------------

TRACES = sorted(glob.glob(os.path.join(ROOT, "eval", "audit_traces", "*.json")))


@pytest.mark.skipif(
    not TRACES,
    reason="no traces yet; services.audit emits these once the engine lands, and "
           "this activates by itself when it does")
@pytest.mark.parametrize("trace_path", TRACES,
                         ids=[os.path.basename(t) for t in TRACES])
def test_recommendation_traces_carry_warrant_and_provenance(trace_path):
    """The gate this job was originally written for.

    No xfail. A skip that turns into a real assertion the moment a trace exists
    cannot rot the way a placeholder raising unconditionally does — that one was
    green for exactly as long as it stayed broken.
    """
    with open(trace_path, encoding="utf-8") as fh:
        trace = json.load(fh)
    for rec in trace.get("recommendations", []):
        assert rec.get("warrants"), (
            f"{rec.get('id')} carries no warrant chain; an unwarranted "
            f"recommendation must not be emitted at all")
        for w in rec["warrants"]:
            assert w.get("claim") and w.get("principle")
        assert rec.get("provenance"), f"{rec.get('id')} carries no provenance"
        for prov in rec["provenance"]:
            parse(prov, TIERS)
