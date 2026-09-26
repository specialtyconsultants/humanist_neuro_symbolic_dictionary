"""Air-gapped submission: a sealed bundle instead of a network call.

Interstate's own instrument offers a "Require Local / On-Premise Hardware CLIN"
for air-gapped or sensitive deployments. A contribution path that assumes
outbound HTTPS excludes exactly those deployments, and they are the ones whose
entries would be hardest to obtain by any other means.

A bundle is a zip: the entry files, a manifest with a SHA-256 per file, and an
optional HMAC over the manifest. It is small enough to leave on removable media
and it verifies on arrival without contacting anything.

The HMAC establishes that the bundle arrived as it left. It does not establish
who wrote it — key distribution is the deployment's problem and this module does
not pretend otherwise. `verify` reports `signed: False` plainly rather than
implying an integrity guarantee it cannot make.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import zipfile
from dataclasses import dataclass

MANIFEST = "manifest.json"
SIGNATURE = "manifest.sig"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class BundleResult:
    path: str
    files: int
    signed: bool


def pack(entry_paths: list[str], out_path: str, *, vendor_id: str,
         deployment_id: str, sdk_version: str, hmac_key: bytes | None = None,
         root: str = ".") -> BundleResult:
    files = []
    payload: dict[str, bytes] = {}
    for p in entry_paths:
        with open(p, "rb") as fh:
            data = fh.read()
        arc = os.path.relpath(p, root).replace(os.sep, "/")
        payload[arc] = data
        files.append({"path": arc, "sha256": _sha256(data), "bytes": len(data)})

    manifest = {
        "schema": "nsjepa-contrib-bundle/1",
        "vendor_id": vendor_id,
        "deployment_id": deployment_id,
        "sdk_version": sdk_version,
        "created_at": int(time.time()),
        "files": files,
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in payload.items():
            z.writestr(arc, data)
        z.writestr(MANIFEST, manifest_bytes)
        if hmac_key:
            z.writestr(SIGNATURE, hmac.new(hmac_key, manifest_bytes, hashlib.sha256).hexdigest())
    return BundleResult(out_path, len(files), bool(hmac_key))


@dataclass
class VerifyResult:
    ok: bool
    signed: bool
    problems: list[str]
    manifest: dict


def verify(bundle_path: str, hmac_key: bytes | None = None) -> VerifyResult:
    problems: list[str] = []
    with zipfile.ZipFile(bundle_path) as z:
        names = set(z.namelist())
        if MANIFEST not in names:
            return VerifyResult(False, False, ["no manifest.json in bundle"], {})
        manifest_bytes = z.read(MANIFEST)
        manifest = json.loads(manifest_bytes)

        signed = SIGNATURE in names
        if hmac_key:
            if not signed:
                problems.append("hmac key supplied but bundle carries no signature")
            else:
                expected = hmac.new(hmac_key, manifest_bytes, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected, z.read(SIGNATURE).decode().strip()):
                    problems.append("manifest signature does not verify")
        elif signed:
            problems.append("bundle is signed and no key was supplied; "
                            "integrity NOT checked")

        listed = {f["path"] for f in manifest["files"]}
        for extra in sorted(names - listed - {MANIFEST, SIGNATURE}):
            problems.append(f"file present but not in manifest: {extra}")
        for f in manifest["files"]:
            if f["path"] not in names:
                problems.append(f"manifest lists a missing file: {f['path']}")
                continue
            if _sha256(z.read(f["path"])) != f["sha256"]:
                problems.append(f"digest mismatch: {f['path']}")

    return VerifyResult(not problems, signed, problems, manifest)


def unpack(bundle_path: str, dest_root: str) -> list[str]:
    """Extract into a dictionary checkout. Refuses paths outside `contrib/`.

    A bundle arrives from outside the trust boundary, so the path check is not
    theoretical: without it, a crafted archive writes over `core/` or
    `domains/<d>/norms/rules.yaml`, and rewriting the norm set is precisely how
    you would make a dishonest entry validate.
    """
    written = []
    with zipfile.ZipFile(bundle_path) as z:
        for name in z.namelist():
            if name in (MANIFEST, SIGNATURE):
                continue
            target = os.path.normpath(os.path.join(dest_root, name))
            allowed = os.path.normpath(os.path.join(dest_root, "contrib"))
            if not target.startswith(allowed + os.sep):
                raise ValueError(
                    f"bundle entry {name!r} would write outside contrib/ — refusing")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as fh:
                fh.write(z.read(name))
            written.append(target)
    return written
