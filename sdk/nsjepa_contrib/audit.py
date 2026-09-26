"""The auditor side: attestations, and why a vendor cannot write one.

WHAT WAS BROKEN. The `audit:` provenance tier is the load-bearing answer to
"who verifies the half of the governance posture a vendor cannot verify about
itself." It is marked independent, so it can carry a positive polarity where a
`vendor:` edge cannot. Until this module existed, the gate checked a STRING
PREFIX and nothing else, and this built cleanly:

    .adverse_to("operator")
    .edge("automated_data_match", "increases", "benefit_takeup_among_eligible",
          confidence=0.85, provenance="audit:we_hired_our_cousin#finding")
    .claim("meaningful_access", "+", because=["e1"])

A vendor asserting, at 0.85, on its own say-so, exactly the kind of favourable
claim the conflict-of-interest gate exists to refuse. The tier was
unforgeable in intention and trivially forgeable in fact.

The matching defect pointed the other way: `independent_governance_audit` is
`observable=False`, so `assess` always returned UNMEASURED, so `claim_warrant`
always withdrew it, so `coi_avoidance` could never be discharged by any code
path at all. The tier was simultaneously too easy to claim in an edge and
impossible to claim as a warrant.

HOW THIS FIXES IT, AND WHY THERE IS NO CRYPTOGRAPHY HERE. The obvious design is
a signed blob the auditor hands the vendor to embed. That needs key
distribution, a signing dependency inside a FedRAMP boundary, and it puts the
artifact in the hands of the party with a reason to be selective about which
attestations get embedded.

Independence is established instead by WHO FILED, not by what they signed. The
auditor submits their own attestation, as their own pull request, from their own
identity, to `contrib/audits/<auditor_id>/`. A vendor entry does not contain an
attestation; it CITES one. Both the builder and the receiving-side validator
resolve the citation against the repository and refuse it when the file is
absent, when it does not cover the term being claimed, or when its `auditor_id`
matches the `vendor_id` of the entry citing it.

That is weaker than a signature in one specific way, stated plainly rather than
papered over: it establishes that a distinct party filed a document, not that
the party is competent or that the audit happened. What it does buy is that a
vendor cannot manufacture independent support alone, in private, at build time —
which is the failure that was actually live.
"""
from __future__ import annotations

import datetime
import glob
import os
import re
from dataclasses import asdict, dataclass, field

import yaml

from ._io import read_yaml
from .config import ALL_TERMS, CATEGORIES, ConfigError

SCHEMA = "nsjepa-contrib-attestation/1"

#: Where attestations live, relative to the dictionary root. Deliberately beside
#: the vendor contributions rather than inside any one vendor's directory: an
#: attestation is about a deployment, it is not part of the vendor's submission,
#: and a reviewer should be able to list every audit of a deployment without
#: reading the vendor's tree.
AUDIT_DIR = os.path.join("contrib", "audits")

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class AttestationError(ValueError):
    """An attestation is malformed, missing, or does not support the claim."""


# --------------------------------------------------------------------------
# who is filing
# --------------------------------------------------------------------------
@dataclass
class AuditorConfig:
    """Identity of a third-party assessor.

    The counterpart to `ContributorConfig`, and the reason `EntryBuilder` no
    longer hardcodes its submitter as the vendor. `role` is what the
    conflict-of-interest gate reads.
    """
    auditor_id: str                     # stable, lowercase: "northwind-assurance"
    auditor_org: str                    # legal name, for the record
    dictionary_root: str = "."
    domain: str = "gov_procurement"
    role: str = "auditor"

    def __post_init__(self) -> None:
        if not _ID_RE.match(self.auditor_id or ""):
            raise ConfigError(
                "auditor_id must be a stable lowercase slug, e.g. 'northwind-assurance'")
        if not self.auditor_org.strip():
            raise ConfigError(
                "auditor_org is required. An attestation whose author is a slug and "
                "nothing else is not a document anyone can weigh")


# --------------------------------------------------------------------------
# what they file
# --------------------------------------------------------------------------
VERDICTS = ("met", "not_met", "inconclusive")


@dataclass
class AuditFinding:
    """One term, one verdict, and how it was reached.

    `method` is required and is not ceremony. A verdict of `met` on
    `data_residency_no_training` means something entirely different depending on
    whether the assessor read a contract clause or inspected a training
    manifest, and the corpus has no way to tell them apart afterwards unless the
    assessor says so at the time.
    """
    term: str
    verdict: str
    method: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.term not in ALL_TERMS:
            raise AttestationError(
                f"unknown governance term {self.term!r}; one of {sorted(ALL_TERMS)}")
        if self.verdict not in VERDICTS:
            raise AttestationError(
                f"verdict must be one of {VERDICTS}, not {self.verdict!r}. "
                f"`inconclusive` is a real answer and is the honest one whenever "
                f"scope or access did not permit a finding")
        if not self.method.strip():
            raise AttestationError(
                f"finding on {self.term!r} has no `method`. State how the verdict "
                f"was reached — a bare verdict is an opinion with a letterhead")


