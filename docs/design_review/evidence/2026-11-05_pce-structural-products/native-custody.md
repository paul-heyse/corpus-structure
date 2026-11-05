# Native assessment foundation controls

**Tested, 2026-11-05; bounded controls, overall failed.** These receipts establish native
custody/authorization behavior only. Fixture A/B/C actor labels are test identities, not
independent semantic judgments. No whole-PCE qualification or default adoption is claimed.

- `uv run pytest python/corpus-structure/tests/evaluate/test_review_assessments.py python/corpus-structure/tests/evaluate/test_structural_assessment.py -q`: **passed**,10 controls.
- `uv run ci schema native-candidate --out <candidate directory> --json`: candidate003
  produced145 (15 native/15 ordinary operations); candidate004 produced146 (7 native/15 ordinary).
  Both rollback-only authorings used persistent `corpus_structure_dev` on18/corpus5434.
- `uv run ci db migrate --json`: **passed**,145 and146 deployed additively. Frozen source,
  state and admission artifacts remain hash-bound in the migration owner. New assessment
  physical fields change the existing physical-model-bound companion projection identity;
  the four changed companion functions otherwise retain the same query semantics.
- `uv run python docs/design_review/evidence/2026-11-05_pce-structural-products/native_assessment_journey.py native-assessment-controls-007.json`:
  **failed overall**, with bounded positives recorded in [raw receipt](raw/native-assessment-controls-007.json).
  Original run45/view46, run15/view25 and run13/view32 authenticated successfully after146.
  Group frame2, passes4/5/6, committed receipt3 yielded full A/B/C history. Already-exposed
  feature-fit operation set18, receipt4 yielded17 history rows without relabeling its partition.
  Same-actor B and reversed adjudication parents refused (23514); actual producer history
  access refused (42501). Full protected provider execution and offline bundle acceptance are
  separate obligations. No real sealed operation reference set was selected: that control is
  **not_run**, not passed.
- The precommit-exposure guard **failed**: a receipt's row xmin can differ from the current
  top-level xid before commit. The independent
  `uv run python docs/design_review/evidence/2026-11-05_pce-structural-products/receipt_subtransaction_control.py`
  also reproduced delivery of17 rows before the top-level transaction committed.
  [Failure receipt](raw/receipt-savepoint-146.json) is retained.147 must store explicit creating
  top-level transaction identity and refuse fresh delivery from an uncommitted receipt.

Semantic release `release:58fbd6fc5ee29f3b29d9cf292bc8903b7116e3aa3ce5798d9856de1cd5916e71`
was installed nondefault for these controls. Original source releases remain distinct. The
Python deployment verifier's exact descriptor hash now matches the reviewed frozen146 body;
its enforcement was not weakened. Original archive and result defaults remain unselected.

Candidate001 is superseded because source coordinate version needed the product-kind binding;
002 is superseded by the released-input-schema guard.003/004 are preserved exact compiler
outputs. Failed native journey attempts remain in `raw/`: initial composition-name collision,
old descriptor verifier hash, incorrect setup purposes, omitted-versus-null frame serialization,
and the discovered precommit guard failure were not erased. Their successful replacements do
not establish broader semantic quality. Root owns final integration,147 repair/retesting,
independent source-only authors, qualification and plan/status handoff.
