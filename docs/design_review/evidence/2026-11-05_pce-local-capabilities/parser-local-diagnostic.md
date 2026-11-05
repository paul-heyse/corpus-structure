# Retained parser local-channel diagnosis

Status: **Tested**, 2026-11-05. This is a bounded mechanism investigation over
retained task110 and two of its actual source contexts, not corpus accuracy,
calibration, canonical identity or scientific-truth qualification.

Task110 retained 45 successful local GLiNER reports. The raw model results already
contain distribution=0, quantity=471, condition=92 and zero entries for each of
`approximated_by`, `arises_from` and `condition_for`. No unexpected or renamed raw
channel was present; no entity had an attribute field. The contribution adapter
therefore did not discard returned distribution spans or role labels. `role`
applies only to distribution spans, so its absence follows from the absent decoded
distribution population. Relation arrays are present, but the library's public
formatter also supplies empty arrays for requested relations; those arrays do
not expose separate internal relation proposals, counts or abstention decisions.

All 45 model-consumed input hashes reconstruct exactly from retained native
projection pieces and declared separators/suffixes. Input byte counts also match.
All 15 requested native regions link to attempted local contexts; differences
between selected fragment pointers and context pointers reflect retained paragraph
owners. Context8, selected from `#/texts/25`, contains Poisson, binomial and
distribution names. Context1, selected from `#/texts/325` under paragraph owner
`#/texts/316`, contains binomial and normal names. Their absence from the model's
distribution output is not explained by omission of those source passages.
See `raw/parser-local-retained-diagnostic-001.json`.

