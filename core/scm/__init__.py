"""Structural causal model reasoner (Type-C). Domain-independent engine.

Loads a domain's causal edges (with confidence + provenance) into a DAG and
answers do-calculus queries. Never learns edges from correlation — edges are
curated and provenance-tagged, because active-agency data is impermissible.
"""
