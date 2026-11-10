# DMC contract inspection acceptance · 2026-11-10

DMC-00–02 acceptance uses the dedicated development database. The existing native archive
reader explicitly enumerates supported compiler versions; compiler20 requires a forward
`sem.require_archive_bytes(text)` compatibility update. `change.yaml` requests the
native compiler compatibility update through the ordinary frozen candidate route. Archive3 and boundary ABI12
remain unchanged. Current package disposition and managed result identities belong to the
[coordinator](../../../plans/domain-data-model_2026-11-10.md#dmc-0002-execution-receipt--2026-11-10).

## Live reader acceptance

**Scoped Tested, 2026-11-10.** Deployment result `8791940484e64d9ab4162e94d7f17a19`
passed migration/archive/admission/reader verification at `semantic_dmc_compiler20`.
The first migration remains deployed; the second advances the producing-compiler guard.
No ordinary relational operation, activation or run selection occurred.

- Release: `release:4b5fd49b3879d7628e80a5feb78607b3cdc327ce223e37a5827f517f44d822f3`.
- Execution: `execution:7bf8d8d78f16df38f1454ed81b5ce64e9ad4d3ab72de2f3226a36266b996754c`.
- Artifact-set digest: `226906703a28a535f8304ea70a62802aabb74dcbedffb9a8b933d3b622c18ec2`.
- Physical: `physical:89a7c561254db10003b43437832e1188e02ccfebe68e00913b1f40e6fbce7e52`.

`uv run ci db check --release RELEASE --json`, `uv run ci release check --release RELEASE --json`
and `uv run ci db status --maintenance --json` passed on the dedicated development target.

`uv run python docs/design_review/evidence/2026-11-10_dmc-contract-inspection/journey.py RELEASE CANDIDATE`
passed with candidate `53d8c6b524a2466a877282680549185d`. The journey verifies inherited source
attribution, CLI/MCP equality, frozen managed candidate equality, valid/invalid structural input,
finite scaffolding and the existing archive-operation explanation. It also checks that Docling's
converter and GLiNER are not imported. It acquires real development reader connections.

The compiler19 PTD archive remains readable with its required `Formula.language` fact and
explicit unavailable authoring detail. No current source is used to fill that historical gap.

The coordinator owns affected-test accounting and remaining series qualification. These checks
establish the selected authoring/read workflow, not whole-series or provider qualification.
