# Status

_Updated2026-11-12. BEP GPU-default pivot and audit closure authorized; implementation incomplete.
Full-book execution and book-specific acceptance remain explicitly deferred._

## Current authority

- [Approved BEP closure](docs/plans/book-processing-efficiency-and-parallelism_2026-11-11.md#approved-audit-closure-and-gpu-pivot) owns sequencing and acceptance. Its existing findings table remains the sole E01–14 disposition owner; no audit gap is closed by target acceptance.
- [ADR-0088](docs/adr/0088-gpu-default-native-hosts.md) supersedes ADR-0087's CPU-hybrid selection/global CUDA lane while preserving native capacity, exact source, demand anchors, replay, cancellation and effect guarantees. D3/D4/D6/D8/§B and all five BEP companions are reconciled.
- Target: two shared GPU hosts, Python3.14 (D1/GLiNER/HanLP/spaCy) and3.12 (Maverick/DiPO), bounded model threads and independent streams. D1 remains BF16; other selected learned NLP targets FP32. Gates protect mutable instances/DiPO module patches, not all GPU work. HanLP retains native gradient contexts; spaCy needs explicit Thinc/CuPy context.
- The NLP GPU session begins after capture, never sleeps Nemotron while capture needs it, and restores external custody only after owned hosts die. Shared-host generation fencing and request multiplexing are required production work, not delivered by these docs.
- SourceRunRequest/ResolvedSourceRun/SourceOperationResult target explicit workflow and shared application validation rather than graph-presence inference. E04/E06–14 remain implementation work, including real CLI/Python parity, read admission, CPU teardown, ready refill, batching, native reporting and profile compatibility.

## Delivered boundary and prerequisites

- This increment records the approved target and implements explicit ci test/retry --workers control with requested/observed receipt context. Common GPU runtimes, shared host transport/streams and application request cutover remain unimplemented. No GPU/model run, dependency installation, migration, book run, activation, selection, promotion or push occurred.
- Scoped dependency prerequisites: direct CuPy14.2.0/Thinc compatibility; one root/HanLP lock; common Python3.12 runtime using TensorBoard2.18.0, Protobuf3.20.0, SentencePiece0.2.0 and Setuptools80.10.2 while preserving primary model libraries. Metadata compatibility is not a native pass.
- Initial target counts4regions/4stage runs/8claims/4provider jobs, CPUworkers/submissions2; byte limits unchanged. Running product defaults remain the previous2/2/4/2 CPU-hybrid implementation until coherent cutover and qualification.
- The operator-authored untracked docs/libraries/parsing/torch.md remains untouched and is not included in agent commits. TC plans remain unchanged. Main is the sole worktree.

## Last verified · 2026-11-12

- Targeted `uv run ci test --workers 1 --json -- ...` passed37/37,d057530f1d3a418eb4fa28e548184ece; exact command is in the coordinator's prerequisite-delivery section. Requested/actual1/1. Original cb05ccd28a144464828e06b6b04c44cd retains two corrected harness failures; exact retry c2f7182970794024a71c44afc4629fd6 passed2/2. All held; coverage reports required34/covered34/unresolved0 with original failure/source difference preserved.
- `uv run ci check --only types --view steps --json` passed,e28fb7904cf648469bcc6996f3fc1662; --only lint passed,68d15ea4ca554bcb8386f65e847b3060. `uv run ci docs check --json` passed,c3bd970746ea4a0da25835a118913933,894pages/zero link errors. Initial stale-index publication failure is retained. Final `just turn-end` passed; equivalent final formatting/test literals do not alter tested semantics. Broad/product/native qualification is not_run for this increment.

## Retained evidence and next work

- E05 has no repository/process memory attribution. Do not chase speculative memory causes. Original campaign0a78c71ce1a949e38e906c9c5392c1f3 stays held/unsettled; genuine recovery proof is required and valid refusal remains preserved. Fresh qualification requires excluding conflicting live work.
- Native head semantic_bep_capacity; release03c24857dc91… deployed/admitted, unselected. Retained capture496/cut614/product1627 remains316views/518pages. E01's full-book acceptance and BEP-09 enclosing completion remain open; the full-book consumer utility remains unexecuted.
- Earlier native capacity/recovery/D1 and functional/nonfunctional receipts remain dated source/profile-specific evidence in the coordinator; historical CPU passes do not qualify new GPU hosts.
- Next: finish the shared application contract and locked GPU runtime prerequisites, implement host/multiplexed stream execution and migrate consumers, complete E04/E06–14, independently review assembled source, then qualify the applicable bounded functional/provider/nonfunctional union. Full book stays deferred.
