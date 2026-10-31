# PDF application serialization and native retention

**Outcome: partial, 2026-10-31.** The application boundary and PostgreSQL retention were exercised; this is not whole-book or source-fidelity qualification.

The first full-book attempt finished native inference but application preparation rejected explicit `font: null` in vector candidate records. The producer now omits absent optional fields in its own candidate/projection wire DTOs. Native Docling serialization remains owned by Docling. A minimal schema-valid raw native capture is prepared before optional discovery/runtime products, and every successfully prepared product is retained when later view preparation fails. Terminal diagnostics retain the validation count and first three locations, bounded to 1,800 characters; they do not multiply original input values into PostgreSQL errors and logs. The original full-book refusal log remains in the adoption evidence folder.

The one fresh physical page 85 conversion used the retained complete original, exact cached model assets, StandardPdfPipeline, CUDA layout/table/formula engines, and observed CPU OCR providers. It returned success and both minimal raw and full application envelopes passed `prepare_pdf_product`, including 24 candidates with absent fonts, the runtime report and native confidence. It took 22.29 seconds in this bounded run. The page-lifetime owner had released its retained pages after conversion. These are capability/preparation observations, not correctness grades or a full-book runtime estimate.

`test_native_documents.py` exercised two PostgreSQL cases: an independently constructed native document and this retained actual page 85 capture. Both raw and full application products published through the real restricted publisher. An explicit candidate `font: null` remained invalid. Completing a failed task retained both valid products, and item/region readback matched the retained native artifacts. The two cases passed in 34.14 seconds. The earlier control failure compared PostgreSQL NUMERIC/Decimal directly with a binary float; the independent expectation now uses the exact serialized decimal representation.

Commands used the main application interpreter with `PYTHONPATH` explicitly naming this producer worktree. To satisfy the existing corpus prerequisite in the worktree, its corpus path temporarily linked the actual main-checkout corpus; no original was copied or modified. The actual source digest is `e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9`.

```sh
python qualify.py preflight --source /home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf
python qualify.py convert --source /home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf
python -m pytest python/corpus-structure/tests/semantic/test_native_documents.py -q --override-ini addopts=''
```

The receipts retain the absent-worktree-corpus skip, Decimal assertion failure and passing rerun separately. An earlier run against the old0049 admission failed before entering the control and supplies no retention acceptance credit. No additional GPU work follows the page 85 case here. The coordinator owns the subsequent full-book retry and assembled acceptance. Finite process ownership and backend-only recovery were subsequently implemented. Normal strict/config/importlib pytest controls passed 23 cases in 8.89 seconds, including an actual blocked CPU child that ignores termination and is killed/joined on KeyboardInterrupt, serial same-child reuse, native non-success disposal, claim-loss interruption, failed-teardown handle custody, fresh registry ownership and all-owner cleanup. These lifecycle controls do not count as model/provider inference. The real native publication/fence control also refused a late native product after authoritative run cancellation.

CPU-only rediscovery of the retained physical page 85 returned 24 native word/vector candidates in 2.51 seconds. The initial non-rendered native backend attempt was refused because vector shapes were skipped at decode time; the selected native backend enables its CPU rendering/shape computation. No layout, OCR or formula model ran in this recovery. The discovery result is retained in `raw/backend-rediscovery.json`.

The final spawned-child adapter still requires its actual model/provider OCR qualification after the coordinator's book releases GPU ownership. Existing page 85 provider evidence exercised the in-process adapter, while these later process controls establish ownership and IPC only.
