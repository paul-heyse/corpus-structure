# Execution and qualification

**Interface-checked by source inspection, 2026-11-02.** Baseline and limits are in the
[account](README.md#baseline). No runtime or timing result was produced by this refresh.

<a id="dta-002"></a>

## DTA-002 — Database ownership does not recover interrupted cluster-level test effects

**FP-05/07, DP-19/20/21; H24/25; companion §6/8.** The session-head deployment and fresh clone
separation remains a strength: package `tests/conftest.py:156–225` and semantic conftest retain
real deployment, committed isolation and purpose logins. The earlier repeated-head-bootstrap
manifestation is closed; it is not being reopened merely because bootstrap is expensive.

The remaining distinct effect is `tests/semantic/test_alternate_principal.py:33–90`: it creates a
cluster role and appends HBA/ident rows outside database ownership. Its `finally` attempts both
row removals, reload and role removal, but a killed interpreter cannot execute that cleanup.
`PgAdmin.sweep` (`scripts/native_test_support.py:529–584`) owns authenticated database names, not
roles/authentication rows. The qualification supervisor settles its process group; that does not
remove server-side effects already committed. This can leave residue on the shared cluster after
an interrupted test. It is a structural recovery gap, not an observation that this audit stranded
anything. No new cluster changes or crash experiment was necessary.

<a id="dta-003"></a>

## DTA-003 — Native receipt context still describes ambient settings rather than each acquired clone

**FP-05/06, DP-21/22; CI-04/10 by analogy; companion §6.** `record_server_context`
(`scripts/native_test_support.py:619–647`) reports an actual server version and maintenance
principal but serializes the original Settings, whose application URL is the selected project
rather than the test clone. It does not include each clone/replayed policy/head revision.
The plugin import can return without emitting context, and `classify_receipt` does not require a
native-context event (`scripts/test_receipts.py:376–483`). Reading an ambient URL as the actual
exercise target would overstate reproducibility. This remains a known observation limitation;
it is not evidence that a test actually used the selected application database.

Positive counterevidence matters: native prerequisites have explicit categories, phase outcomes
are preserved, interrupted workers cannot manufacture success, and empty Rust selections remain
`not_run` with no functional coverage. Required-node applicability and mixed source/context union
judgment are external responsibilities, explicitly surfaced by `classify:537–603`. An empty
`required` list is not automatically a classifier defect or assembled qualification.
The former S0 corpus-subset failure claim needs current consumer-specific attribution; the old
file/line/count is not republished as a freshly verified failure.

<a id="dta-017"></a>

## DTA-017 — A real selected project remains the ambient application target during tests

**FP-02/05/06, DP-19/20; H18/25; companion §5/6.** `settings.py:35–37` now selects
`corpus_pdf_20261102`, replacing the old dated target. Package `tests/conftest.py:118–128` still
uses the application Settings unless the CLI helper receives an explicit override. Fixtures
replace database names correctly, but there is no global refused application target for paths
that accidentally bypass a test override. A regression can therefore acquire an unintended
real application connection before a seeded assertion fails. This is a suspected exposure,
not a demonstrated misrouted write.

The disposal concern is separately bounded: `PgAdmin._drop:195–224` checks owner and exact OID
when given an OwnedDatabase, while older comment-based acquisition and the sweeper use authenticated
comments/names. Do not generalize this into unrestricted deletion or resurrect the old catalog
observation about databases the operator has since removed. Existing prefix matching, leases,
exact ownership and restricted principals are substantial protection.

<a id="dta-018"></a>

## DTA-018 — Read-mostly cases repeatedly construct complete write scenarios

**FP-03/06/07, DP-10; H5/12/19/20/27; companion §6/8.** The sealed session schema eliminates
repeated native deployment, but test scenario preparation remains finer-grained. For example,
`tests/semantic/test_serving.py:376–446` assembles a release, inserts project/realization data,
builds occurrences and publishes facts for each caller of `install_pack`; serving matrices
then vary read predicates or response properties. Cross-module scenario hubs amplify the same
preparation pattern (DTA-009). This is demonstrated repeated construction, not a measured dominant
cost or a recommendation to share mutable fixtures.

Fresh commits, independent principals, write refusal and rollback cases have distinct isolation
needs. Any proposed reuse must preserve those needs and complete preparation dependencies.
The old receipt percentages and clone timings are not current measurements and are removed
from this living diagnosis. No blanket cache, fixture-scope or concurrency prescription follows.

<a id="measurements"></a>

## Measurements

No current timing measurement was taken. The prior account's 2026-10-30 receipt retains its
original source and conditions in Git; none of its percentages is a current workload claim.
