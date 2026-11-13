# DDO preservation roots and declared external custody

**Observed / Tested2026-11-12 local (2026-11-13UTC); metadata-only; partial closure.**
This inventory supplies actual instance identities for DDO-00/DDO-11. It preserves original source,
protected reference and retained evidence custody by default. It does not authorize migration,
reset, disposal, result settlement, provider execution or protected-reference rewriting.

[Summary](raw/summary.json) contains selected IDs, classifications, concrete manifest consumers,
pending workspaces and link-check exceptions. [Raw inventory](raw/inventory.json) contains all58
explicit relation projections, complete357FK definitions in the selected schemas, and the declared
local metadata universe. [Source](census.py) is reusable for a later authorized fresh census.
No source bytes/text, artifact payload, task-result body, protected question/answer, credentials,
provider output or private model configuration was selected. Completion source/proof receipts are
identity-only native metadata, produced as task/derivation IDs by the completion SQL owner.

## Acquired target and bounds

The first command, `uv run ci db status --maintenance --json`, passed and acquired
`corpus_structure_dev`, principal `paul`, `/var/run/postgresql:5434`, databaseOID25921445,
system identifier7701811359771751232, revision/head `semantic_bep_located_v2`.
[Preflight](raw/preflight.json) reported PostgreSQL18.6. The detailed read reported18.7 under
the identical system/database identity and migration revision; no cause for this version change
is inferred. Reacquire the actual target before any later effect.

The detailed snapshot was taken at2026-11-12 22:24:37-05:00, snapshot1451578:1451578:,
through `open_runtime_engine(Settings(), purpose='maintenance')`, with
`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`, a15-second statement timeout,
at most100000rows per explicit metadata projection and a2000FK bound. The transaction was
rolled back. The357FKs comprise all329prior census relationships plus28`sem` relationships;
none of the prior relationships is absent. This is broader schema selection, not evidence that
28constraints were added during this task.

## Actual selected roots and consumers

| Roots (exact identities in raw inventory) | Preservation action and actual consumer |
|---|---|
|29documents,7480artifact digests,316source-build bindings,784source views | Preserve original files and original source/native/recipe/schema identities. `semantic.source_views.load_source_view`, retained source/proof readers and protected unit/frame bindings consume them. All29declared original paths exist by metadata; their bytes were not rehashed. The artifact pool includes both original and derived custody, so none is labelled disposable merely by table membership. |
| Full-book documents45and50, original digest `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e` | Preserve both document bindings and original/native source custody. Document45has580retained source-view identities across historical interpretations; this is not a claim that the plan's one frozen316-view/518-page demand has been selected or qualified. |
|42reference sets,107units,318passes/frames,3390item identities;8structural sets/24passes;43evaluations | Preserve protected sealed interpretation, original source-run/release/unit/frame/projection/digest links and immutable evaluation identity. Evaluator and independent source-only/protected assessment readers remain their consumers. Original questions/answers stay untouched. |
|256completed results,663input cuts,2662cut-task memberships;565runs/2409tasks | Preserve every completion and exact dependency/source/proof receipts with its original release/runtime interpretation and task/product dependencies. Retained `serve`/native/CLI readers, detached selected-run/cut/task review and evidence readers consume them. IDs are explicit lists, not inferred from counts or maximum IDs. |
|95releases,165runtime bindings,31288archived artifact descriptors,12331input descriptors | Preserve sealed original compiler/runtime/native interpretation. The census selects IDs and content digests, never archive/prepared/input bytes. Retaining migration source alone would not preserve these instances. |
|309runs without a completed-result row;4unpublished native builds | Preserve/quarantine; no implied disposal or fabricated recovery consumer. Retained managed requests refer by run ID to2,17and616; matching numbers alone does not establish current-target recovery applicability. The other306remain sealed pending consumer disposition. Exact stage builds/tasks/runs are listed below. |
|2825configured managed manifests;246archived/copied managed manifests | Preserve exact original action/outcome/custody/hold/artifact metadata and referenced directories for `ci results` inspection/delivery/recovery and retained failures. No managed artifact body, diagnostic stream or observation body was opened. |
|203progressive-review manifests;241semantic/companion/enriched-document exports | Preserve original format, manifest digest, selected root IDs and declared member digests/paths. `serve.review_bundle`, `serve.export`, `serve.companion_export` and detached review readers are the named consumers. Unknown historical target binding remains sealed. |
|397retained evidence records and their declared inputs/outputs | Preserve records, supersession/dependency/consumer metadata and referenced file/directory custody. Every declared input/output path exists by metadata; directory and member bytes were not verified. The owning package and `consumed_by` fields name actual evidence consumers. |

