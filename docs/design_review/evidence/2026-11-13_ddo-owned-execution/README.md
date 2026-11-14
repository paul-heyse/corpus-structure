# Owned DDO execution and effective v4 admission

**Execution in progress, 2026-11-13.** The DDO coordinator owns DDO-06–08 state.
This folder retains the immutable native successor required to admit effective v4 stream
settlement and captured capability correspondence. Existing frozen predecessors remain exact.
Preview/candidate/register are preparation only; persistent deployment/activation stays DDO-11.

The source contracts support terminal-atomic settlement. Partial stream prefixes do not publish
fulfillment. Ordinary caller migration and actual owned transport require their own scoped checks;
changing the native archive guard alone establishes neither.

## Registered native successor

**passed, 2026-11-13:** preview `7140393ec9e343f8ad0d46b1130f9ede`, rollback-only
candidate `94b54246db1e44768860589106f1a580`, registration
`7c84e38e315a42f0b333e0a38545488b`. Candidate operation/SQL inspection found exactly two
body changes: `sem.require_execution_projection(text)` changes the current model guard
from v3 to v4; `data.execution_contract_descriptor()` carries its corresponding body hash.
There are zero ordinary schema operations, and owners/ACLs are unchanged.

The new frozen revision is `semantic_ddo_stream_v1`, after `semantic_ddo_projection_v1`.
Candidate binding acquired `corpus_structure_dev`, OID25921445/system7701811359771751232,
port5434, revision `semantic_bep_located_v2`. Authoring was rollback-only; registration writes
four frozen checkout files and performs no persistent deployment/activation. Later source
changes can stale lifecycle previews without changing registered bytes. A future deployment
must reacquire its own current binding under DDO-11.