@dataclass
class Independence:
    """The declarations that make an `audit:` finding independent, or do not.

    `engaged_by` is the whole definition. A vendor-engaged assessment can be
    honest, careful, and correct, and it is not independent of the vendor, so it
    does not enter at the `audit:` tier. `build` refuses it rather than quietly
    downgrading, because a downgrade would let an assessor file at the wrong tier
    and never find out.
    """
    engaged_by: str = "issuing_body"        # issuing_body | vendor | other
    engagement_reference: str = ""          # PO or contract number
    fee_contingent_on_outcome: bool = False
    prior_engagements_with_vendor: int = 0

    def check(self) -> None:
        if self.engaged_by != "issuing_body":
            raise AttestationError(
                f"engaged_by={self.engaged_by!r}: only an assessment engaged and paid "
                f"by the issuing body enters at the `audit:` tier. That is not a "
                f"judgement about this assessor's integrity — it is what the tier "
                f"means. File a vendor-engaged review at the `vendor:` tier, where "
                f"its ceiling is 0.60 and it cannot carry a positive polarity.")
        if self.fee_contingent_on_outcome:
            raise AttestationError(
                "fee_contingent_on_outcome=True is disqualifying at this tier. An "
                "assessor paid more for one verdict than another is not independent "
                "of the verdict, whoever engaged them.")
        if not self.engagement_reference.strip():
            raise AttestationError(
                "engagement_reference is required: the PO, contract, or task order "
                "the issuing body raised. It is the only part of the independence "
                "claim a reviewer can check against something outside this file.")


@dataclass
class Attestation:
    """A third-party assessment of one deployment over one period."""
    auditor_id: str
    auditor_org: str
    deployment_id: str
    vendor_id: str                      # the SUBJECT of the audit, not its author
    domain: str = "gov_procurement"
    category: str = "CAT-09"
    period_from: str = ""               # ISO date
    period_to: str = ""
    issued_at: str = ""
    findings: list[AuditFinding] = field(default_factory=list)
    independence: Independence = field(default_factory=Independence)
    scope_note: str = ""
    schema: str = SCHEMA

    # -- identity ----------------------------------------------------------
    @property
    def id(self) -> str:
        return f"audit:{self.auditor_id}/{self.deployment_id}/{self.issued_at}"

    @property
    def terms(self) -> set[str]:
        return {f.term for f in self.findings}

    def verdict_for(self, term: str) -> str | None:
        for f in self.findings:
            if f.term == term:
                return f.verdict
        return None

    def finding_for(self, term: str) -> AuditFinding | None:
        for f in self.findings:
            if f.term == term:
                return f
        return None

    def provenance_for(self, term: str) -> str:
        """The provenance string an edge cites to rest on this attestation."""
        if term not in self.terms:
            raise AttestationError(
                f"{self.id} makes no finding on {term!r}; it covers {sorted(self.terms)}")
        return f"{self.id}#{term}"

    # -- validation --------------------------------------------------------
    def check(self) -> None:
        if self.schema != SCHEMA:
            raise AttestationError(f"unknown attestation schema {self.schema!r}")
        for f in ("auditor_id", "deployment_id", "vendor_id", "issued_at"):
            if not getattr(self, f):
                raise AttestationError(f"attestation is missing {f}")
        if self.auditor_id == self.vendor_id:
            raise AttestationError(
                f"auditor_id and vendor_id are both {self.auditor_id!r}. An "
                f"attestation is independent of the party it assesses or it is not "
                f"an attestation.")
        if self.category not in CATEGORIES:
            raise AttestationError(f"unknown category {self.category!r}")
        if not self.findings:
            raise AttestationError(
                "attestation has no findings. An assessment that reached no verdict "
                "on any term should say so as `inconclusive`, with the reason in "
                "`method` — filing nothing is indistinguishable from not looking")
        self.independence.check()

    # -- io ----------------------------------------------------------------
    def as_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return {"schema": d.pop("schema"), "id": d.pop("id"), **d}

    def path(self, root: str = ".") -> str:
        return os.path.join(root, AUDIT_DIR, self.auditor_id, self.deployment_id,
                            f"{self.issued_at}.audit.yaml")


