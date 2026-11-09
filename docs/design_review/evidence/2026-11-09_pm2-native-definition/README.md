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

**Controlled development route.** Create a private pack copy and prepare its exact
release:

```sh
uv run python docs/design_review/evidence/2026-11-09_pm2-native-definition/private_definition.py stage-pack domains/statistics build/models/pm2/definition-staging
```

Archive and admit that exact staged pack through the existing development release
route after the corresponding native candidate is registered. Bind a private active
input realization. Export the CPU HanLP startup envelope from the retained native
response, then use `private_definition.py parser-request` with the frozen structural
input, its passage ID, the covering sentence extent, model assets, staged release,
and active realization. Submit that JSON using `uv run ci run parsers --request ... --json`.

Use `private_definition.py run-chain` with the completed parser receipt, the exact
naming predicate key, the original input and passage ID, the same realization, and
a run output directory. The script resolves the naming predicate from that
completed cut and issues only the scoped declaration-only operation. Export a
selected-source closure covering both the structural report and its original parser
cut, then verify it without a database connection. Any independent assessment and
retrieval qualification remain separate from the private chain.
