"""`nsjepa-contrib` -- init, observe, validate, submit, bundle, verify, vocab."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .config import (ALL_TERMS, CATEGORIES, GOVERNANCE_TERMS, PROPOSED_TERMS,
                     ConfigError, ContributorConfig)
from .derive import Status, assess
from .observer import ObservationLog
from .validate import Level, has_errors, validate_file, validate_tree
from .version import __version__
from .vocabulary import Vocabulary


def _load_log(path: str) -> ObservationLog:
    raw = json.load(open(path, encoding="utf-8"))
    raw.pop("review_latency_seconds", None)
    known = ObservationLog.__dataclass_fields__
    return ObservationLog(**{k: v for k, v in raw.items() if k in known})


def cmd_init(a) -> int:
    cfg = ContributorConfig(
        vendor_id=a.vendor_id, product=a.product, deployment_id=a.deployment_id,
        domain=a.domain, category=a.category, issuing_body=a.issuing_body or "",
        docket_reference=a.docket or "", governance_terms=a.terms or [],
        dictionary_root=a.dictionary_root, offline=a.offline)
    path = cfg.save(a.out)
    print(f"wrote {path}")
    unclaimed = sorted(set(GOVERNANCE_TERMS) - set(cfg.governance_terms))
    if unclaimed:
        print("\nSelectable terms NOT claimed by this deployment:")
        for t in unclaimed:
            print(f"  {t:<32} discharges {ALL_TERMS[t][1]}")
        print("\nEvery resident-facing harm this deployment produces will carry "
              "`warrants: []`\nand escalate. That is the correct behaviour, not a "
              "misconfiguration -- but if\nthe solicitation did require a term, "
              "declare it here so the SDK can hold you to it.")
    return 0


def cmd_terms(a) -> int:
    print("Interstate Section 3 -- selectable today:")
    for t, (label, principle) in GOVERNANCE_TERMS.items():
        print(f"  {t:<32} {principle:<30} {label}")
    print("\nRequired by the CAT-01..09 seed, no checkbox on the form:")
    for t, (label, principle) in PROPOSED_TERMS.items():
        print(f"  {t:<32} {principle:<30} {label}")
    return 0


def cmd_assess(a) -> int:
    cfg = ContributorConfig.load(a.config)
    findings = assess(cfg, _load_log(a.log))
    width = max(len(f.term) for f in findings)
    bad = 0
    for f in findings:
        if f.status is Status.NOT_CLAIMED and not a.all:
            continue
        obs = "" if f.observed is None else f"  observed={f.observed} n={f.n}"
        print(f"{f.status.value.upper():<12} {f.term:<{width}}{obs}")
        if f.detail:
            print(f"{'':<12} {f.detail}")
        bad += f.status is Status.NOT_MET
    print(f"\n{bad} claimed term(s) not met in production.")
    if bad:
        print("Warrants for those terms will be WITHDRAWN by the builder. The "
              "entry will\nrecord that the deployment did not meet a term its "
              "solicitation required.")
    return 0


def cmd_validate(a) -> int:
    findings = (validate_file(a.path, a.dictionary_root) if a.path
                else validate_tree(a.dictionary_root))
    for f in findings:
        print(f)
    errors = sum(f.level is Level.ERROR for f in findings)
    warns = len(findings) - errors
    print(f"\n{errors} error(s), {warns} warning(s)")
    if warns and not errors:
        print("Warnings do not block. An honestly-marked weak edge is a "
              "contribution;\na tool that failed the build over one would teach "
              "contributors to hide it.")
    return 1 if has_errors(findings) else 0


def cmd_vocab(a) -> int:
    v = Vocabulary.load(a.domain, a.dictionary_root)
    if a.resolve:
        for name in a.resolve:
            r = v.resolve(name)
            if r.registered:
                mark = "->" if r.renamed else "=="
                print(f"{name} {mark} {r.canonical}")
                if v.gloss(r.canonical):
                    print(f"     {v.gloss(r.canonical)}")
            else:
                sugg = f"  (nearest: {r.suggestion})" if r.suggestion else ""
                print(f"{name} UNREGISTERED{sugg}")
        return 0
    print(f"{v.size} canonical node(s) registered for {a.domain}")
    return 0


def cmd_bundle(a) -> int:
    from .submit import bundle as b
    key = os.environ.get("NSJEPA_BUNDLE_HMAC_KEY", "").encode() or None
    res = b.pack(a.entries, a.out, vendor_id=a.vendor_id,
                 deployment_id=a.deployment_id, sdk_version=__version__,
                 hmac_key=key, root=a.dictionary_root)
    print(f"wrote {res.path}  ({res.files} file(s), signed={res.signed})")
    if not res.signed:
        print("Unsigned. Set NSJEPA_BUNDLE_HMAC_KEY to seal it; the receiving "
              "side will\nreport `signed: False` rather than implying an "
              "integrity guarantee it lacks.")
    return 0


def cmd_verify(a) -> int:
    from .submit import bundle as b
    key = os.environ.get("NSJEPA_BUNDLE_HMAC_KEY", "").encode() or None
    res = b.verify(a.bundle, hmac_key=key)
    print(f"signed={res.signed}  ok={res.ok}")
    for p in res.problems:
        print(f"  {p}")
    return 0 if res.ok else 1


def cmd_submit(a) -> int:
    from .submit import github as gh
    cfg = ContributorConfig.load(a.config)
    if cfg.offline:
        print("config sets offline=true; use `nsjepa-contrib bundle` instead.")
        return 2
    findings = []
    for path in a.entries:
        findings.extend(validate_file(path, cfg.dictionary_root))
    if has_errors(findings):
        for f in findings:
            print(f)
        print("\nrefusing to submit an entry that does not validate")
        return 1
    sub = gh.submit(a.entries, vendor_id=cfg.vendor_id,
                    deployment_id=cfg.deployment_id, token=gh.token_from_env(),
                    upstream=a.upstream, fork=a.fork, root=cfg.dictionary_root)
    print(f"opened {sub.url}\nbranch {sub.branch}, {len(sub.files)} file(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("nsjepa-contrib", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--dictionary-root", default=os.environ.get("NSJEPA_DICTIONARY_ROOT", "."))
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="write a contributor config")
    i.add_argument("--vendor-id", required=True)
    i.add_argument("--product", required=True)
    i.add_argument("--deployment-id", required=True)
    i.add_argument("--domain", default="gov_procurement")
    i.add_argument("--category", default="CAT-09", choices=sorted(CATEGORIES))
    i.add_argument("--issuing-body")
    i.add_argument("--docket")
    i.add_argument("--terms", nargs="*", choices=sorted(ALL_TERMS))
    i.add_argument("--offline", action="store_true")
    i.add_argument("--out", default="nsjepa_contrib.json")
    i.set_defaults(func=cmd_init)

    t = sub.add_parser("terms", help="list governance terms and what they discharge")
    t.set_defaults(func=cmd_terms)

    a_ = sub.add_parser("assess", help="score an observation window against claimed terms")
    a_.add_argument("--config", default="nsjepa_contrib.json")
    a_.add_argument("--log", required=True, help="ObservationLog JSON")
    a_.add_argument("--all", action="store_true", help="include unclaimed terms")
    a_.set_defaults(func=cmd_assess)

    v = sub.add_parser("validate", help="validate entries (default: whole contrib/ tree)")
    v.add_argument("path", nargs="?")
    v.set_defaults(func=cmd_validate)

    vo = sub.add_parser("vocab", help="resolve node names against the canonical registry")
    vo.add_argument("--domain", default="gov_procurement")
    vo.add_argument("resolve", nargs="*")
    vo.set_defaults(func=cmd_vocab)

    b = sub.add_parser("bundle", help="pack entries for air-gapped transfer")
    b.add_argument("entries", nargs="+")
    b.add_argument("--out", required=True)
    b.add_argument("--vendor-id", required=True)
    b.add_argument("--deployment-id", required=True)
    b.set_defaults(func=cmd_bundle)

    ve = sub.add_parser("verify", help="verify a bundle on arrival")
    ve.add_argument("bundle")
    ve.set_defaults(func=cmd_verify)

    s = sub.add_parser("submit", help="open a PR against the common repo")
    s.add_argument("entries", nargs="+")
    s.add_argument("--config", default="nsjepa_contrib.json")
    s.add_argument("--upstream", default="specialtyconsultants/humanist_neuro_symbolic_dictionary")
    s.add_argument("--fork")
    s.set_defaults(func=cmd_submit)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
