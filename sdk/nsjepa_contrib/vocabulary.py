"""Canonical node-name resolution — the anti-drift gate.

Convergence on shared causal nodes is the dictionary's central claim to say
anything structural. It is also the first property lost when contributions
arrive from many parties, because there is nothing wrong with any of the names
people independently choose and no way for the graph to know they meant the
same thing.

`Vocabulary.resolve` maps a submitted name onto its canonical form, strips the
`@t` time index before lookup, and reports anything unregistered so it can be
reviewed rather than silently forked.
"""
from __future__ import annotations

import difflib
import os
from dataclasses import dataclass, field

from ._io import read_yaml


@dataclass
class Resolution:
    submitted: str
    canonical: str
    registered: bool
    time_index: str = ""          # "t", "t1", ... ; "" when not time-indexed
    suggestion: str = ""          # nearest registered name, when unregistered

    @property
    def renamed(self) -> bool:
        return self.canonical != self.submitted


@dataclass
class Vocabulary:
    domain: str
    separator: str = "@"
    _canonical: dict[str, str] = field(default_factory=dict)   # alias/name -> canonical
    _gloss: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, domain: str, root: str = ".") -> Vocabulary:
        path = os.path.join(root, "domains", domain, "vocab", "nodes.yaml")
        if not os.path.exists(path):
            # A domain with no registry yet: everything is unregistered, which
            # `validate` reports rather than rejects. A new domain should not be
            # blocked from its first contribution by a file it has not written.
            return cls(domain=domain)
        data = read_yaml(path) or {}
        v = cls(domain=domain, separator=data.get("time_index_separator", "@"))
        for name, spec in (data.get("nodes") or {}).items():
            v._canonical[name] = name
            v._gloss[name] = (spec or {}).get("gloss", "")
            for alias in (spec or {}).get("aliases", []) or []:
                v._canonical[alias] = name
        return v

    def split_index(self, node: str) -> tuple[str, str]:
        base, sep, idx = node.partition(self.separator)
        return (base, idx) if sep else (node, "")

    def resolve(self, node: str) -> Resolution:
        base, idx = self.split_index(node)
        canonical_base = self._canonical.get(base)
        if canonical_base is None:
            close = difflib.get_close_matches(base, list(self._canonical), n=1, cutoff=0.75)
            return Resolution(
                submitted=node, canonical=node, registered=False,
                time_index=idx, suggestion=close[0] if close else "",
            )
        canonical = canonical_base + (self.separator + idx if idx else "")
        return Resolution(submitted=node, canonical=canonical, registered=True, time_index=idx)

    def gloss(self, node: str) -> str:
        base, _ = self.split_index(node)
        return self._gloss.get(self._canonical.get(base, base), "")

    @property
    def size(self) -> int:
        return len(set(self._canonical.values()))

    @property
    def registered(self) -> set[str]:
        return set(self._canonical.values())
