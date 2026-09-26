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


class Status(str, Enum):
    """Epistemic standing of an entry.

    Only RATIFIED entries may contribute to institution-level aggregation.
    PROVISIONAL marks an entry whose evidence is live (open investigation) or
    whose ethics footnote has no matching warrant yet; it must be re-checked.
    """
    PROVISIONAL = "provisional"
    RATIFIED = "ratified"
    RETIRED = "retired"


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
    # Stable within the entry ("e1", "e2", ...). Exists so the ethics footnote
    # can name the edges supporting each polarity. Before this field, Type G was
    # checkable against the glyph vocabulary and Type C against its provenance
    # tiers, while Type E was an assertion sitting beside the graph with no link
    # to it — the only footnote a reader had to take on faith.
    id: str = ""


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
class PolarityClaim:
    """One principle's polarity, and the edges that earn it.

    `supported_by` holds CausalEdge ids from THIS entry. It is what makes the
    ethics footnote auditable: "every polarity has support" and "a positive
    polarity has INDEPENDENT support" both become mechanical checks instead of
    editorial judgement.

    The second is the conflict-of-interest control, and it is stated in terms of
    who a claim cuts against rather than of its sign. A claim requires
    independent support unless it is adverse to the party submitting it —
    testimony against interest is credible on its own, and a submitter's
    finding that is adverse only to somebody else is not testimony against
    interest merely because it is negative.
    """
    polarity: Polarity
    supported_by: list[str] = field(default_factory=list)

    @classmethod
    def coerce(cls, value) -> PolarityClaim:
        """Accept a bare "+"/"-"/"+/-" for the pre-`supported_by` form.

        Tolerated on read so old files load; reported by the validator as an
        unsupported normative claim, because that is what it is.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(polarity=Polarity(value))
        return cls(polarity=Polarity(value["polarity"]),
                   supported_by=list(value.get("supported_by", [])))


@dataclass
class EthicsFootnote:
    """Why acting on the term is PERMISSIBLE. Domain-agnostic container;
    the principle ids resolve against the active domain's principle set."""
    principle_polarity: dict[str, PolarityClaim] = field(default_factory=dict)
    warrants: list[Warrant] = field(default_factory=list)
    balancing_note: str = ""

    #: Who the entry's findings cut against: any of "vendor", "operator",
    #: "resident". Drives the independence requirement above. An entry with no
    #: contributor is authored by the domain itself and is adverse to nobody in
    #: particular, so the field is empty and the requirement falls back to sign.
    adverse_to: list[str] = field(default_factory=list)


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
    status: Status = Status.PROVISIONAL
    conceptual_space_vector: dict[str, float] = field(default_factory=dict)
    neural_embedding: list[float] = field(default_factory=list)
    grounding: GroundingFootnote | None = None
    causal: CausalFootnote | None = None
    ethics: EthicsFootnote | None = None
    svo: SVOTriplet | None = None
    glyph_block: GlyphBlock | None = None
    metaphor_type: str = ""
    provenance: str = ""

    # ---- correction and retirement ------------------------------------------
    # `Status.RETIRED` existed from the start with no protocol behind it, which
    # is worse than not having it: a corpus that can name a live agency needs a
    # way to be wrong on a clock rather than by argument. See
    # docs/adr/0003-corrections-and-retirement.md.
    supersedes: list[str] = field(default_factory=list)   # entry ids this replaces
    superseded_by: str = ""                               # set on the retired entry
    retired_reason: str = ""                              # required when RETIRED
    #: ISO date. Required on any PROVISIONAL entry that names a living person or
    #: an identifiable institution. A provisional finding about a real party is
    #: a claim with no expiry unless someone writes one down.
    review_by: str = ""
