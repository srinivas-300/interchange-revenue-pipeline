"""Interchange source-data simulator.

Generates a deterministic set of raw source files that stand in for the feeds a
card issuer / spend-management platform would receive: the card event stream,
effective-dated interchange and rewards rate tables, FX rates, and the daily
network settlement file used for reconciliation.
"""

from .run import run

__all__ = ["run"]
