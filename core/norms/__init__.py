"""Norms engine (Type-E). Domain-independent MECHANISM; domain-specific CONTENT.

Given an entry + a proposed recommendation, assigns each domain principle a
polarity and builds the warrant chain (claim |- principle). Encodes the
principle set as a HARD FLOOR (cf. LeCun's immutable Intrinsic Cost) and keeps
balancing/specification inspectable rather than folding it into a scalar.
"""
