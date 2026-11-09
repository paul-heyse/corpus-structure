# Private native definition witness preparation

The new HanLP layout and definition method have separate registered versions.
Ordinary packs contain no private declaration policy, and their v1 parser and v9
definition extraction remain available. The private policy is a canonical release
dependency staged into a copy of a pack. It carries no source, target, or genre rules.

**Tested on isolated PostgreSQL 18 · 2026-11-09.** The native verifier reconstructed
the v2 source layout, runtime/input hash, typed roles and exact declaration witness
from the same genuine CPU HanLP response retained in the
[earlier probe](../2026-11-09_pm2-definition-chain/README.md). The native witness
matched the Python term, defining content, label, parameter bindings, construction
and naming reference. It rejected a wrong seam, literal, input digest, naming act,
coordination arc and omitted SRL argument. All selected typed frames and their
native occurrence members matched. Missing policy was refused and the exact staged
policy accepted. A staged copy of the statistics pack prepared successfully.
The isolated run exercised the native verifier functions; it did not settle a
deployed application task, activate a release, or grade semantic quality.

**Tested on the deployed private release · 2026-11-09.** Native revision
`semantic_pm2_definition_chain` accepted the [staged release](raw/private-release.json).
CPU HanLP v2 [settled](raw/parser-result.json) as task 2152, run 444, cut 546;
its exact input digest matched the earlier repair replay. The declaration producer
settled as task 2153, run 445, at [final cut 548](raw/chain-completed.json).
The Reader matched the frozen term, content and ordered role basis. The
[deployed native guard](raw/native-qualification.json) accepted the exact retained
component and refused an altered declaration use in a read-only transaction.
The new result remains private. No source recognition, activation, or selection
was performed.

The [exact detached export](raw/review-export.json) and
[manifest-bound verification](raw/review-verified.json) passed under managed result
`3f51e23c5a8c455b9e89c21059f32ef7`. Offline replay accepted the exact component
and refused the [same altered use token](raw/detached-qualification.json).
An [initial diagnostic attempt](raw/detached-attempt-01.txt) failed before replay
because it supplied a path to a relation reader that requires an open directory
descriptor; the corrected diagnostic used the existing secure reader. The bundle
verifies this selected source closure and supplies no independent semantic grade
or whole-book completeness claim.

**Controlled development route.** After the native candidate deploys with the ordinary
statistics pack, set `deployment` to its successful JSON receipt. The private
archive command verifies that receipt, the acquired PostgreSQL target, and the
exact deployed catalog. It archives and admits the private release and creates
its active input realization. It does not select or activate the release.

```sh
driver=docs/design_review/evidence/2026-11-09_pm2-native-definition/private_definition.py
prior=docs/design_review/evidence/2026-11-09_pm2-definition-hanlp/raw/hanlp-layout.json
inputs=docs/design_review/evidence/2026-11-09_pm2-adoption/raw/target-inputs.json
expected=docs/design_review/evidence/2026-11-09_pm2-definition-chain/raw/replay.json
attempt=build/models/pm2/definition-private-01
project=nce-grinstead-snell-full-book
mkdir -p "$attempt"
uv run python "$driver" stage-pack domains/statistics "$attempt/staged" > "$attempt/staged.json"
uv run python "$driver" archive-private --stage-receipt "$attempt/staged.json" \
  --deployment "$deployment" --native-revision "$(jq -r .operation_account.reached_revision "$deployment")" \
  --project "$project" > "$attempt/private-release.json"
```

Submit the source-backed HanLP v2 operation on the same bounded source and CPU
profile. The naming predicate was selected from the earlier exact replay, before
this new run. Keep each receipt in its own file.

```sh
release=$(jq -r .release "$attempt/private-release.json")
realization=$(jq -r .realization "$attempt/private-release.json")
jq '.[1].startup' "$prior" > "$attempt/hanlp-startup.json"
uv run python "$driver" parser-request --release "$release" --realization "$realization" \
  --startup "$attempt/hanlp-startup.json" --assets build/models/pm2 --extent 52043 52499 \
  --inputs "$inputs" --passage binomial-distribution > "$attempt/parser-request.json"
uv run ci run parsers --request "$attempt/parser-request.json" --json > "$attempt/parser-result.json"
uv run python "$driver" run-chain --parser-receipt "$attempt/parser-result.json" \
  --naming-frame "$(jq -r .basis.naming_frame "$expected")" --output-directory "$attempt" \
  --inputs "$inputs" --passage binomial-distribution --realization "$realization" \
  > "$attempt/chain-source-ready.json"
run=$(jq -r .run_id "$attempt/chain-source-ready.json")
uv run ci run finalize "$run" --output-realization "private:pm2-definition:$run" --json \
  > "$attempt/chain-completed.json"
```

Read the exact completed definition and its retained parser predecessor. Export
their selected source closure and verify the delivered files without a database
connection. The earlier replay used here is a frozen transport and role check.
Independent semantic assessment and retrieval qualification remain separate.

```sh
uv run python "$driver" review-selection --chain-receipt "$attempt/chain-source-ready.json" \
  --finalized-receipt "$attempt/chain-completed.json" --expected "$expected" \
  > "$attempt/review-selection.json"
uv run python "$driver" native-qualification --selection "$attempt/review-selection.json" \
  --deployment "$deployment" --native-revision "$(jq -r .operation_account.reached_revision "$deployment")" \
  > "$attempt/native-qualification.json"
uv run ci review export "$attempt/review-selection.json" "$attempt/detached" --exact-closure --json \
  > "$attempt/review-export.json"
review=$(jq -r .invocation_id "$attempt/review-export.json")
uv run ci review inspect --result "$review" --json \
  > "$attempt/review-inspect.json"
digest=$(uv run ci results show "$review" --json | jq -r .details.bundle_manifest_sha256)
uv run ci review verify "$attempt/detached" --manifest-sha256 "$digest" --json \
  > "$attempt/review-verified.json"
uv run python "$driver" detached-qualification --bundle "$attempt/detached" \
  --manifest-sha256 "$digest" > "$attempt/detached-qualification.json"
```

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 3 current, 0 superseded.


**pm2-native-definition**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Native definition chain guard development deployment](records/pm2.native-definition-development-deployment.json) | PM2-03 | passed | I02, PM2-03, PM2-08, PM2-09 | 2026-11-09 |
| [Exact native definition target eligibility](records/pm2.declaration-retrieval-eligibility.json) | PM2-09 | passed | I01, I02, PM2-09 | 2026-11-09 |

**pm2-remediation**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Deployed private declaration chain and matched offline refusal](records/pm2.native-declaration-chain-private-qualification.json) | PM2-09 | passed | I01, I02, PM2-03, PM2-09 | 2026-11-09 |
<!-- evidence-index:end -->
