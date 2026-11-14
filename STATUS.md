# Status

_Updated 2026-11-13. DDO-00–05 foundation scope is complete. No production deployment, activation or cutover._

## DDO authority and implemented scope

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#ddo-0005-resumed-execution-and-scoped-acceptance--2026-11-13) owns package/finding state and required-scope reconciliation. DDO-00 preparation remains complete; DDO-01–05 implementation, scoped retirement and applicable targeted acceptance are complete. DDO-06–12 remain open.
- Effective v3 carries compiled projection interpretation consumed by semantic graph validation and selected demand closure. Current v1 authoring/decoding and the unused trusted-call alias are retired; exact historical v2 reading cannot authorize current native or Python execution. TS-19's earlier helper removal is preserved.
- Captured standard builtin references and runtime dictionaries are authenticated across direct/helper/generated/stream ports. Complete-context native population closure preserves ADR-0100 JSONB meaning; actual scoped discovery reaches child publication.
- [Source evolution](docs/plans/declared-data-operations/source-evolution-and-migrations.md) owns implemented finite source-migration preparation, LibCST APIs/references, proposed-model compilation and readiness/effect custody. Signature changes, dynamic lookup, unresolved re-exports and destination collisions do not silently become completed migrations; later caller/interface adoption remains open.

## Scoped verification · 2026-11-13

- **passed:** `uv run ci test --json --` source/compiler/ports/model/projection/demand/preparation263, `3a40d30d38934ef189b1c6b1ba547379`; binding/wire/parameters/source-set/subject/population/consumer108, `792326c6afa247acbd2a5e48843b5186`; final ports70, `abf6354897214e21b53e908235a24f59`.
- **passed:** source-migration19, `c498044acb2e4fdea7d662f285434c60`; final historical-port/subclass refusals2, `564cfbcfb212476cbf9f8def8b6bb939`; input-closure/keyword controls2, `2ce0522bf5e94a96835c43ae7338ccf8`. The coordinator preserves earlier failed attempts and scoped replacements. Independent implementation review: Accept scoped by source inspection.
- **failed, retained:** native94 `07021252b8464b599428d0d3655957e0`,91passed/3failed. **passed:** final replacements10 `09ecb5f88e5f476a9ed8bcd226e30829`, covering seed setup, corrected typed population cases, final-port production source publication/resume and independent null-scope controls. One obsolete invalid-schema parameter identity is explicitly removed from the current required inventory; raw original-inventory coverage correctly remains unresolved for it.
- **passed:** seed controls6, `68fdc68fe1be422191a231671ce8e48d`. Cached validation reuses the existing bounded backend-exit waiter and retains persistent-session refusal. No backend termination or confirmed leak claim.
- **passed:** `uv run ci check --only types --json`, `1aa76272c86f4293a864e4b11012deb6`; `uv run ci check --only lint --json`, `b46defb5ea8a4c6395514f274b524e14`. `uv run ci docs check --json` passed `c5d40d6ecf3e4a3890a4329cb02edb95`; root maintenance made no final source changes.

## Native custody and next work

- [Authoring evidence](docs/design_review/evidence/2026-11-13_ddo-projection-context/README.md) owns preview `10a81274757548a084cad38f26fd10da`, rollback-only candidate `7ccd25c86a534675a5db847dc2d5db27` and registration `7c5d74466b734072bc47ffe8848516b7`: **passed**, four native transitions/zero schema operations. Exact registered bytes remain verified; later prep-only guards stale the old preview generator.
- `semantic_ddo_projection_v1` follows `semantic_test_pdf_seal_producer`. The persistent working database retains `semantic_bep_located_v2`, OID25921445/system7701811359771751232. Frozen predecessors, protected sources and interrupted receipts remain intact.
- Next work belongs to DDO-06–12: physical/native streams, ordinary producer/caller/serving migration, reuse, adoption and assembled qualification. TS-21 transfers controls with actual retirement; TS-22 remains gated to DDO-12. No later package is started here. No push.

## Test system: execution closed; qualification deferred · 2026-11-13

- The [coordinator](docs/plans/test-system-target-design_2026-11-13.md#execution-close-out--2026-11-13) owns TS-00–25, current findings and receipt applicability. Keyed heads, isolation, generic seeds, SQL batching and provider selection are implemented; non-gated consumer migrations are implemented and final qualification is deferred by operator. Benefits are Proposed, unmeasured.
- **passed:** targeted `uv run ci test` selections: record seed/refusal50 `5582aa6fa10a439db49782432a692b19`; PostgreSQL compiled-binding35 `ac8e56c2984943efbefb5add2c375690`; complete-result perturbations6 `3345772ed6174e2fa9edcd1b86e5c61e`; binding-source seed25 `cd5b7d3f4183405087bc35d92b368e20`; source/identity/JSON rollback24 `afb0de834cc64fafb590408c033bcf80`. These are bounded evidence, not final union credit.
- **passed:** actual private PostgreSQL infrastructure9/two workers `38db958326b24a66a670e740eb8a0464`; private SQL family19 `8bbf9bb6a7fe4c3a97fd12d7f96a3650`. Private retry reports a new incarnation; deliberate interruption retains incomplete execution with settled custody and captured logs. [Tooling companion](docs/plans/test-system-target-design/postgresql-tooling.md) owns the contracts.
- Both authorized [PDF repairs](docs/design_review/evidence/2026-11-13_test-system-pdf-guard-repair/README.md) use immutable successors; current-model replay controls passed. Persistent revision/OID/system remain unchanged. Those PDF repairs did not perform DDO deployment, adoption or cutover; TS-21/22 retain their gates.
- **passed:** pre-Unicode-metadata-repair `uv run ci check --json`, `efadf0f11b3943b6a39e1069e11b5f7a` (all applicable checks), and `uv run ci doctor --json`, `7d94b9efb3784e699c56d250566743b8`. The later source diff changes exact qualified PG18.6 metadata to fully qualified PG18.7; folding/admission algorithms are unchanged.
- **passed:** `uv run ci docs check --json`, `047fa7ac07b742429ea7b18e21d4c94f`,1255pages/zero link errors before final close-out wording. No further health checks, per operator.
- **Interrupted by operator:** `uv run ci test --json`, `087abdd3b95d49409c305105165fa6cb`: 2688 passed, 2 failed, 1 blocked, 16 incomplete, 5194 not_run; child custody settled. Fault/Rust not_run. All16 workers observed one fresh run-private head with no deployment-key gap. TS-23 qualification remains open; scoped findings closure is distinct.
- **Closed out by operator:** focused replacement `25a39bdc146e4c0f95c5440ec554f5c3` was also interrupted, two incomplete; custody settled and both receipts held. PG18.7 metadata is corrected after exact Unicode-pair qualification passed. No test-system run remains active; no further tests or health checks. Independent review is Accept scoped; TS-21/22 stay DDO-gated. Global Ruff E501 remains excluded and frozen migration bytes protected.

## Agent reference guidance · 2026-11-13

AGENTS.md now describes optional Context7 use for implementation approaches, examples and options,
with query framing and version awareness. `uv run ci docs check` **passed**, `0c4f263917dc452389bbdb682632c7d3`.
Product tests and whole-repository checks are **not_run** for this documentation-only change.
