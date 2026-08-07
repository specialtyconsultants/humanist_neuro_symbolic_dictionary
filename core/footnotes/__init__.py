"""Generators for the three footnotes and the supplemental artifacts.

- grounding.py : builds Type-G from encoder output + glyph vocab
- causal.py    : builds Type-C by querying the domain SCM
- ethics.py    : builds Type-E via the norms engine
- artifacts.py : reads the highest-confidence causal edge into an SVO triplet
                 and assembles the Maya-style glyph block
"""
