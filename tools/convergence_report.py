#!/usr/bin/env python3
"""Measure the property the corpus rests on, and fail when it regresses.

The dictionary's claim to say anything structural is that entries written by
unrelated people from unrelated events converge on shared causal nodes without
coordination. That property is real, it is not automatic, and — this is the part
that makes a CI check necessary rather than nice — NOTHING FAILS WHEN IT DIES.
Every entry still validates. Every edge still has a tier. The graph simply stops
being one graph and becomes a pile of disjoint ones, and the only symptom is a
number nobody was looking at.

The first pass at the CAT-01..09 seed produced 71 nodes with zero overlap,
because the same capacity had been named `reliance_defense`,
`impeachment_of_the_record`, `contestation_of_grounds`, `right_of_appeal`, and
`informed_recourse` in five different entries. Nothing was wrong with any of
those names. That is exactly why this has to be measured.

Usage:
    python tools/convergence_report.py                 # print the report
    python tools/convergence_report.py --check         # fail on regression
    python tools/convergence_report.py --update-baseline
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import yaml

BASELINE = "eval/convergence_baseline.json"
PATTERNS = ("domains/*/entries/*.entry.yaml", "contrib/**/*.entry.yaml")


def collect(root: str = ".") -> dict:
    node_entries: dict[str, set[str]] = defaultdict(set)
    node_domains: dict[str, set[str]] = defaultdict(set)
    entries = 0
    registries: dict[str, set[str]] = {}

    for pattern in PATTERNS:
        for path in sorted(glob.glob(os.path.join(root, pattern), recursive=True)):
            e = yaml.safe_load(open(path, encoding="utf-8"))
            if not e or not (e.get("causal") or {}).get("edges"):
                continue
            entries += 1
            eid, domain = e.get("id", path), e.get("domain", "?")
            if domain not in registries:
                reg = os.path.join(root, "domains", domain, "vocab", "nodes.yaml")
                names: set[str] = set()
                if os.path.exists(reg):
                    data = yaml.safe_load(open(reg, encoding="utf-8")) or {}
                    for name, spec in (data.get("nodes") or {}).items():
                        names.add(name)
                        names.update((spec or {}).get("aliases", []) or [])
                registries[domain] = names
            for ed in e["causal"]["edges"]:
                for key in ("cause", "effect"):
                    base = str(ed[key]).split("@")[0]
                    node_entries[base].add(eid)
                    node_domains[base].add(domain)

    shared = {n: sorted(v) for n, v in node_entries.items() if len(v) > 1}
    cross = {n: sorted(node_entries[n]) for n in shared if len(node_domains[n]) > 1}
    recurring = set(shared)
    unregistered_recurring = sorted(
        n for n in recurring
        if not any(n in names for names in registries.values())
    )
    return {
        "entries": entries,
        "nodes": len(node_entries),
        "shared_nodes": len(shared),
        "cross_domain_nodes": len(cross),
        "shared": {n: v for n, v in sorted(shared.items())},
        "cross_domain": {n: v for n, v in sorted(cross.items())},
        "unregistered_recurring": unregistered_recurring,
        "convergence_ratio": round(len(shared) / len(node_entries), 4) if node_entries else 0.0,
    }


def report(m: dict) -> str:
    out = [
        "CONVERGENCE REPORT",
        f"  entries              {m['entries']}",
        f"  distinct nodes       {m['nodes']}",
        f"  shared (>1 entry)    {m['shared_nodes']}   ratio {m['convergence_ratio']}",
        f"  cross-domain         {m['cross_domain_nodes']}",
        "",
        "SHARED NODES",
    ]
    for n, v in m["shared"].items():
        mark = "  [CROSS-DOMAIN]" if n in m["cross_domain"] else ""
        out.append(f"  {n:<40} {len(v)} entries{mark}")
        for eid in v:
            out.append(f"      {eid}")
    if m["unregistered_recurring"]:
        out += ["", "RECURRING BUT UNREGISTERED — these are the forks in progress:"]
        out += [f"  {n}" for n in m["unregistered_recurring"]]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true",
                    help="fail if shared or cross-domain node count has dropped")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    m = collect(a.root)
    print(json.dumps(m, indent=2) if a.json else report(m))

    path = os.path.join(a.root, BASELINE)
    if a.update_baseline:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        keep = {k: m[k] for k in ("entries", "nodes", "shared_nodes",
                                  "cross_domain_nodes", "convergence_ratio")}
        keep["shared"] = sorted(m["shared"])
        keep["cross_domain"] = sorted(m["cross_domain"])
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(keep, fh, indent=2)
            fh.write("\n")
        print(f"\nbaseline written to {BASELINE}")
        return 0

    if not a.check:
        return 0
    if not os.path.exists(path):
        print(f"\nno baseline at {BASELINE}; run --update-baseline")
        return 1

    base = json.load(open(path, encoding="utf-8"))
    lost = sorted(set(base.get("shared", [])) - set(m["shared"]))
    lost_cross = sorted(set(base.get("cross_domain", [])) - set(m["cross_domain"]))
    fail = False
    if lost:
        fail = True
        print("\nREGRESSION: nodes that were shared are no longer shared:")
        for n in lost:
            print(f"  {n}")
        print("Usually this means a new or edited entry renamed one of them. "
              "Check domains/<domain>/vocab/nodes.yaml before merging — a rename "
              "here costs a structural finding and nothing else will report it.")
    if lost_cross:
        fail = True
        print("\nREGRESSION: cross-domain nodes lost: " + ", ".join(lost_cross))
        print("These are the rarest and most load-bearing thing in the corpus.")
    if m["unregistered_recurring"]:
        print("\nNOTE: recurring unregistered nodes (not a failure, but the place "
              "the next fork happens): " + ", ".join(m["unregistered_recurring"]))
    print("\nOK — no convergence regression" if not fail else "")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
