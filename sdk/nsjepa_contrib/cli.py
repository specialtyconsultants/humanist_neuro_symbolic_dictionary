"""`nsjepa-contrib` -- init, observe, validate, submit, bundle, verify, vocab."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import audit as _audit
from .config import (
    ALL_TERMS,
    CATEGORIES,
    GOVERNANCE_TERMS,
    PROPOSED_TERMS,
    ConfigError,
    ContributorConfig,
)
from .derive import Status, assess
from .observer import ObservationLog
from .validate import Level, has_errors, validate_file, validate_tree
from .version import __version__
from .vocabulary import Vocabulary


def _load_log(path: str) -> ObservationLog:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
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
            print(f"  {t:<32} discharges {ALL_TERMS[t].principle}")
        print("\nEvery resident-facing harm this deployment produces will carry "
              "`warrants: []`\nand escalate. That is the correct behaviour, not a "
              "misconfiguration -- but if\nthe solicitation did require a term, "
              "declare it here so the SDK can hold you to it.")
    return 0


def cmd_terms(a) -> int:
    def show(terms):
        for t, spec in terms.items():
            mark = "" if spec.observable else "  [NOT OBSERVABLE from inside a product]"
            print(f"  {t:<33} {spec.principle:<30}{mark}")
            print(f"  {'':<33} {spec.label}")

    print("Interstate Section 3 -- selectable today:")
    show(GOVERNANCE_TERMS)
    print("\nRequired by the CAT-01..09 seed, no checkbox on the form:")
    show(PROPOSED_TERMS)
    print(
        "\nHalf the governance surface the form sells cannot be verified by the "
        "party being\nasked to verify it. Three of the six selectable terms are "
        "facts about corporate\nconduct, hosting, and what was left OUT of a "
        "synthesis; no runtime probe reaches\nthem, and none ever will.\n"
        "\n  verifiable_governance_telemetry   buys the half a product can measure\n"
        "  independent_governance_audit      buys the half it cannot\n"
        "\nNeither is on the form today. The first is the term that makes this SDK "
        "worth\ninstalling; the second is the term that makes the rest of the "
        "posture checkable,\nand it closes with money rather than with code.")
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


def cmd_convergence(a) -> int:
    import subprocess
    cmd = [sys.executable, os.path.join(a.dictionary_root, "tools",
                                        "convergence_report.py"),
           "--root", a.dictionary_root] + (["--check"] if a.check else [])
    return subprocess.call(cmd)


def cmd_attest(a) -> int:
    """File a third-party attestation. The assessor runs this, not the vendor."""
    findings = []
    for spec in a.finding:
        parts = spec.split(":", 2)
        if len(parts) != 3:
            print(f"error: --finding wants term:verdict:method, got {spec!r}",
                  file=sys.stderr)
            return 2
        term, verdict, method = parts
        findings.append(_audit.AuditFinding(term=term, verdict=verdict, method=method))

    att = _audit.Attestation(
        auditor_id=a.auditor_id, auditor_org=a.auditor_org,
        deployment_id=a.deployment_id, vendor_id=a.vendor_id,
        domain=a.domain, category=a.category,
        period_from=a.period_from or "", period_to=a.period_to or "",
        issued_at=a.issued_at or _audit.today(),
        findings=findings, scope_note=a.scope_note or "",
        independence=_audit.Independence(
            engaged_by=a.engaged_by,
            engagement_reference=a.engagement_reference or "",
            fee_contingent_on_outcome=a.fee_contingent,
            prior_engagements_with_vendor=a.prior_engagements),
    )
    try:
        path = _audit.write(att, a.dictionary_root)
    except _audit.AttestationError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    print(f"  id: {att.id}")
    print()
    print("File this as YOUR OWN pull request, from your own identity. The vendor")
    print("cites it by id; they cannot embed it, and a citation naming an")
    print("attestation that is not in the repository is refused at build and")
    print("again on receipt.")
    print()
    print("Cite it as:")
    for f in att.findings:
        if f.verdict != "inconclusive":
            print(f"  {att.provenance_for(f.term)}")
    return 0


def cmd_audits(a) -> int:
    atts = _audit.load_all(a.dictionary_root, a.deployment)
    if not atts:
        print("no attestations found under " + _audit.AUDIT_DIR + "/")
        return 0
    for aid, att in sorted(atts.items()):
        print(f"{aid}")
        print(f"  {att.auditor_org}  audits {att.vendor_id}/{att.deployment_id}"
              f"  engaged_by={att.independence.engaged_by}")
        for f in att.findings:
            print(f"    {f.verdict:<13} {f.term}")
    return 0


def cmd_validate(a) -> int:
    findings = (validate_file(a.path, a.dictionary_root) if a.path
                else validate_tree(a.dictionary_root, a.pattern))
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
    v.add_argument("--pattern", default="contrib/**/*.entry.yaml",
                   help="glob relative to --dictionary-root")
    v.set_defaults(func=cmd_validate)

    c = sub.add_parser("convergence",
                       help="report shared causal nodes across the corpus")
    c.add_argument("--check", action="store_true",
                   help="fail if a previously shared node is no longer shared")
    c.set_defaults(func=cmd_convergence)

    at = sub.add_parser("attest",
                        help="file a third-party attestation (assessors only)")
    at.add_argument("--auditor-id", required=True)
    at.add_argument("--auditor-org", required=True)
    at.add_argument("--deployment-id", required=True)
    at.add_argument("--vendor-id", required=True, help="the subject of the audit")
    at.add_argument("--domain", default="gov_procurement")
    at.add_argument("--category", default="CAT-09", choices=sorted(CATEGORIES))
    at.add_argument("--finding", action="append", default=[], required=True,
                    metavar="TERM:VERDICT:METHOD",
                    help="repeatable; verdict is met|not_met|inconclusive")
    at.add_argument("--engaged-by", default="issuing_body",
                    choices=["issuing_body", "vendor", "other"])
    at.add_argument("--engagement-reference", help="PO or contract number")
    at.add_argument("--fee-contingent", action="store_true")
    at.add_argument("--prior-engagements", type=int, default=0)
    at.add_argument("--period-from"); at.add_argument("--period-to")
    at.add_argument("--issued-at"); at.add_argument("--scope-note")
    at.set_defaults(func=cmd_attest)

    au = sub.add_parser("audits", help="list third-party attestations in the repo")
    au.add_argument("--deployment")
    au.set_defaults(func=cmd_audits)

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
