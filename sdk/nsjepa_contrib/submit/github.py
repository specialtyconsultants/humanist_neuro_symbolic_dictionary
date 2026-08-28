"""Online submission: a pull request against the common repo.

Deliberately a PR and never a push. A contribution is a claim about a
government system's effect on people, and no vendor writes that into the shared
record unreviewed — including a vendor writing about itself favourably, and
including this SDK's own author.

Standard library only. A governance SDK that drags a dependency tree into a
FedRAMP-boundary product will not be installed, and then nothing is contributed.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com"
UPSTREAM = "specialtyconsultants/humanist_neuro_symbolic_dictionary"


class SubmitError(RuntimeError):
    pass


@dataclass
class Submission:
    url: str
    branch: str
    files: list[str]


def _req(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "nsjepa-contrib")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SubmitError(f"{method} {url} -> {e.code}: {detail}") from e


def token_from_env(env: str = "NSJEPA_CONTRIB_TOKEN") -> str:
    tok = os.environ.get(env) or os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise SubmitError(
            f"no token in ${env} or $GITHUB_TOKEN. The token needs `contents:write` "
            f"and `pull_requests:write` on your fork only — it must NOT have write "
            f"access to {UPSTREAM}, and a token that does is a finding in its own right."
        )
    return tok


def submit(entry_paths: list[str], *, vendor_id: str, deployment_id: str,
           token: str, upstream: str = UPSTREAM, fork: str | None = None,
           root: str = ".", title: str | None = None,
           body: str = "") -> Submission:
    """Commit `entry_paths` to a branch on `fork` and open a PR against `upstream`.

    `fork` defaults to the authenticated user's fork of `upstream`, which must
    already exist — creating one silently on a user's account is not this
    library's call to make.
    """
    me = _req("GET", "/user", token)["login"]
    fork = fork or f"{me}/{upstream.split('/')[1]}"

    upstream_default = _req("GET", f"/repos/{upstream}", token)["default_branch"]
    base_sha = _req("GET", f"/repos/{fork}/git/ref/heads/{upstream_default}",
                    token)["object"]["sha"]

    branch = f"contrib/{vendor_id}/{deployment_id}"
    try:
        _req("POST", f"/repos/{fork}/git/refs", token,
             {"ref": f"refs/heads/{branch}", "sha": base_sha})
    except SubmitError as e:
        if "Reference already exists" not in str(e):
            raise

    committed = []
    for path in entry_paths:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        content = base64.b64encode(open(path, "rb").read()).decode()
        payload = {"message": f"contrib({vendor_id}): {os.path.basename(rel)}",
                   "content": content, "branch": branch}
        try:
            existing = _req("GET", f"/repos/{fork}/contents/{rel}?ref={branch}", token)
            payload["sha"] = existing["sha"]
        except SubmitError:
            pass
        _req("PUT", f"/repos/{fork}/contents/{rel}", token, payload)
        committed.append(rel)

    pr = _req("POST", f"/repos/{upstream}/pulls", token, {
        "title": title or f"contrib({vendor_id}): {len(committed)} entr"
                          f"{'y' if len(committed) == 1 else 'ies'} from {deployment_id}",
        "head": f"{fork.split('/')[0]}:{branch}",
        "base": upstream_default,
        "body": body or _default_body(vendor_id, deployment_id, committed),
        "maintainer_can_modify": True,
    })
    return Submission(pr["html_url"], branch, committed)


def _default_body(vendor_id: str, deployment_id: str, files: list[str]) -> str:
    listing = "\n".join(f"- `{f}`" for f in files)
    return f"""\
Automated contribution from `nsjepa_contrib`.

- **Vendor:** `{vendor_id}`
- **Deployment:** `{deployment_id}`
- **Entries:** {len(files)}

{listing}

All entries are `status: provisional` and land under `contrib/`, outside the
canonical `domains/<domain>/entries/` namespace. Promoting one is a maintainer
action and requires a ratification decision — a contributor cannot ratify its
own entry.

Please read the `term_findings` block before the causal edges. Where a
governance term the solicitation required was found NOT met in production, the
corresponding warrant has been **withdrawn by the SDK**, not asserted, and the
entry may therefore contradict the contract it was produced under. That is
working as intended.
"""
