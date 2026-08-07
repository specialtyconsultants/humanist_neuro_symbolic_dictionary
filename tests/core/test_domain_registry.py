def test_all_domains_register():
    import domains  # triggers registration
    from core.schemas.domain import available
    for name in ("patient_advocacy", "gov_procurement", "agri_microfinance"):
        assert name in available()


def test_principle_sets_differ_per_domain():
    import domains  # noqa
    from core.schemas.domain import get_domain
    pa = {p.id for p in get_domain("patient_advocacy").principles()}
    gp = {p.id for p in get_domain("gov_procurement").principles()}
    assert "autonomy" in pa and "autonomy" not in gp
    assert "open_competition" in gp
