# WCE repair qualification

The [WCE coordinator](../../../../plans/witnessed-corpus-enrichment_2026-11-05.md#completion-audit)
owns the combined acceptance judgment. Test coverage and source benefit use separate
accounts. All provider journeys used the original selected pages and retained model outputs.

## Functional campaigns

On 2026-11-07, `just test-all -n auto` ran the ordinary Python selection with 16 xdist
workers. It returned 5,066 passes and four failures without a worker loss. Native
provenance was complete for all 881 required native nodes in that invocation.
[The raw receipt](test-receipts/ordinary-001/) preserves the failed result.

The four failures were a 30-second CLI subprocess timeout under load, two older
rootless dossier fixtures and an outdated portable refusal message expectation.
The fixture changes exercise the same semantic states through exact roots. The
CLI rerun preserves its original timeout. A new native note test exercises a
whole-note positive and a positive-looking suffix of a contradictory original.

The affected selection covers the contextual method and its native consumers, the
scoped method, dossier and portable fixtures, and the failed CLI identity. The note
test was moved under the semantic fixture owner after its first invocation reported
the fixture unavailable in the methods directory. Both selections are retained.

The contextual revision removes label-only relationship selection. Its methods,
native consumers and retained actual source run receive fresh verification. The
earlier table, artifact, comparison and dossier results exercise the same native
revision and their product routes were unaffected by this final contextual change.

The final affected `just test-all -n auto` selection passed 148 cases. It includes
all four originally failing identities, all directly affected contextual/native
consumers and the new whole-note control. The exclusive `just test-native-faults`
campaign passed eight after the provider and ordinary lanes completed. The two
intermediate affected failures retain their original receipts.

The [required union](union-summary.json) covers 5,079 unique Python nodes,
889 of them native-required, with zero unresolved. The machine classifier retains
the failed original campaign and reports `covered` for the distinct required
union. Product `91c5fa5e9` identifies the native165 behavior used by the broad run.
Final product `07d25b840` changes the contextual producer and the named controls.
The affected final scope re-exercises that producer, its native consumers and
the changed tests. Table, comparison, rooted dossier and artifact implementations
and their native schema are the same across these later contextual reruns.
The final retained contextual run has its own producer runtime under the same
semantic release. The earlier unexplained native GC fault did not recur in these
campaigns.

```sh
w=docs/design_review/evidence/2026-11-06_wce-completion-repair/qualification
uv run python scripts/test_receipts.py classify \
  --receipt-dir "$w/test-receipts/ordinary-001" --required-from "$w/required-ordinary-001.json" \
  --receipt-dir "$w/test-receipts/affected-final-003" --required-from "$w/required-affected-final-003.json" \
  --receipt-dir "$w/test-receipts/native-faults-001" --required-from "$w/required-native-faults-001.json"
```

`just hygiene` and `just turn-end` passed on the final source. Rust nextest selected
zero cases, recorded as `not_run`. The retained toolchain is
`rustc 1.101.0-nightly (2d20b42b8 2026-11-04)`. The qualification account covers
software behavior and transports within the stated selections. Source assessment
and the remaining acceptance obligations are in the coordinator.
