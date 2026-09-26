# `contrib/audits/` — third-party attestations

An attestation is filed **by the assessor**, as the assessor's own pull request,
from the assessor's own identity. A vendor never files one and never embeds one.

```
contrib/audits/<auditor_id>/<deployment_id>/<issued_at>.audit.yaml
```

## Why this directory exists

The `audit:` provenance tier is marked independent, which means it can carry a
positive polarity where a `vendor:` edge cannot. It is the load-bearing answer
to *who verifies the half of the governance posture a vendor cannot verify about
itself* — `exit_ready_no_lock_in`, `data_residency_no_training`,
`minority_view_preservation` are facts about corporate conduct, hosting, and
what was left out of a synthesis, and no runtime probe reaches them.

Until this directory existed the gate checked a string prefix and nothing else,
so a vendor could write `provenance="audit:anyone#finding"` and obtain
independent support for a favourable claim at 0.85. The tier was unforgeable in
intention and trivially forgeable in fact.

## How independence is established

Not by a signature. By **who filed**.

A vendor entry does not contain an attestation, it cites one by id. The builder
and the receiving-side validator both resolve that citation against this
directory and refuse it when:

- no such attestation exists;
- it makes no finding on the term being claimed;
- its `auditor_id` equals the citing entry's `vendor_id`;
- the finding it names is `inconclusive`;
- it attests a different deployment.

**What that buys:** a vendor cannot manufacture independent support alone, in
private, at build time. **What it does not:** it does not establish that the
assessor is competent, or that the audit happened. Those are judgements for a
reviewer, which is why the independence block and each finding's `method` are
mandatory and are the first things to read.

We chose this over a signed blob deliberately. Signing needs key distribution
and a crypto dependency inside a FedRAMP boundary, and it puts the artifact in
the hands of the party with a reason to be selective about which attestations
get embedded.

## Filing one

```bash
nsjepa-contrib attest \
  --auditor-id northwind-assurance \
  --auditor-org "Northwind Assurance LLP" \
  --deployment-id cuyahoga-jfs-prod \
  --vendor-id acme-civic \
  --category CAT-02 \
  --engagement-reference "Cuyahoga County PO-2026-4471" \
  --finding "exit_ready_no_lock_in:met:exported the full case store to NDJSON and reimported into a clean instance from a second supplier" \
  --finding "data_residency_no_training:not_met:training manifests show resident free-text in the fine-tuning corpus for two of four model revisions"
```

`nsjepa-contrib audits` lists what is already on file.

## Reviewing one

1. **`independence.engaged_by` must be `issuing_body`.** A vendor-engaged
   assessment can be honest, careful, and correct, and it is not independent of
   the vendor. It belongs at the `vendor:` tier, ceiling 0.60, where it cannot
   carry a positive polarity. The tool refuses to write it at this tier rather
   than quietly downgrading, so an assessor cannot file at the wrong tier and
   never find out.
2. **`engagement_reference`** is the only part of the independence claim
   checkable against something outside the file. A missing one is refused.
3. **`fee_contingent_on_outcome: true`** is disqualifying. An assessor paid more
   for one verdict than another is not independent of the verdict, whoever
   engaged them.
4. **Read every `method`.** A verdict of `met` on
   `data_residency_no_training` means something entirely different depending on
   whether the assessor read a contract clause or inspected a training manifest,
   and nothing downstream can tell them apart afterwards.
5. **`prior_engagements_with_vendor`** is declared, not thresholded. There is no
   correct number and a tool that picked one would be pretending. It is here so
   a reviewer can see it.
6. **`inconclusive` is a real verdict** and should be common. It is the honest
   answer whenever scope or access did not permit a finding, and the SDK refuses
   to let it be cited as support.

## What an attestation is not

It is not a certification, a seal, or a pass. It is one assessor's finding on
named terms over a named period, with the method stated. An entry citing it
inherits exactly that and no more.

It is also not the vendor's to withdraw. Once filed it is in the repository
history, and the corrections protocol in
[`docs/adr/0003-corrections-and-retirement.md`](../../docs/adr/0003-corrections-and-retirement.md)
applies to it as to anything else: supersede it with a later attestation, do not
delete it.
