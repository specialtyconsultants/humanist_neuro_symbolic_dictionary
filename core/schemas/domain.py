"""Domain protocol and registry.

This is the single extension point that lets `core/` stay ignorant of any
specific use case. A domain pack subclasses `Domain`, decorates it with
`@register("<name>")`, and supplies paths to its ontology, norms, and glyph
vocabulary. `core/` drives every domain uniformly through this interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Callable

_REGISTRY: dict[str, type["Domain"]] = {}


def register(name: str) -> Callable[[type["Domain"]], type["Domain"]]:
    """Class decorator that registers a domain pack under `name`."""
    def _wrap(cls: type["Domain"]) -> type["Domain"]:
        if name in _REGISTRY:
            raise ValueError(f"domain '{name}' already registered")
        cls.name = name
        _REGISTRY[name] = cls
        return cls
    return _wrap


def get_domain(name: str) -> "Domain":
    if name not in _REGISTRY:
        raise KeyError(f"unknown domain '{name}'; registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)


@runtime_checkable
class Domain(Protocol):
    """Everything the engine needs to serve one use case.

    Only *content* differs per domain (ontology, norms, glyphs). The
    reasoning machinery (SCM, norms engine, KG, interpretive readings) is
    shared and lives in `core/`.
    """

    name: str
    ontology_path: str
    principles_path: str        # finite principle set + polarities
    warrant_rules_path: str     # claim |- principle warrant templates
    glyph_vocab_path: str

    def grounding_space(self) -> "GroundingSpace":
        """Return the conceptual-space / embedding target the JEPA encoder
        aligns to (the Type-G footnote target). Default impl loads from
        the ontology's quality dimensions."""
        ...

    def principles(self) -> list["Principle"]:
        """The domain's finite normative principles (the 'world model')."""
        ...


@dataclass
class Principle:
    """One normative principle in a domain's grounding world model."""
    id: str
    label: str
    # polarity is assigned per-entry by the norms engine, not here
    description: str = ""
    # A principle a domain pack asserts is REQUIRED but that the domain's
    # owners have not adopted. Declaring it lets an entry record a harm the
    # ratified set cannot receive, without the engine treating that harm as
    # settled. Any entry whose principle_polarity touches a proposed principle
    # must escalate rather than resolve — the same posture as an empty
    # `warrants` list. See domains/gov_procurement/domain.py for the case that
    # forced it: nine deployed-system entries whose harms land on nobody in the
    # five-principle procurement-integrity set.
    proposed: bool = False


@dataclass
class GroundingSpace:
    """Quality dimensions the encoder maps percepts into (Gardenfors-style)."""
    dimensions: list[str] = field(default_factory=list)
    embedding_dim: int = 256