The pinned GLiNER2 package is 2.1.0, with checkpoint
`fastino/gliner2.5-base-v1`, revision
`54785d51df8d86a0d8f2eb212fec15871aad2c4d`. Context7's
[official span-attribute documentation](https://github.com/fastino-ai/gliner2/blob/main/tutorial/13-span_attributes.md)
and installed `inference/schema.py` / `inference/runtime.py` agree:
`qualify_labels` qualifies model-facing attribute queries while returned attribute
values use their original short labels. It does not rename the distribution
entity channel. The installed decoder assigns attributes after decoding an
applicable entity span; its boundary settings enable both relations and records.

On the same two actual inputs, three explicitly retained schemas—current three
entities plus attributes, the same three entities without attributes, and
distribution only—each returned zero distribution spans and zero relations under
the task's codepoint splitter profile. This rules out attribute qualification and
quantity-label competition as sufficient explanations on those two inputs.
`raw/parser-local-schema-comparison-002.json` retains all six native reports,
source bytes, checkpoint/profile/schema identities, thresholds and preparation.
Attempt001's evidence serialization failed on a Path value; its failed log is
preserved, and the same bounded comparison was repeated to retain its results.

Changing only the explicit splitter recipe to the existing whitespace profile,
with the same checkpoint, source bytes, current schema and threshold0.5, produced:

| Actual context | Distribution spans | Role labels | approximated_by | arises_from | condition_for |
|---|---:|---:|---:|---:|---:|
| 8, selected25 | 7 | 7 | 2 | 2 | 1 |
| 1, selected325 | 1 | 1 | 1 | 0 | 0 |

This establishes a material recipe effect on these inputs. It establishes neither
the correctness of those spans, roles and relations nor completeness of either
input. In particular, a returned role label is a model proposal requiring its own
assessment. `raw/parser-local-whitespace-comparison-001.json` retains both actual
reports. No inference result was published as a new corpus product by these probes.

The original task also stopped after context44's assertion request exceeded the
schema-conditioned subword bound. Its earlier products remained retained, while
16 later family requests were not_run. The evidence driver's direct indexing of
encoded `parse_detail` incorrectly exported NULL stage arrays and an empty gap
list. The driver now preflights a64MiB selected-origin bound and decodes once per origin
in Python through source_python under ordinary writer permissions. No grant to
the internal SQL decoder is required.
The read-only retrospective receipt
`raw/parser-corpus-002-retrospective-inspection-001.json` correctly reports
**partial** with 89 gap rows: 72 partial, one failed and 16 not_run. It preserves
the original sealed34 products and earlier report artifact.

The child had classified every request refusal as a worker fault, and both the
parent and child retired residency. The repaired internal reply carries a typed
request_refused classification. A finite input/preparation refusal preserves the
healthy child; loader, model, cancellation and IPC faults still fence it. The
producer emits explicit zero-output limited or not_run operations for their
declared selection scopes. An independent later request can proceed after a
request limit; a true worker fault prevents later model execution.

`raw/parser-local-refusal-survival-002.json` establishes this using the actual
native child: a 276-subword input is refused under an explicit234-subword budget,
then the 192-subword input succeeds on the same resident PID. Attempt001 exposed
the child's remaining unconditional exit and is retained as failed evidence.
The fix includes a production-child-loop regression rather than relying only on
a controlled reply. `raw/parser-refusal-focused-003.log` passed 46 focused
GLiNER/M1 controls, including later useful output retention through the actual
contribution binder and true-fault fencing. Scoped Ruff and Pyrefly passed.

The operator's broader source/output assessments and the go-forward whitespace
producer run remain coordinator-owned. These findings justify a bounded recipe
correction and request-lifetime repair; they do not close the remaining corpus
qualification scope.

The newly exercised attribute path also exposed a semantic-value defect:
`attribute.role.value` contained the returned label/confidence mapping. A source
author cannot independently supply the model's confidence as source truth.
Local adapter operation `native-local-contributions-2` now retains only the label
as semantic value and uses the existing shared numeric score owner for native
confidence. Raw reports remain unchanged; missing confidence remains missing,
and multiple returned labels remain independently addressable. The same version
constant governs successful, limited, failed and not_run local operations.
Historical version1 reports remain unchanged and readable; the input schema
pack remains `native-local-v1`.

`raw/parser-refusal-attribute-focused-001.log` passed 75 selected adapter, producer
and worker controls, including independent label expectations without confidence,
exact numeric score retention, missing scores, multi-label outputs, binding and
worker lifecycle controls. `raw/parser-attribute-native-001.log` passed actual
protected native completion of a controlled label-only attribute with its separate
score and operation version2. This validates custody and representation, not model
accuracy. Scoped Ruff and Pyrefly passed after these changes.

## Retained consumer and geometry closure

The next retained consumer revealed a separate population defect: replaying only
old `parse_detail.reports` omitted the already sealed local entity, attribute,
cue and syntax products. The implemented forward path now prefers the complete
typed contribution/operation/coordinate-text batch. It preserves product values,
scores, source attribution, operation versions and limited outcomes. The existing
explicit historical source-map/provenance retag follows that preservation; legacy
raw-only reports retain their actual raw reconstruction fallback.

The shared private group consumer also exposes table and definition associations
from declared natural or latent group roles, and captured native geometry. A
unique qualified located primary is required; ambiguous or unlocated primaries
retain only the raw composite. Native blank cell inspection subjects may retain
captured header associations independently of value presence. Missing-role
inspection placeholders supply no attachment target. Caption and note remain
distinct, and no absent unit, note or independent relation evidence is invented.
Association proposals keep the existing question/version and explicitly retain
group mode and producer provenance, without score or public authority.

`raw/retained-typed-forward-003.log` passed 48 focused adapter/M1Readings controls,
including typed population preservation, source/coordinate/limited-operation
preservation, actual `bind_result`, full local consumer input, latent association
and ambiguity cases, captured native headers with blank subjects, and the legacy
raw fallback. Scoped Pyrefly and Ruff passed. The actual forward-derived replay
and independent assessments remain coordinator-owned.

## Read-only whitespace-run recovery

The actual whitespace producer40/task122 completed; only its first evidence
summary failed because an internal SQL decoder was unavailable to its ordinary
writer role. The corrected bounded Python summary requires no new grant.
`parser_retained_readonly_recovery.py` performs no scheduling, finalization or
inference. `raw/parser-corpus-003-readonly-recovery-002.json` and its common pages
recover the original immutable producer under its original runtime006 attribution:

- 7530 retained products: 1594 occurrences, 5136 proposals, 447 composites,
  43 relations and 310 diagnostics.
- 107 distribution proposals and 107 role attributes; 435 quantity and
  19 condition proposals.
- 34 approximated_by, seven arises_from and two condition_for relation proposals.
- **Partial** assessment of task execution: 79 partial stage rows and no failed
  or not_run rows. All planned model requests executed; complete knowledge
  construction is not inferred from execution.

Current project defaults match the earlier saved parser002-after snapshot. The
receipt explicitly states that comparison basis; it does not invent an immediate
pre40 snapshot. Common pages use the existing service with explicit row/byte
bounds. The first recovery attempt was interrupted and its artifacts remain.
No model outputs or prior evidence were replaced during this recovery.

The actual first forward replay then exposed a representation boundary missed by
Python-only fixtures: JSON arrays inside cue/syntax SourceValue objects require
the released decoder's tuple restoration before strict Python binding. Forward
products now pass through `reader.prepared.validate_json` for contributions,
operations and coordinate texts. Canonical JSON bytes must remain identical;
there is no custom recursive conversion or older-byte semantic upcast.

Independent review also found that a schema-pack dictionary key was not checked
against the declaration fingerprint on the typed path. The group consumer now
authenticates that identity before a declaration can authorize an association.
A substituted declaration retains all original typed products and adds an
explicit zero-output unsupported attachment operation; it cannot substitute a
different group mode under the original pack dependency.

`raw/retained-json-forward-002.log` passed 49 focused adapter/M1Readings controls.
They include JSON-roundtripped nested cue/syntax objects, unchanged canonical
bytes, actual `bind_result`, valid natural/latent associations and rejection of a
mismatched pack key/declaration. The first focused attempt's missing test import
is retained in `raw/retained-json-forward-001.log`; it was corrected without
weakening expectations. Scoped Pyrefly and Ruff passed. The coordinator owns the
actual replay under runtime008; no extraction was rerun for this repair.
