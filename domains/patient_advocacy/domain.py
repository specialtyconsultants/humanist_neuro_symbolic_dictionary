from core.schemas.domain import Domain, register, Principle, GroundingSpace

@register("patient_advocacy")
class PatientAdvocacy(Domain):
    ontology_path = "domains/patient_advocacy/ontology"
    principles_path = "domains/patient_advocacy/norms/principles.yaml"
    warrant_rules_path = "domains/patient_advocacy/norms/rules.yaml"
    glyph_vocab_path = "domains/patient_advocacy/glyphs/vocab.yaml"

    def principles(self):
        return [
            Principle("autonomy", "Respect for autonomy"),
            Principle("non_maleficence", "Non-maleficence"),
            Principle("beneficence", "Beneficence"),
            Principle("justice", "Justice"),
        ]

    def grounding_space(self):
        return GroundingSpace(
            dimensions=["comprehension", "voluntariness", "disclosure", "risk"],
            embedding_dim=256,
        )
