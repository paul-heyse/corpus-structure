"""Comparison instruments for spike S0 (plan: docs/plans/design-spikes-s0-s1/comparison-instruments.md).

Throwaway spike code, not product code. Modules:

- ``batch``: Pydantic models of the model-facing and stored ``ClaimProposalBatch`` (D2 §7.3).
- ``schema_lookup``: per-predicate rules from the LinkML schema v0 through ``SchemaView``.
- ``validate``: batch validation by category (instruments §2.3).
- ``values``: canonical forms (D1 §6.2) and tiered value equivalence (instruments §4).
- ``conditions``: condition-tree canonicalization (D5 §5.2), shared by ``keys`` and ``align``.
- ``align``: entity and claim alignment per unit (D7 §5.2-5.3).
- ``scores``: D7 §5.4 scores with bootstrap intervals over units.
- ``keys``: claim and meaning keys (D1 §10.1, D5 §5.2).

The quote locator and stored-form conversion live in ``code/s0_locate.py``.
"""
