# Pending SP-0031 handoff

No SP-0031 migration or fingerprint change was published to the repository. No native checks
were started for this increment. All preparatory commands have exited; this worker owns no
running process. Operational databases and sealed run 3 were not changed.

The initial reviewable draft is in this directory:

- `0031_statement_inheritance.py`: draft forward revision from semantic_0030.
- `semantic_0031_statement_inheritance.sql`: initial base-SourceStatement-or-descendant guard,
  copied unchanged custody checks, and refreshed descriptor/require.
- `execution_admission.py`: corresponding initial draft fingerprint file.
- `test_statement_inheritance.py`: initial actual-toy schema publication test for descendant
  membership and unrelated-class refusal.
- `generate.py`: generator for that initial draft.

DO NOT APPLY THESE DRAFTS AS THE ACCEPTED FIX. The later instruction superseded the initial
base-class widening: the allowed class must come from the admitted release's
`AgentStatementBinding.statement` range using `sem.property_applicability` and
`sem.class_definition`. Membership must match that exact class or its same-release descendants
through `sem.class_hierarchy`. An explicit ToySourceStatement binding must refuse the base
SourceStatement and unrelated classes. Archives without AgentStatementBinding may use the
existing declared SourceStatement protocol. Malformed or ambiguous bindings must refuse.
This updated binding-based implementation and its expanded tests have NOT been written.

Relevant current sources examined:

- `semantic_0030_source_frames.sql`: direct `c.name='SourceStatement'` occurrence-context guard.
- `semantic/statement_types.py`: Python materialization already derives the explicit binding.
- `model/semantic/agent.yaml`: AgentStatementBinding.statement declaration.
- `semantic_0027_transport.sql`: existing same-release hierarchy pattern for Qualification.

The initial draft preserves execution model
`execution:6e6f27d22ad3d4ce187c22d52fefaebca5c58850011ec84886b11fada576d9b5`
and physical model
`physical:a1d1377c7f65ba528b52f096ec737094228f2075802db0a70af9afec78bf1f2e`.
The final correction should not require either model ID to change.

Preparatory checks:

- SQL parsing of the initial draft: passed.
- Pending migration/test plus the current in-package execution_admission module:
  Pyrefly with deprecated/conversion warnings passed, log `/tmp/sp31-pending-context-types.log`.
- Checking the copied standalone fingerprint file under /tmp failed on its package-relative
  imports; this was not a product source error. Log `/tmp/sp31-pending-types.log`.
- All native / functional checks for SP-0031: not_run.
