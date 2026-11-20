# Serving continuation compatibility

**Review date** 2026-11-20. **Tier/purpose** design/target, bounded to serving authority,
continuation compatibility and execution fit. **Source** `3e0fd0014`, before implementation
of this pivot. **Judgment** accept the proposed target with the conditions below. All source
claims are Interface-checked by static inspection on 2026-11-20. No tests, providers or native
effects were run for this review.

## Review contract and evidence

The operator selected a simpler route after repeated strict D2/T4/T14 failures and approved
separating required navigation from optional persistent reuse. This review examines the shared
serving identity, page envelope, native demand/rich/contribution reads, change-impact, generator
selection and adjacent producer recovery. It uses core 3.3, efficient-architecture heuristics
1.0 and code-intelligence 1.4. The production audit's `5139eaba3` baseline supplies earlier
DA-075/DA-076 context. Current source reading refreshes only this scoped subject and supports
no broader audit claim.

## Responsibility and fidelity

Native PostgreSQL cut/support contracts own permission and the selected population. Query owners
own selection, ordering, diagnostics and bounded projection. Installation custody owns the code
and runtime premises under which a continuation can be interpreted. Disposable caches own only
derived bytes. Producer identity, immutable acknowledgments and native publication own durable
recovery. None of these owners can substitute its standing for another's.

| Fact | Source and meaning | Consumer and constraint |
|---|---|---|
| Native cut and support | Current authorized read of one pinned population | Each resumed request rechecks scope and support before delivering rows |
| Installation identity | Conservative source/resource/runtime compatibility under managed deployment | Cursor interpretation, without claiming complete dependency proof |
| Determining identity | Partial or complete attributed code analysis | Optional cache eligibility retains its existing stronger rule |
| Row ordinal | Position in the query's deterministically ordered population | Replay rederives with the same cut/selection and validates bounds |
| Draft/checkpoint | Acknowledged material and original contributor | UDM-25 keeps native compatible adoption and writer-retirement checks |

## Findings and alternatives

**TR-01 — Compatibility and cache eligibility need separate contracts.** At the baseline,
`ServingImplementation` salts an incomplete identity with a fresh UUID, and
`apply_page_reuse_refusal` clears all cursor and resource handles. Correct fresh results
therefore cannot be paged. Use one stable installation fingerprint for continuation and a
separate stronger proof for cache reuse. An unknown remains attributed and partial.

**TR-02 — Preserve native authority on replay.** Demand, rich and contribution readers already
reacquire their pinned cut/support and rebuild bounded rows on a miss. Use those routes across
processes and after eviction. Preserve selection, exact root, ordinal, examined-data and encoded
response limits. Exclusion retains two cuts. Wrong scope, changed installation, revoked support
and incompatible pins must refuse before data delivery.

**TR-03 — Bound the installation claim.** Capture sorted relative first-party source and
resource names and content, actual Python identity, resolved managed dependency inventory,
selected model and query/profile contract. Include added/removed files. Reuse imported-source
correspondence and metadata checks, requiring restart for unsupported drift. The contract assumes
managed dependencies and excludes runtime third-party monkeypatching. It does not certify arbitrary
loaders or solve determining closure. Application edits can conservatively invalidate more cursors.

**TR-04 — Migrate adjacent consumers together.** Change-impact still calls
`_installed_read_basis` without `wire_digest` and constructs its own custody context. Migrate it
with the eight installed readers and shared CLI/MCP resources. No consumer may use an installation
fingerprint to mark its `CodeIdentity` complete or grant a cache hit.

Continuing the full proof campaign preserves more precise reuse but adds substantial initializer,
compiler and mutable-registry modeling before ordinary pagination is usable. Materializing durable
query snapshots or adding a constrained worker adds new storage, lifecycle or enforcement owners.
Existing bounded rederivation plus installation compatibility is the smallest sufficient route.
It can repeat graph preparation and prefix traversal. That cost is accepted explicitly and is a
future optimization trigger when it obstructs the operator's workflow. There is no speedup claim.

## Judgment and scenarios

A1–A4 support the target within this scope. It improves separation, explicit semantic authority,
local reasoning and execution fit. Core G1–G7 and CI-G1–CI-G3 have credible implementation and
acceptance routes under TR-01–04. G8 introduces no material library-selection question. The
existing custody, hashing, native readers and row iterators supply the needed mechanisms.
Enclosing production architecture and final release qualification remain open under UDM-22–24.

The revealing change scenarios are a new source/resource file, a changed model while an older
capture remains pinned, cache eviction between CLI pages, support revocation before the next
page, and a changed dependency environment. The installation owner invalidates compatibility
where applicable. Native authority remains fresh. Supported data and presentation invariants
are checked independently of cache presence. Producer recovery remains with its own premises.

## Rule impact and disposition

**RC01.** Supersede ADR-0137 and DESIGN §B3/D8's complete determining-closure prerequisite for
continuation compatibility. Cache eligibility retains its stronger proof, and model capture
semantics continue. D2/D4 persistence and cross-request entity hit targets are deferred. T4
becomes safe continuation replay, T14 preserves equal rows and distinct authorized pins, and T20
covers applicable process/recovery behavior. Keeping the prior rule would retain the navigation
block and full proof campaign.

The operator approved RC01 in execution planning. [ADR-0141](../../adr/0141-serving-continuation-and-reuse.md)
records the accepted decision. The UDM [qualification amendment](../../plans/unified-domain-model-and-execution/qualification.md#continuation-compatibility-amendment)
owns implementation acceptance and the scheduled disposition. Old failed receipts keep their
original scope and do not become passes by this decision.

## Acceptance

Use installed demand, rich and contribution CLI reads across fresh processes with empty caches,
plus MCP resources and change-impact. Verify independent rows/order/ordinal/byte expectations,
replay after process cache eviction, wrong scope, revocation, changed installation and model
pins. Authoring retains correct fresh rendering, exact frozen-catalog parity, manifest and
predecessor checks. Run the revised final-source union before canonical adoption. Preserve
producer recovery and the whole-book no-new-provider-work repeat. Review acceptance alone
establishes none of these observed outcomes.