The4unpublished native builds remain explicitly selected for quarantine:

| Build | Run / task | State |
|---|---|---|
| `055436f72f15610e972f59abe9f2343d83db2f045505af5f260f47a28fa68ad1` |344/1550 | open |
| `8d473fb05cabd9b9600426cb72fd068d31f0ca18cb810dda9bc33ee0d469947e` |373/1615 | frozen |
| `afca3eca6fbe5fce228a5090a9523aff6425d8f3d57147d3c5e61b64184bfeab` |352/1559 | open |
| `dc45e031dd4673a14caf608e63419c5449f467b08a51ce062ce62a4cb1347603` |299/1372 | open |

Managed result `0a78c71ce1a949e38e906c9c5392c1f3` is present, `outcome=running`,
`settled=null`, `custody_unsettled=true`. Its manifest has an empty holds array; the operator's
existing preservation hold remains authoritative. Its referenced observations file exists by
metadata. No recovery or settlement command was invoked, and no cause is invented.

## Classification and closure boundary

The3967local manifests classify as3118preserve-sealed,417sealed pending a schema/consumer
disposition, and432generated pytest fixtures. The last class is limited to explicit
`/tmp/pytest/` paths with their named test-directory consumer. It is the only disposable class;
no production completion, source/reference root, retained evidence or unknown workspace is
approved disposable. No correspondence is selected. If new addresses are required later,
reviewed correspondence must keep both identities and preserve original protected material.

The scan roots are this checkout's `build/` and `docs/design_review/evidence/`, with the
configured managed owner `build/ci`. Only exact `manifest.json` and `*/records/*.json`
metadata schemas are opened; payload/relations/source/answer files are only `lstat`ed.
There are2413candidate current-database identity matches and73external/historical identity
references. These73are **not automatically dangling required roots**: retained detached
exports may carry historical interpretations that are intentionally absent from the active
database. Their original manifests/members remain preserved. This metadata-only pass does
not establish replay completeness or guess a mapping for them.

All41949selected source-build/product/visual artifact-digest references resolve to the
artifact pool; all3726source-view/native-product and PDF-input product identities resolve.
The6missing/symlink manifest members belong exclusively to named pytest negative controls
(`test_missing_member_and_undecl` and `test_symlink_member_is_rejecte`), and are retained in
the report as disposable generated fixtures. No missing nonfixture artifact member or evidence
record path was found within the supported parsed schemas. This is an existence/link claim,
not byte-integrity or full detached-read verification.

DDO-00 now has the exact conservative metadata root selection for this acquired snapshot
and declared local universe. Destructive-adoption preservation closure remains **open**:
the future frozen target/source and recovery material are not prepared or tested;417unknown
nonfixture manifests retain conservative sealed custody pending interpretation/consumer
review; incomplete recovery intent is not settled; historical replay applicability is not
proved; and unrecorded deliveries outside these declared owners cannot be finitely discovered
from local metadata. A concrete required external reference discovered later must be included
and resolved before any destructive action. Database and filesystem scans are not one atomic
snapshot; stable per-file metadata reads do not replace a later writer fence/source freeze.

## Commands and result

`uv run ci db status --maintenance --json`: **passed**.
`uv run python docs/design_review/evidence/2026-11-12_ddo-preservation-closure/census.py`:
**passed** for the scoped metadata acquisition/link checks; retained stdout/stderr and
[attempt account](raw/attempts.json). The initial draft **failed** on the nonexistent
`alembic_version` relation before correction to `public.semantic_alembic_version`; that
read-only transaction aborted without a write, and the failure remains recorded.

Product/provider tests, migration, export, restore/replay, result recovery/settlement and
full-series qualification: **not_run**; outside this metadata-only assignment.
The original record remains **partial** for its original snapshot inquiry. The
[classification follow-up](classification-followup.md) and new
[reconciliation record](records/ddo.preservation-classification.json) settle all pending manifest
and historical-reference classifications within the declared metadata-owner scope. DDO-11 freeze,
byte integrity, replay/recovery and settlement remain operational adoption obligations.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**declared-data-operations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Preservation metadata classification and historical custody reconciliation](records/ddo.preservation-classification.json) | DDO-00 | passed | DDO-00, DDO-11 | 2026-11-12 |
| [Metadata preservation roots and declared external custody inventory](records/ddo.preservation-root-inventory.json) | DDO-00 | partial | DDO-00, DDO-11 | 2026-11-12 |
<!-- evidence-index:end -->
