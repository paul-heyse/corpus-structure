# cattrs

**Realization assessed:** cattrs 26.2.1, which the pivot adopted.

**Researched:** 2026-10-29 by the R4 cluster.
- The [overview](../../../libraries/data_model/msgspec_attrs_and_cattrs.md) was read end to end. msgspec and
  attrs are deferred, so their sections got only what CBO-017 needs.
- The installed `cattrs/gen/__init__.py` was inspected.

## Reusable opportunity types

<a id="cattrs-default-aware-structuring"></a>

### `cattrs/default-aware-structuring`

**Need.** Optional collections that are absent from the unstructured input should become empty
defaults on the structured class.

**Mechanism.** The generated structure functions read a defaulted field only when its key is present,
and otherwise apply the class default (`cattrs/gen/__init__.py:471–501`). This works together with
`forbid_extra_keys` and `detailed_validation`.

**Residual obligations.**
- Defaults must be immutable, for example `()`.
- Defaults must be ordered after required fields, or the fields declared `kw_only`.
- Whether a field was present is not recorded once the input is structured.

## Applicability at source `d739b88`

<a id="applicability-cbo-017"></a>

### CBO-017 — catalog collection defaults: **fits**

Opportunity: [CBO-017](../../codebase/release-preparation.md#cbo-017).

- `_collection_defaults` in `semantic/contracts.py` could be dropped by giving the hand dataclasses'
  optional collections `= ()` defaults. cattrs then fills them in.
- Required fields are already enforced upstream, by the Pydantic and LinkML validation of the
  companion schema.
- Generating the static product dataclasses themselves is covered in the
  [LinkML account](../linkml/README.md#applicability-cbo-017).

## Coverage limits

Installed source only. No structuring run was performed.
