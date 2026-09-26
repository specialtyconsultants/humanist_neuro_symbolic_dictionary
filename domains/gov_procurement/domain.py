from core.schemas.domain import Domain, GroundingSpace, Principle, register


@register("gov_procurement")
class GovProcurement(Domain):
    ontology_path = "domains/gov_procurement/ontology"
    principles_path = "domains/gov_procurement/norms/principles.yaml"
    warrant_rules_path = "domains/gov_procurement/norms/rules.yaml"
    glyph_vocab_path = "domains/gov_procurement/glyphs/vocab.yaml"

    def principles(self):
        # Procurement-integrity "world model" (NOT medical ethics).
        #
        # The first five govern the relation between the BODY and its BIDDERS.
        # They are sufficient for entries about the award process, and only
        # gpr:open_scope_solicitation is such an entry.
        #
        # The six marked `proposed=True` govern the relation between the
        # procured SYSTEM and the RESIDENT. They are required because none of
        # the first five is violated when a resident-service assistant issued
        # under the body's own seal tells a landlord they may refuse a housing
        # voucher: competition was open, bidders were treated fairly, criteria
        # were disclosed, no evaluator was conflicted, and the price was good.
        # Asked to score that deployment against the first five, the norms
        # engine returns "permissible" and is not wrong. That silent pass is
        # the failure mode these six exist to prevent.
        return [
            Principle("open_competition", "Open competition"),
            Principle("fair_treatment", "Equal / fair treatment of bidders"),
            Principle("transparency", "Transparency"),
            Principle("coi_avoidance", "Conflict-of-interest avoidance"),
            Principle("best_value_integrity", "Best-value integrity"),

            # --- proposed: resident-facing stratum -------------------------
            Principle("resident_non_maleficence",
                      "The procured system must not injure the resident it serves",
                      proposed=True),
            Principle("due_process",
                      "A person subject to an adverse action can contest it before "
                      "a human who can reverse it, and before the deprivation takes effect",
                      proposed=True),
            Principle("non_discrimination",
                      "No disparate adverse impact across protected or under-served classes",
                      proposed=True),
            Principle("meaningful_access",
                      "Service is usable in the language the resident actually speaks, "
                      "and with disability",
                      proposed=True),
            Principle("data_sovereignty",
                      "Resident data is not appropriated for vendor benefit",
                      proposed=True),
            Principle("continuity_of_public_capacity",
                      "The body retains the ability to perform the function "
                      "without the vendor",
                      proposed=True),
        ]

    def grounding_space(self):
        return GroundingSpace(
            dimensions=[
                "specificity", "competition_openness", "disclosure", "risk",
                # --- proposed, required by the CAT-01..09 seed -------------
                # A solicitation is scored on how open and how specific it is.
                # A DEPLOYED system is scored on how much is at stake for the
                # person it acts on and whether the outcome can be undone —
                # neither of which the original four can express.
                "consequentiality",   # magnitude of what the output does to a person
                "reversibility",      # whether a wrong output can be unwound, and when
                "access",             # whether the person can reach the service at all
            ],
            embedding_dim=256,
        )
