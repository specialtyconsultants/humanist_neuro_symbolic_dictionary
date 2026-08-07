from core.schemas.domain import Domain, register, Principle, GroundingSpace

@register("gov_procurement")
class GovProcurement(Domain):
    ontology_path = "domains/gov_procurement/ontology"
    principles_path = "domains/gov_procurement/norms/principles.yaml"
    warrant_rules_path = "domains/gov_procurement/norms/rules.yaml"
    glyph_vocab_path = "domains/gov_procurement/glyphs/vocab.yaml"

    def principles(self):
        # Procurement-integrity "world model" (NOT medical ethics).
        return [
            Principle("open_competition", "Open competition"),
            Principle("fair_treatment", "Equal / fair treatment of bidders"),
            Principle("transparency", "Transparency"),
            Principle("coi_avoidance", "Conflict-of-interest avoidance"),
            Principle("best_value_integrity", "Best-value integrity"),
        ]

    def grounding_space(self):
        return GroundingSpace(
            dimensions=["specificity", "competition_openness", "disclosure", "risk"],
            embedding_dim=256,
        )