HEADER = """\
# THIRD-PARTY ATTESTATION — filed by the assessor, not by the vendor.
#
# This file is the only way an `audit:` tier edge can enter the corpus. A vendor
# entry CITES it by id; it never contains one. Both the builder and the
# receiving-side validator resolve the citation against this directory and
# refuse it when the file is absent, when it makes no finding on the term being
# claimed, or when its auditor_id matches the citing entry's vendor_id.
#
# What that establishes: a distinct party filed this document, and the vendor
# could not have manufactured it alone at build time.
# What it does not: that the assessor is competent, or that the audit happened.
# Those are judgements for the reviewer, which is why the independence block and
# the per-finding `method` are mandatory and are the first things to read.
"""


def write(att: Attestation, root: str = ".") -> str:
    att.check()
    p = att.path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    body = yaml.safe_dump(att.as_dict(), sort_keys=False, width=88,
                          allow_unicode=True, default_flow_style=False)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(HEADER + body)
    return p


def _from_dict(d: dict) -> Attestation:
    d = dict(d)
    d.pop("id", None)
    findings = [AuditFinding(**f) for f in d.pop("findings", [])]
    ind = Independence(**d.pop("independence", {}) or {})
    return Attestation(findings=findings, independence=ind, **d)


def load(path: str) -> Attestation:
    att = _from_dict(read_yaml(path) or {})
    att.check()
    return att


def load_all(root: str = ".", deployment_id: str | None = None) -> dict[str, Attestation]:
    """Every attestation in the repo, by id. Malformed files are skipped loudly
    by `validate`, not here — this is the lookup path and must not raise on a
    neighbour's bad file."""
    out: dict[str, Attestation] = {}
    pattern = os.path.join(root, AUDIT_DIR, "**", "*.audit.yaml")
    for p in sorted(glob.glob(pattern, recursive=True)):
        try:
            att = load(p)
        except Exception:  # noqa: BLE001, S112
            # Deliberate. This is the lookup path: one malformed attestation
            # from another assessor must not make every other citation in the
            # repository unresolvable. `validate` reports bad files loudly.
            continue
        if deployment_id and att.deployment_id != deployment_id:
            continue
        out[att.id] = att
    return out


def resolve(provenance: str, attestations: dict[str, Attestation],
            *, citing_vendor_id: str | None) -> tuple[Attestation, str]:
    """Resolve an `audit:...#term` provenance, or explain why it does not hold.

    This is the function that closes the forgery hole. Every refusal below was
    reachable before it existed.
    """
    body = provenance.split(":", 1)[1] if ":" in provenance else provenance
    att_id, _, term = body.partition("#")
    att_id = f"audit:{att_id}"
    att = attestations.get(att_id)
    if att is None:
        raise AttestationError(
            f"{provenance} cites no attestation that exists. An `audit:` edge must "
            f"name a file under {AUDIT_DIR}/, filed separately by the assessor. "
            f"Known: {sorted(attestations) or '(none)'}. This is the tier that lets "
            f"a claim count as independent; it cannot be minted by writing the word.")
    if not term:
        raise AttestationError(
            f"{provenance} names an attestation but no term. Use "
            f"`att.provenance_for('<term>')` so the citation says which finding it "
            f"rests on — an attestation covering four terms supports four claims, "
            f"and a bare citation does not say which")
    if term not in att.terms:
        raise AttestationError(
            f"{att_id} makes no finding on {term!r}; it covers {sorted(att.terms)}")
    if citing_vendor_id and att.auditor_id == citing_vendor_id:
        raise AttestationError(
            f"{att_id} was filed by {att.auditor_id!r}, which is the vendor citing "
            f"it. Self-attestation at the audit tier is the exact failure this "
            f"resolution exists to prevent")
    verdict = att.verdict_for(term)
    if verdict == "inconclusive":
        raise AttestationError(
            f"{att_id} records {term!r} as INCONCLUSIVE. An inconclusive finding is "
            f"honest and is not support; cite it in the balancing note instead")
    return att, term


def today() -> str:
    """UTC, not local.

    An attestation's issued_at and an entry's review_by are calendar dates that
    appear in a public record and are compared across filers. Local time would
    make the same filing carry two different dates depending on who ran it.
    """
    # `datetime.UTC` is 3.11+, and sdk/pyproject.toml declares >=3.10 on
    # purpose: this package installs into vendor products whose Python is
    # not ours to choose. ruff reads the ROOT pyproject's 3.11 floor and
    # does not know this distribution has a lower one.
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()  # noqa: UP017
