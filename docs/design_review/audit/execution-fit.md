# Execution fit

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline and limits](README.md#baseline)). Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`. Nothing on this
page is a measured latency, throughput or memory claim: each finding states work that is
unnecessary or amplified by structure. The integrated view of these findings with the domain
model and the test account is on the [joint page](model-and-execution.md).

Findings of the [production-efficiency review](../reviews/design_review_production-efficiency_2026-11-17.md)
keep their `PE-Fnn` identities and their disposition in the
[DDO plan](../../plans/declared-data-operations_2026-11-12.md). Where one of them is only
partly realized in source, that is recorded on the
[joint page](model-and-execution.md#pe-state), not as a new finding here.

<a id="da-068"></a>

## DA-068 — One digest over every captured native source keys admission, read acquisition and carried assurance

**Delta, 2026-11-17, source `1afa63f88`.** Wider. The captured set gained the shared program layer `native_program.py`, the PDF search and SourceValue generators, three whole logical model files, and the installed versions of pglast, sqlalchemy and linkml-runtime (`semantic/data_operation_storage.py:42–47, 129–140, 241`). A bump of one of those libraries now changes the digest even when the generated SQL is byte-identical. The same program layer and `schema/relational.py` also joined the PDF lowering identity (`semantic/pdf_lowering.py:15–90`), so one edit there changes the kernel digest and refuses PDF certification together. Contrary evidence: the exact generated SQL bytes are now captured beside their generators (`:147–153`), which a narrower identity could use ([delta](README.md#delta-1afa63f88)).

**FP-04/A2, FP-07/A4; DP-04, DP-08, DP-09, DP-10, DP-19; H18, H19.**

`native_source_digest()` hashes every captured `native/*` source
(`semantic/data_operation_storage.py:480–490`). The capture is much wider than the installed
kernel: it includes the bytes of about forty Python modules that generate or consume native
SQL, among them `data_operation_storage.py` itself, the whole `data_operation_projections.py`,
provider profiles, `established_validity.py` and the physical YAML
(`data_operation_storage.py:42–366`; `data_operation_projections.py:2496–2503`). That one
digest is then used as identity in five places:

- baked into the SQL as `__DDO_SOURCE_DIGEST__` and required to equal the installed descriptor
  (`data_operation_storage.py:566, 869–875`);
- the `native_digest` that release admission compares (`sql/admission.sql:50`);
- stamped on each demand read as `kernel_digest`; a different kernel forces reacquisition
  (`sql/data_operations.sql:222–227, 1981`);
- the completion seal that publication compares before skipping its battery (`:1431–1435, 1830–1832`);
- each receipt's `validating_kernel_digest` (`:1868`).

`ddo_require_episode_correspondence` runs the complete original-producer completion battery
whenever a receipt's digest differs from the current one, and by its own comment does not
record that the replay succeeded (`sql/data_operations.sql:1476–1482`). Seven family dependency
validators call it inside validity evaluation (`contextual_admission_native.py:226`,
`operation_event_native.py:322`, `definition_admission_native.py:129`,
`record_grade_native.py:415`, `rich_admission_native.py:483`,
`record_policy_completion_native.py:456`, `artifact_admission_native.py:58`).

**Consequence.** An edit that changes no native behavior (a docstring in a captured module, an
unrelated generator) changes the digest. The comparison is between the checkout's capture and
the installed descriptor, so the trigger is a working-tree edit, not a deployment. From then on:

- every port acquisition refuses until a new native revision is authored and deployed;
- releases prepared earlier fail the admission projection check and must be prepared again;
- every historical episode in those seven families re-runs its full battery on each validity
  evaluation that reaches it (bind, attach, claim, renew, retain, publish, read page). Validity
  is not cached across statements, and by search nothing other than publication writes a
  receipt's digest, so this continues until receipts are rewritten.

The assurance being protected depends on the validator code that ran. The key covers far more
than that.

**This is a documented choice, with one divergence from the plan.** The plan chose the kernel
digest for the seal on the premise that it "covers every completion-validator body", and
specified that a differing or absent digest "runs the full battery as today"
(`docs/plans/declared-data-operations/products-and-support.md:428, 528, 534`). What the plan
did not weigh is that the digest covers about forty other modules as well, or what the replay
costs over time. The plan also said the producer replays inside the dependency validators
would leave validity and be recorded under the kernel digest (`:466–469`). In source they
remain inside validity, gated on the receipt digest, and their outcome is not recorded.
Several validators say in their own comments that they intend no replay on support reads
(`artifact_admission_native.py:59–61`; `definition_admission_native.py:130–131`;
`contextual_admission_native.py:220–222`); the digest gate brings it back after any kernel
change.

**Contrary evidence and what to keep.** Capturing generator source makes candidate authoring
hermetic and attributable (CI-11). Replaying under changed validator code protects a real
premise and fails closed. A narrower identity already exists beside this one:
`__DDO_LOWERING_DIGEST__` is the digest of the generated `data-operations.sql` alone
(`data_operation_storage.py:567–570`).

**Footprint.** Established for the mechanism and the five uses. How often it bites, and the
volume of replayed episodes, are not measured. The plan's record of a candidate refused for
stale contextual source is consistent with it.

**Lead.** Separate provenance (what was captured) from identity (what is installed and what
validated a result), and record a successful replay.

<a id="da-069"></a>

## DA-069 — Implementation identity of source-level operations takes whole files, whole model files and library versions through opaque boundaries

**Delta, 2026-11-17, source `1afa63f88`.** Footprint grew: `semantic/established_validity.py:127–362` is now a generator and is still captured whole by the construction and formal identities ([delta](README.md#delta-1afa63f88)).

**FP-04, FP-07; DP-04, DP-09; H13.**

The compiled model gives each operation an implementation-slice fingerprint over the normalized
source of what it calls. Operations can also declare an opaque boundary whose digest is folded
into that fingerprint (`semantic/python_operation_sources.py:941–973`), and native completion
requires the implementation revision to equal the definition's (`sql/data_operations.sql:1542`).

For the construction and formal families the opaque artifact is coarse:

- `characterization/construction-assets` hashes whole files (`navigation.py`,
  `retained_rules.py`, `forest.py`, `layers.py`, `methods/annotation_rules.py`,
  `ingest/annotation_views.py`), the entire `model/semantic/data-operation-constructions.yaml`,
  and the installed versions of `lark`, `pydantic` and `spacy`
  (`semantic/characterization_ports.py:57–75, 129–134, 183–193`);
- `formal/profile-assets` does the same for twelve whole module files (among them
  `source_products.py`, `characterization.py` and `established_validity.py`), the math grammar,
  transform and TeX modules with the shipped and extension grammars, three model YAML files and
  the `lark`, `sympy` and `pydantic` versions (`semantic/formal_products.py:686–757`).

The finer mechanism sits in the same function: `formal_products.py` itself is sliced to
selected definitions (`:727–745`) while its sibling modules are captured whole.

**Consequence.** An unrelated edit (a helper in `source_products.py` used by another operation,
another product added to the constructions YAML, a patch release of pydantic) changes the
formal or construction implementation revision, so their prior derivations cannot be reused.
Formal is at the root of the characterization chain for the book workload. The plan intends
propagation to stop at an equal admissible value and support
(`docs/plans/declared-data-operations/implementation-contracts-and-fingerprints.md:279–280`);
whether it does was not traced in source.

**Contrary evidence.** The plan explicitly permits "an explicitly coarse module boundary" and
accepts conservative recomputation after some harmless refactors
(`docs/plans/declared-data-operations/implementation-contracts-and-fingerprints.md:258–283`).
Whole-file capture also covers JSON rule files and grammars that slicing cannot see, and
adapter and receipt code is deliberately kept out of recipe meaning
(`formal_products.py:672–684`). This is over-invalidation, not unsoundness.

**Footprint.** Established for the capture; the downstream extent is likely, not established.

<a id="da-075"></a>

## DA-075 — Five of six selected-query cache keys include the acquisition instance, so identical fresh requests do not share an entry

**FP-07/A4; DP-09, DP-10; H12, H19.**

Five of the six cached serving paths include `cut.identity` in the key of
`SELECTED_QUERY_CACHE`: `serve/rich_queries.py:225`, `serve/contribution_facets.py:263`,
`serve/interpretations.py:207`, `serve/structural_products.py:282` and
`semantic/demand_queries.py:200–213`. The sixth, identity-exclusion comparison, keys on the
implementation, the selection and content stamps of the frontier rows, which carry no read
identity (`serve/identity_exclusion_comparison.py:155`; `semantic/demand_results.py:350–354`).
`CutSelection.identity` is the SHA-256 of every pin, including `read_id`, `read_snapshot` and
`frontier_at` (`semantic/demand_results.py:65–104`). A request without a `read_id` makes native
acquisition mint `read:<uuid>`, the current snapshot and the clock time
(`sql/data_operations.sql:1968–1971`).

**Consequence.** For those five paths, two identical requests against an unchanged database get
different keys. A hit can only come from a continuation page, a `resource_handle` replay or an explicitly pinned
re-request, and only inside one long-lived MCP server process. The `ci` CLI runs each page in a
new process (`cli/selected_results.py:96–130`), so it never hits, and the replay cost the cache
was added to remove (PE-F17) remains for CLI paging. On each miss the request re-reads support
into a new temporary index, reopens the release, binds the model and re-validates the graph
(`serve/rich_knowledge.py:118–130`; `semantic/demand_results.py:431–473`).

Two related repetitions share the miss path:

- four consumers page the whole frontier in `recheck_selected_frontier` and then page it again
  under the same read in `selected_record_index`
  (`serve/contribution_facets.py:248–270`; `serve/selected_contributions.py:353–367`;
  `semantic/demand_results.py:401–461`);
- `byte_bounded_page` rebuilds the full report envelope once per accepted row
  (`semantic/selected_query_cache.py:189–200`), and rich entries store the cumulative
  `unknowns` list in every cached row (`serve/rich_queries.py:246–251`), so entries reach the
  8 MiB cap sooner.

**Contrary evidence and what to keep.** Keying on the read makes reuse trivially safe: frontier,
trust snapshot and visibility are fixed. Every request, hit or miss, rechecks native authority
first, and a revocation between pages refuses. The cache itself is well built: byte-accounted,
bounded by entry and row count, immutable encoded entries, a fresh copy on each hit.

**Open premise, already relied on once.** Four consumers compute a content stamp of the
frontier on every request; three then add the cut identity on top of it, and the exclusion
comparison keys on the stamp alone, so within one process its identical fresh requests can
hit. Whether (frontier stamp, release, runtime, selection, implementation) fully determines
the derived rows depends on whether whole-read support visibility is a function of frontier
content. Either that holds at least for product-scoped exclusions, or the exclusion path is
keyed too loosely. The native owner has to settle which.

**Footprint.** Established for the key composition and the two repetitions; how often agents
repeat identical requests is unknown.

<a id="da-078"></a>

## DA-078 — The readiness watermark is coarser than the declared role dependencies

**FP-07/A4; DP-08, DP-10; H5.**

The planner skips re-binding a waiting obligation only when its inputs watermark is unchanged
(`semantic/data_operation_demands.py:730–738`). `_inputs_watermarks` digests, for each waiting
obligation, every fulfilled use of every transitive prerequisite operation with the same
original source, regardless of subject or scope, together with the whole read trust snapshot
and the kernel digest (`semantic/data_operation_projections.py:1825–1951`).

**Consequence.** In the one-book workload every obligation shares one original source, so any
upstream publication advances every waiting obligation's watermark and each round re-binds all
of them. The waiting-obligation skip that PE-F06 intended is then largely unrealized for that
workload. The model declares which roles each operation consumes and from which producers; the
watermark does not use it.

**Contrary evidence.** This granularity is the plan's specification: the watermark is "the
latest visible fulfilled use, population or original among its prerequisite operations and
exact pins" (`docs/plans/declared-data-operations/products-and-support.md:574–575`), with a
soundness argument in `demand-planning-and-execution.md:688–692`. Binding is the authority, so
a conservative watermark cannot admit a wrong result, and an unchanged repeat run still ends
after one round. What the plan text does not weigh is the one-source workload, or that folding
in the whole trust snapshot makes any trust-epoch change advance every watermark.

**Footprint.** The key composition is established. The skip rate in the book run is likely, and
rests on that run's subject and source granularity.

<a id="da-033"></a>

## DA-033 — Admission and binding re-prove immutable release content that earlier steps already established

**Delta, 2026-11-17, source `1afa63f88`.** Changed footprint, substance stands: the projection check is generated by `semantic/archive_projection_native.py:119–300` and performs the same whole-archive re-proof; the native closure is still rebuilt three times on the admission path (`semantic/data_operation_storage.py:947, 950, 1377`) ([delta](README.md#delta-1afa63f88)).

**FP-07/A4; DP-10, DP-19; H12, H18, H19.** Changed footprint; the 2026-11-03 question was
whether cumulative assurance work was avoidable. The publication scans cited then are gone
(`sql/closure.sql` is now admission helpers; publication checks are scoped to the build's own
rows, `semantic/pdf_publication_native.py:743–756`). The current form is narrower and
established.

`data.require_execution_release` runs on every `require_native_execution` call: each port
acquisition, cached-port recheck, publication-port acquisition, definition admission and
activation (`semantic/execution_admission.py:196–221`; `semantic/data_operation_admission.py:268–414`;
`semantic/releases.py:568–619`). Before it reaches its catalog checks it:

- parses the whole prepared archive and re-aggregates every registry row
  (`sql/execution_projection_check.sql:5–27`);
- parses the archive and manifest again and hashes every input and artifact
  (`sql/closure.sql:90–131`);
- parses the archive a third time for diagnostics and re-derives the class closure
  (`sql/admission.sql:24–77`).

Archive publication already ran the first two and wrote `sem.release_finalization`; admission
records `sem.deployment_admission` for the release, physical id and descriptor digest
(`semantic/archive_native.py:150–170`; `semantic/native_products.py:358–378`). Both receipts are
read on this path: the admission body checks that the finalization row exists immediately
before it starts the re-proof (`native_products.py:358–364`; `sql/admission.sql:4–5`), and the
deployment-admission row is recorded only if absent. Neither short-circuits the re-proof. The inspection path runs the full check twice in one transaction
(`data_operation_admission.py:147`; `sql/data_operations.sql:9`).

The same pattern recurs per obligation: `ops.ddo_require_binding` parses and re-hashes
`data_operations.json` and the native definitions for every attached item and passes the whole
archived model into the binding context (`sql/data_operation_bindings.sql:723–741, 795`), and
`ops.select_data_population` repeats it (`sql/data_operations.sql:2147–2155`). The admitted
`sem.data_operation_definition` rows already hold the binding expression and identities, and
other kernel code reads them directly (`:921`). The native source closure is also rebuilt
uncached two or three times per acquisition (`semantic/data_operation_storage.py:873, 876, 1303`).

**What is not in question.** The catalog half of admission (functions, triggers, tables, ACLs,
indexes; `sql/admission.sql:123–183`) guards against deployment drift, which is a live premise.
The per-call kernel paths that carry facts instead of re-proving them are sound
(`ops.ddo_require_release_facts`, `require_pdf_operation`, `require_runtime_binding`).

**Open decision.** Re-hashing would detect tampering by an owner or superuser. The design
already trusts definer roles (DA-029), so whether that premise justifies per-acquisition
re-proof of content protected by immutability triggers is an owner decision about trust.

<a id="da-058"></a>

## DA-058 — Visual recognition re-prepares its runtime every four packets

**FP-07/A4; DP-10; H2, H12, H24.** Changed footprint. The 2026-11-08 manifestations (page
render and original-PDF open per group) are gone: the image is a packet input and a retained
attempt result is reused before inference (`semantic/visual_requests.py:360–378, 439–462`).

The current form: `execute_visual_demand` loops up to 100 rounds; each round runs a full demand
sweep, takes `session.queue(limit=4)` packets and creates a new `_LocalChandraGroup` whose
lifetime is that round (`visual_requests.py:697–710`). Building `ChandraRuntime` hashes every pinned checkpoint file in full
(`ingest/pdf_chandra.py:50–68, 152–157`); the model load, the PDF GPU slot and the Nemotron
suspension follow on the group's first recognition (`visual_requests.py:475–512`).
Without a group, the runtime (including the checkpoint hash) is built before the check for a
retained result (`:583` against `:597`). Checkpoint hashing does not use the process file
custody that other model assets now use.

**Consequence.** Every round re-hashes the checkpoints, and a round that needs any inference
also pays model load, slot acquisition and the service handoff, so these recur about once per
four packets. One invocation covers at most about 400 packets.

**Limits.** Whether the round size of four is deliberate (GPU memory) was not established.
Chandra OCR is outside the current DDO scope by operator direction; this is recorded as the
state of the code, not as scheduled work.

## Prior identities on this page

<a id="da-024"></a>
<a id="da-025"></a>
<a id="da-042"></a>
<a id="da-043"></a>
<a id="da-054"></a>

Earlier text for these is in Git at the publication before this refresh (`fbd3f2a98`).

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-024 | No longer applicable | `semantic/publication.py` is gone; publication is `ops.publish_data_derivation` and PDF validate/seal |
| DA-025 | No longer applicable | Unchanged from 2026-11-03: legacy rendition keying is not on the current path. The unused machinery itself is [DA-080](boundaries-and-composition.md#da-080) |
| DA-042 | Changed footprint | The cited readers are gone. Read paths use `open_release` (PE-F03 implemented). Execution still derives the release at registration and once per host basis, which the production-efficiency review records as a deliberate verification boundary |
| DA-043 | Not re-examined | Last evidence 2026-11-04; consolidation was outside this refresh |
| DA-054 | No longer applicable | The task-dependency projection is gone. Reuse is now keyed by the semantic request identity, which excludes release and runtime. The successor granularity question is DA-078 |
