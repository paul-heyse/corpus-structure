"""The model's loader, declaration check, revision and compilers (ADR-0020; model and projections).

`schema` is the only package that imports LinkML. `model` loads the model's `core` and `system`
modules, checks their declarations and computes the model revision; `generate` is Stage A, which
writes the checked-in `core/vocab.py` and `core/_model/` that `core` imports without LinkML.
`python -m corpus_structure.schema generate|check` (`just model generate|check`) runs them.
"""
