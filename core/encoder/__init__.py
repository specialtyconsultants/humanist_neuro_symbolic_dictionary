"""JEPA grounding encoder (the ONLY neural component).

Maps multimodal percepts (text, glyph image, structured record) into the
active domain's grounding space s_x. Trained non-contrastively; collapse is
prevented by SIGReg (LeJEPA) or VICReg — see `training/configs`.

Public surface:
    encode(percept, domain) -> s_x            # Type-G grounding
    nearest_entry(s_x, kg)  -> (Entry, sim)   # embedding-similarity reading
"""
