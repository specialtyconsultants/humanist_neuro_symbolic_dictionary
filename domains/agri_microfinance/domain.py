from core.schemas.domain import Domain, GroundingSpace, Principle, register


@register("agri_microfinance")
class AgriMicrofinance(Domain):
    ontology_path = "domains/agri_microfinance/ontology"
    principles_path = "domains/agri_microfinance/norms/principles.yaml"
    warrant_rules_path = "domains/agri_microfinance/norms/rules.yaml"
    glyph_vocab_path = "domains/agri_microfinance/glyphs/vocab.yaml"

    def principles(self):
        # Contract-fairness + borrower/creditor-protection "world model".
        return [
            Principle("contract_fairness", "Contract fairness"),
            Principle("non_predatory", "Non-predatory terms"),
            Principle("solvency_protection", "Borrower solvency protection"),
            Principle("disclosure", "Full disclosure"),
            Principle("proportionate_recourse", "Proportionate recourse on default"),
        ]

    def grounding_space(self):
        return GroundingSpace(
            dimensions=["affordability", "disclosure", "collateral_burden", "risk"],
            embedding_dim=256,
        )
