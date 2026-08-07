"""Thin JEPA encoder wrapper. Backbone is swappable (I-JEPA / V-JEPA / LeJEPA).

The encoder is the whole neural footprint of Proposal 2. It outputs a
representation aligned to the domain grounding space; it does NOT predict
future states and does NOT make decisions.
"""
from __future__ import annotations


class JEPAEncoder:
    def __init__(self, backbone: str = "lejepa-vit-b", grounding_dim: int = 256):
        self.backbone = backbone
        self.grounding_dim = grounding_dim

    def encode(self, percept, domain):
        """Return s_x in the domain's grounding space. (impl: load backbone,
        project to grounding_dim, apply SIGReg-trained head.)"""
        raise NotImplementedError
