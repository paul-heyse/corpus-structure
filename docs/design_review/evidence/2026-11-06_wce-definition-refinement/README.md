# Definition method refinement on the frozen GS120 inputs

**Tested, 2026-11-06:** bounded method-development replay and functional controls.
This is exposed development evidence. It does not independently qualify the semantic
correctness or completeness of the new proposals, or complete WCE qualification.

The input is the same forty authenticated source projections from physical pages
191–310 of Grinstead–Snell used by native baseline139. The original annotations
are detached through `load_structural_annotations` from their original source cut.
The 149 original raw model replies are read from task544's immutable export. No
PDF, trained linguistic pipeline, GLiNER inference, or database write runs here.

The accepted source-only cases COMMON001/007/016/023/031 and baseline output
reviews were available to the implementer. They are exposed development references,
not held-out evidence. The independent source/output authors own semantic assessment.

## Result and its limits

The unchanged recipes and decoder reproduce baseline139's one named-rule component
and eight model components. The final replay with the revised recipes retains
32 named proposals: thirteen `definition` and nineteen `explanation` readings.
The additional native-display readings include exponential density, expected value,
conditional expectation, variance, and correlation. Counts do not mean that these
are 32 independently supported or complete statistical definitions.

The decoder now preserves an individually role-valid attachment when another
candidate in its window fails. On these exact frozen replies it recovers one model
component, for nine total. **That recovered binomial-distribution → “Chapter 3”
attachment is semantically unsuitable defining content.** It is retained as an
unassessed model reading, not evidence of improvement. Thirteen indexed attachment
role errors remain across the same ten failed windows. Production retains the raw
reply, each rejected candidate's channel/index/reason, and a failed attachment stage
alongside any independently decoded components.

The recipes now cover explicit active/passive “define … to be,” active/passive
“call … [term]” with the correct endpoint orientation, and “defined by/as” or
“given by” followed directly by a source-owned display. Naming and “given by” are
explanation readings. The old compound-based `call_reversed` recipe is removed.
The explicit numbered-Definition label can compose with a trailing copula and the
adjacent native display in that same retained block. Ordinary copulas retain only
`nominal_subject`/`copular_cue` roles; they are not raw defined-term assertions.

Negation suppresses positive attachments while retaining the raw linguistic cue.
Competing role bindings for the same cue remain unresolved rather than selecting
the first subject. A definition whose scope guard stops at a condition does not
lower its numeric head into an unconditional definition. A citation or intervening
prose between cue and native display blocks the formula join. No citation blacklist
or general discourse engine is added.

Remaining quality limits include unresolved anaphora in local naming (“such a
density”), base noun phrases that omit notation or parameters, malformed upstream
syntax, and native formula captures containing recognition errors or mixed prose.
The exact source display is retained without a mathematical-correctness claim.
Conditional and uncued definitions can remain uncaptured. The method version moves
from four to five; the library/model profile and checkpoint are unchanged.

## Retained evidence

- `raw/before001/result.json`: original code/recipes, one named/eight model components.
- `raw/after001/result.json`: initial extension; its conditional/ambiguous proposals
  prompted refinement and are not the final result.
- `raw/after002/result.json` and `raw/after003/result.json`: intermediate refinements.
- `raw/after004/result.json`: final replay, including exact input, rule and implementation
  hashes, source annotation task identities, raw operation counts and rejected candidates.
- `raw/after004/components.json`: compact final candidate input for independent review.
- `summary.json`: count summary and explicit quality boundary.
- `raw/wce-definition-tests003.log`: final forty targeted tests passed with `-n auto`.
- `raw/wce-definition-types003.log`: final scoped pyrefly passed, zero errors.
- `raw/wce-definition-lint003.log`: final scoped Ruff passed.

Earlier test and replay logs are retained. The first typing attempt failed because
the worktree has no environment; the corrected check explicitly uses the main
checkout's interpreter and site packages. No environment was synchronized or changed.

Replay command used from the composition worktree:

```sh
BASH_ENV= PYTHONPATH=/home/paul/corpus-structure-wce-composition/python/corpus-structure/src \
  /home/paul/corpus-structure/.venv/bin/python \
  docs/design_review/evidence/2026-11-06_wce-definition-refinement/replay.py after004 \
  --baseline /home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-gs120
```

The final targeted test command uses that same interpreter/PYTHONPATH with
`-m pytest` and `-n auto` for `tests/methods/test_definition_applicability.py`,
`tests/ingest/test_definition_rules.py`, `tests/semantic/test_structural_source_annotations.py`,
and `tests/methods/test_m1_producer.py::test_witnessed_recipe_is_explicit_versioned_and_rejects_old_writer_config`
under `python/corpus-structure/`.

The scoped typing command is `-m pyrefly check` with
`--site-packages-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages`
and `--python-interpreter-path /home/paul/corpus-structure/.venv/bin/python`, applied
to the changed implementation, tests and replay script. Ruff checks the same files.
Full current production, source custody/publication qualification, and independent
assessment remain with the integrating coordinator.
