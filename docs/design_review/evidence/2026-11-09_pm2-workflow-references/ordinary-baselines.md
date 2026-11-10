# Ordinary baseline availability and protected registration

**Tested, partial · 2026-11-09.** The [read-only inventory](raw/ordinary-baseline-inventory.json) searched completed cuts in the project, matching the exact Standard and Nemotron native product, recipe and projection digest. It found no `retrieve.contextual/10` task for the spinner use and no `structure.scoped_relations` task for the nested frequency case. It resolved M1 run 407/cut 517 tasks 1992 and 1990, including all 1,276 and 1,640 operation rows respectively, and found no contribution overlapping the queried native anchors. The completed-task search is bounded and fails on truncation. These results describe the named methods and exact historical source population, not the absence of any candidate producer or a grade on source truth.

Reproduce without inference or protected writes:

```sh
uv run python docs/design_review/evidence/2026-11-09_pm2-workflow-references/resolve_ordinary_baselines.py
```

**Registration blockers.** The protected [store guard](../../../../python/corpus-structure/src/corpus_structure/semantic/sql/operation_assessment.sql) requires a completed prediction run on the reference set's release, and the [evaluator](../../../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py) requires every exact frozen source view ID in each prediction run. Matching projection digests alone cannot join run 407's views to a new set. A reference set may be created on a sealed source-ready cut; the prediction runs themselves must be completed. On the final release, explicitly select the same retained source view IDs for both arms, reproduce the incumbent if there is no compatible retained output, and then run the already registered comparison.

- **Definition:** run the ordinary literal `/10` route on the exact spinner occurrence and freeze eligible candidates before opening a new output. Register a retrieval frame and a separate fixed-offer interpretation frame if both are assessed. Establish the independent definition target before selecting a link. No exact same-release completed pair is available.
- **Condition:** reproduce the ordinary located condition route at the exact nested frequency opportunity. If comparing the question-level host decision, offer the same authenticated candidates to both arms. Keep outer premise, modality and approximation preservation distinct from choosing the host. No exact same-release completed pair is available.
- **Referent:** do not reuse old task 2131 unless its question and offers exactly match the current frame and the native release/view binding admits it. Freeze the nearest-prior and revised fixed-offer arms over the same authenticated candidates.
- **Loss and fair coin:** historical magnitude-only answers do not supply an amount/unit/role comparator. Separate the three opt-in loss question keys and keep fair-coin magnitude preservation independent of the fairness-premise check.

**Preparing a matched literal set.** Once both literal requests and their registered configuration hashes exist, the [read-only preparation helper](prepare_literal_references.py) validates the common release, exact native view, scope and question order and converts the source-only judgments into the native sample and pass payloads. For example:

```sh
uv run python docs/design_review/evidence/2026-11-09_pm2-workflow-references/prepare_literal_references.py \
  --case fair_coin --from-run "$source_run" --source-cut "$source_cut" \
  --baseline-request "$baseline_request" --baseline-configuration "$baseline_hash" \
  --revised-request "$revised_request" --revised-configuration "$revised_hash" > "$prepared"
```

Use `.sample` for `ci golden operation-create`, then `.frame`, `.actors.A`/`.actors.B` and `.passes.A`/`.passes.B` for `ci golden submit`. Read the registered unit's `ci golden operation-packet --pass C --json` and rerun the helper with `--adjudication-packet` to get `.passes.C` bound to the actual A/B IDs. Keep the sample and answers in evaluator custody; inference receives the explicit request files only. `--case roulette` requires both requests to opt into the exact three-question loss panel. Neither literal set grades premise preservation.

The historical fair-coin requests for runs 429 and 431 passed a preparation dry run on release `d79e9a624…` and cut 531. Pairing those requests with cut 595 was refused on release identity, and reusing the magnitude-only requests for the three-question roulette panel was refused on question identity. These dry runs do not register a new frame or qualify a new arm.

No new model output was opened. New protected sets, A/B/C submission and grading were `not_run`.
