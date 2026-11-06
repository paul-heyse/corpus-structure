# Current witnessed interpretation native migration

Tested, 2026-11-06: rollback-only native authoring on dedicated corpus_structure_dev accepted 11 native transitions and zero ordinary schema operations, predecessor semantic_wce_roles_20261106. The exact accepted linked candidate is frozen as migration0156. The database transaction rolled back; this authoring result does not establish deployment, independent semantic correctness or positive public admission.

Command: `PYTHONPATH=<worktree>/python/corpus-structure/src <main>/.venv/bin/ci schema native-candidate --out docs/design_review/evidence/2026-11-06_wce-definition-linking/native-candidate-linked` (root-authorized read-only interpreter reuse, separate worktree source).

Earlier candidate directories retain superseded successful authoring states. Initial failed attempts refused a public-to-private model range and an undeclared retired function signature; both were corrected before the accepted linked candidate. No committed database mutation occurred during authoring. The linked candidate adds actual relationship selection references and original occurrence mapping before deployment.

Focused Python frame controls: `PYTHONPATH=<worktree>/python/corpus-structure/src <main>/.venv/bin/python -m pytest -n auto python/corpus-structure/tests/evaluate/test_structural_assessment.py` passed5. An earlier command failed conftest import because an explicit pythonpath override removed scripts; the corrected command retains repository discovery.

Native deployment, positive component/edge publication and combined source/provider journeys remain separate integration obligations.
