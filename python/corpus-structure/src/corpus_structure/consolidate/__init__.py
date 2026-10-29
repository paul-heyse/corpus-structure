"""Shared consolidation algorithms/configuration; publication uses semantic domain operations."""

from corpus_structure.consolidate.pass_ import ConsolidateMethod
from corpus_structure.consolidate.report import PassOutcome, PassReport

__all__ = ["ConsolidateMethod", "PassOutcome", "PassReport"]
