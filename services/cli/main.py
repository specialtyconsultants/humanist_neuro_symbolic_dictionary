"""Entry point for the `nsjepa` console script.

    nsjepa list-domains
    nsjepa ground --domain patient_advocacy --input case.json
    nsjepa reason --domain gov_procurement --entry proc.yaml
    nsjepa audit  --trace last
"""
from __future__ import annotations

import argparse

from core.schemas import domain as dom


def main(argv=None):
    p = argparse.ArgumentParser(prog="nsjepa")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-domains")
    g = sub.add_parser("ground"); g.add_argument("--domain", required=True); g.add_argument("--input", required=True)
    r = sub.add_parser("reason"); r.add_argument("--domain", required=True); r.add_argument("--entry", required=True)
    a = sub.add_parser("audit");  a.add_argument("--trace", default="last")
    args = p.parse_args(argv)

    if args.cmd == "list-domains":
        # importing the domains package registers all packs
        import domains  # noqa: F401
        print("\n".join(dom.available()))
    else:
        raise SystemExit(f"'{args.cmd}' not yet implemented in scaffold")


if __name__ == "__main__":
    main()
