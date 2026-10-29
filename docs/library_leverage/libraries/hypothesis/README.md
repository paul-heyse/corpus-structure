# Hypothesis

**Realization assessed:** Hypothesis 6.170.12, run as a pytest plugin.

**Research:** 2026-10-29 by the R2 cluster.
- The [overview](../../../libraries/hypothesis.md) was read end to end.
- The installed `_hypothesis_pytestplugin.py` and `hypothesis/_settings.py` were inspected.
- A pytest route probe compared the `ci` and default profiles
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-postgres-migrations/README.md)).

## Reusable opportunity types

<a id="hypothesis-route-profile-and-replay"></a>

### `hypothesis/route-profile-and-replay`

**Profile selection.** `--hypothesis-profile` loads the named profile at `pytest_configure`. It
overrides a profile that a conftest loaded at import from an environment default (probe-observed).

**Settings that interact.**
- `derandomize=True` implies `database=None`. Passing both raises `InvalidArgument` (installed
  source).
- `print_blob=True` puts `@reproduce_failure(version, blob)` into the failure text, and so into JUnit
  output (probe-observed).

**Replay.** Blobs are locked to the Hypothesis version. Durable regressions belong in `@example`.

**Side effect.** A `.hypothesis/constants` cache is written even with `database=None`.

<a id="hypothesis-differential-native-parity"></a>

### `hypothesis/differential-native-parity`

**What it combines.**
- Lexical input strategies: `st.from_regex(pattern, fullmatch=True)`, `st.decimals`, and
  `st.text(st.characters(...))`.
- A differential property that compares a Python implementation with a native SQL function on every
  example.
- `@example` for pinned, independent vectors.

**Conditions.**
- Pure SQL functions need no isolation between examples.
- A stateful database fixture must not be function-scoped under `@given`
  (`HealthCheck.function_scoped_fixture`). Use per-example savepoints or a longer-scoped engine.
- Unicode versions must match on both sides.
- Agreement between the two sides does not prove the shared specification correct (see
  [LOP-X003](../../assessment-patterns.md#lop-x003)).

## Applicability at source `d739b88`

<a id="applicability-cbo-015"></a>

### CBO-015 — mirrored typed-value codec: **fits with conditions**

Opportunity: [CBO-015](../../codebase/storage-and-analytics.md#cbo-015).

- `data.decimal_canonical`, `data.canonical_json` and `data.value_meaning` can be called as
  `SELECT`s, so a differential property between Python and native code is straightforward.
- Generate decimal lexicals from the repository's own `_DECIMAL` regex with `fullmatch=True`. That
  also exercises the exponent-form question raised by `str(raw)`.
- Python 3.14 uses Unicode 16.0.0. Revision 0003 already asserts casefold parity natively.

**Prerequisites.**
- An engine that is not function-scoped, which depends on the
  [CBO-010](../postgresql/README.md#applicability-cbo-010) template.
- Pinned `@example` vectors that are independent of both sides.

**Residual.** Owning one written specification of the canonical form.

**Pyarrow cross-check.** Treat any vectorized fast path as another mirror and test it at the edges:
pyarrow 26's decimal256 rounding is wrong on carry patterns (see
[pyarrow](../pyarrow/README.md#pyarrow-exact-numeric-boundary)).

<a id="applicability-cbo-011"></a>

### CBO-011 (informs) — replayable generated cases: **fits**

- The qualification route can pass `--hypothesis-profile=ci`. This works with the current conftest,
  because the command-line flag overrides the environment default.
- Failure blobs then appear in JUnit.

## Coverage limits

- Only the profile route was probed.
- No differential property was run against a database.
