"""Deployment gate: no recommendation may be emitted without a complete
warrant chain + provenance. Enforced in CI (see .github/workflows/ci.yml).
This is a placeholder that the scaffold marks xfail until the engine lands.
"""
import pytest

@pytest.mark.xfail(reason="engine not implemented in scaffold", strict=False)
def test_recommendation_requires_warrant_and_provenance():
    raise AssertionError("wire to core.norms + services.audit once implemented")
