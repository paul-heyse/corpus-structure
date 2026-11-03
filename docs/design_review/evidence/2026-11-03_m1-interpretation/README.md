# Private M1 bounded record interpretation

**Implemented; scoped Tested, 2026-11-03.** This worker evidence supplies the pure numerical
foundation of M1-09 under ADR-0049 / D5. The M1 coordinator owns package status and acceptance.
Baseline: `1c56a68fa58565d3de783adb3ef7d6a5978ac9ed`; isolated branch
`codex/m1-interpretation`, worktree `/home/paul/.cache/corpus-structure-m1-interpretation`.

The question is whether the three selected typed record operations can preserve whole-reading
event semantics over explicit finite candidates, without substituting MAP, marginal products,
display-only normalization or an invented uniform fallback. Inputs are precomputed log tables,
assignment-relative hard masks, dependencies and candidate-selection declarations. The operation
does not fit weights or contain factor callbacks. Every decision needs an unresolved alternative
with its reason; referent/mention/row identity also needs genuine local/new. Events must include
all template roles and meaning-changing qualifiers, with auxiliary evidence decisions summed
over complete support. Overlapping and duplicate derivations count an assignment once.

The implementation preserves observation, counterevidence, rejected-alternative, retrieval,
selection, model, ontology and policy dependencies for the eventual existing reuse owner.
`semantic/analysis_contracts.py` was inspected: `PreparedInterpretationContext` owns mathematical
parsing contexts and `BoundAnalysisFamily` / `invocation_identity` own admitted input and invocation
identities. This pure foundation defines neither a competing identity nor a cache or lease.
Released operation/schema binding and persistence remain with the coordinator.

The numerical realization uses bounded NumPy blocks and SciPy `special.logsumexp`. Real table,
constraint and declared dependence scopes determine NetworkX connected components; common release
metadata alone does not connect decisions. Components are diagnostic. The initial implementation
guards the **total retained joint**, default 65,536 states, and does not split it. This deliberately
conservative limit establishes neither ordinary component fit nor CPU admission integration.
The workspace guard covers accounted numerical buffers and converted tables; it excludes
caller-owned Python objects, library/runtime overhead and whole-process memory. Cancellation and
elapsed limits are cooperative between bounded numerical calls; this is not a process-memory/time
fence. Limits and actual allocation failures produce resource outcomes without partial probabilities.

## Verification

All final commands ran from `/home/paul/corpus-structure`, using its existing environment, while
`PYTHONPATH` selected the isolated production source. `--confcutdir` confines pytest to this pure
test scope and avoids package-wide runtime/database fixture setup. No database, provider, hosted
model, live default or prior UM validation was involved. Versions/machine are in
[`raw/environment.txt`](raw/environment.txt); final source hashes are in
[`raw/review-final-source-sha256.txt`](raw/review-final-source-sha256.txt).

For these commands only, `W=/home/paul/.cache/corpus-structure-m1-interpretation`,
`S=$W/python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py`, and
`T=$W/python/corpus-structure/tests/semantic/test_record_interpretation.py`.

| Outcome | Command | Receipt |
| --- | --- | --- |
| passed: 54 focused cases | `PYTHONPATH=$W/python/corpus-structure/src uv run pytest $T --confcutdir=$W/python/corpus-structure/tests/semantic --strict-markers --strict-config -q -rA` | [final pytest](raw/review-final-pytest.txt) |
| passed | `uv run ruff format --check $S $T` | [format](raw/review-final-format.txt) |
| passed | `uv run ruff check $S $T` | [Ruff](raw/review-final-ruff.txt) |
| passed: 0 errors | `uv run pyrefly check --site-packages-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages --search-path $W/python/corpus-structure/src $S $T` | [Pyrefly](raw/review-final-pyrefly.txt) |
| failed: 2 initial fixture timing assertions | Initial focused pytest command without `-rA`, before final source | [preserved initial pytest](raw/initial-pytest.txt) |
| failed: 11 union-narrowing errors in tests | Initial `uv run pyrefly check $S $T`, before final source | [preserved initial Pyrefly](raw/initial-pyrefly.txt) |

The initial cancellation/elapsed fixtures relied on a fixed poll count and were replaced with
deterministic second-block triggers. Initial Pyrefly errors were repaired by explicit template
narrowing; the final command also names the shared environment's site packages rather than the
absent worktree environment. No suppression or acceptance weakening was introduced.

Independent implementation review found that dataclass annotations did not protect numerical
boundaries: fractional block/display counts could escape as `TypeError`, NaN state/workspace
limits could bypass guards, and nonnumeric log potentials could escape instead of returning an
outcome. These were reproduced before repair; the observed output is retained in
[`raw/review-malformed-boundary-before.txt`](raw/review-malformed-boundary-before.txt).
The repaired operation validates exact integer counts/bytes and finite nonnegative duration
before numerical arithmetic/allocation; retrieval-count metadata follows the same integer rule.
Unsupported potential types return `invalid_input`, while NaN/+infinity and genuine numerical
overflow remain `numerical_failure`; hard negative infinity remains valid. Twenty-seven added
malformed-input controls exercise these boundaries, including zero allocations for invalid limits.
The earlier 27-case endpoint and its source hashes remain unchanged in `raw/final-*.txt` and
`raw/source-sha256.txt`; `raw/review-final-*` names the repaired 54-case endpoint above.

Independent numerical cases cover a 1:2:3:4 joint/event distribution, event sum versus MAP,
duplicate/overlapping derivations, complete qualifier membership, candidate/axis permutations,
all three fixed templates and local identity, explicit dependence components, hard-zero and
all-infeasible support, NaN/+infinity rejection, finite arithmetic overflow, impossible-state
overflow immunity, extreme common and unequal log weights, normalized coherent displayed
alternatives, configurable state limits, preallocation workspace guards, cancellation, elapsed
limits and actual allocation failure.

Context7 was consulted first for NumPy indexing and SciPy log-sum-exp APIs. Its selected SciPy
result was shallow; consequential behavior was checked against the installed SciPy 1.18.1
`logsumexp` docstring and exercised by the independent numerical tests. No dependencies changed.

## Evidence limits and integration

Exactness is relative to complete **retained candidate support**, subject to floating-point
arithmetic. Scores remain provisional/candidate-relative; omitted candidate mass is unknown.
This demonstrates no empirical calibration, source truth, acceptance/publication policy,
template gain, actual producer integration or workload/component-size fit. Full M1 qualification,
CPU admission, released operation binding, selective recomputation, fit/calibration and
publication are **not_run** here. The root owns integration, final evidence acceptance/record
finalization and assembled qualification. No plan, architecture authority, dependency or shared
schema was edited, and no commit, push, turn-end or main-tree write was performed.

## Integrated endpoint and review disposition

**passed · 2026-11-03:** root integrated the repaired source/test hashes and ran
`uv run pytest python/corpus-structure/tests/semantic/test_record_interpretation.py -q`:54 tests.
Independent implementation reviewer rechecked those exact hashes and closed the malformed-input
P2, with no new material mathematical finding. Tied display order follows declared candidate
order; permutation-independent tie selection is not claimed. This remains pure numerical scope.
