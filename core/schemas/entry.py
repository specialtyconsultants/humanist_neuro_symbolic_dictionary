"""Dictionary entry + the three neuro-symbolic footnotes (G / C / E).

These schemas are domain-independent. A patient-advocacy entry, a procurement
entry, and a microfinance entry are the *same* dataclass; only the values and
the norm/glyph vocabularies differ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Peirce(str, Enum):
    ICON = "icon"       # resemblance
    INDEX = "index"     # causal / physical connection
    SYMBOL = "symbol"   # convention


class Polarity(str, Enum):
    POS = "+"
    NEG = "-"
    MIXED = "+/-"


# ---- Type G: Grounding footnote --------------------------------------------
@dataclass
class Glyph:
    form: str
    peirce: Peirce
    role: str = "logogram"   # logogram | superfix | subfix


@dataclass
class GroundingFootnote:
    """What the term MEANS. Anchors the symbol to non-symbolic meaning."""
    conceptual_region: list[str]          # quality dimensions occupied
    embedding_centroid: list[float] = field(default_factory=list)
    glyphs: list[Glyph] = field(default_factory=list)


# ---- Type C: Causal-Provenance footnote ------------------------------------
@dataclass
class CausalEdge:
    cause: str
    relation: str            # e.g. "enables", "increases", "causes"
    effect: str
    confidence: float
    provenance: str          # PROV-O record id / citation


@dataclass
class CausalFootnote:
    """What the term IMPLIES. An SCM fragment supporting do-calculus."""
    edges: list[CausalEdge] = field(default_factory=list)
    interventions: list[str] = field(default_factory=list)  # do(...) notes


# ---- Type E: Ethics / Norms-Warrant footnote -------------------------------
@dataclass
class Warrant:
    claim: str               # e.g. "valid_consent"
    principle_id: str        # e.g. "autonomy"


@dataclass
class EthicsFootnote:
    """Why acting on the term is PERMISSIBLE. Domain-agnostic container;
    the principle ids resolve against the active domain's principle set."""
    principle_polarity: dict[str, Polarity] = field(default_factory=dict)
    warrants: list[Warrant] = field(default_factory=list)
    balancing_note: str = ""


# ---- Supplemental artifacts -------------------------------------------------
@dataclass
class SVOTriplet:
    subject: str
    verb: str
    obj: str
    derived_from: str = ""   # id of the causal edge it was read off


@dataclass
class GlyphBlock:
    logogram: str
    superfix: str = ""       # metaphor-type marker
    subfix: str = ""         # norm-polarity "phonetic complement"
    reading_order: str = "left-to-right, top-to-bottom"


# ---- The entry itself -------------------------------------------------------
@dataclass
class Entry:
    id: str                  # stable URI
    lemma: str
    domain: str
    domain_sense: str
    conceptual_space_vector: dict[str, float] = field(default_factory=dict)
    neural_embedding: list[float] = field(default_factory=list)
    grounding: GroundingFootnote | None = None
    causal: CausalFootnote | None = None
    ethics: EthicsFootnote | None = None
    svo: SVOTriplet | None = None
    glyph_block: GlyphBlock | None = None
    metaphor_type: str = ""
    provenance: str = ""
