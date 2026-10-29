"""Consolidation (consolidation §3; D5; ADR-0014, ADR-0021): the only writer of the run's
knowledge rows. `run_pass` is the stage runner's entry; `assemble` is the pure core over the pool.
"""

from corpus_structure.consolidate.pass_ import ConsolidateMethod, consolidate, run_pass
from corpus_structure.consolidate.report import PassOutcome, PassReport

__all__ = ["ConsolidateMethod", "PassOutcome", "PassReport", "consolidate", "run_pass"]
