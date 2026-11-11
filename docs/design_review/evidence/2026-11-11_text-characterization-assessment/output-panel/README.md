# Exact output-first panel preparation

`prepare_output_panel.py` is a dated selection script, not a producer or reference author. It reads the exact final combined book view from `../book-result.json`, protected active-layer manifests and only the required retained layer payloads. It neither reads protected reference passes nor runs inference. The source-first panel is immutable and is not an input to output selection.

Status on 2026-11-11: **not_run**, awaiting the final combined view. The script compiles; actual selection and protected author-packet delivery still require that product. It deliberately refuses to replace it with a latest or regional pin.

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/output-panel/prepare_output_panel.py select
```

The frozen frames use guideline `characterization-reference-2`, rubric `chapter-facet-task-semantics-1` and the public semantic-task contract where applicable. Native fidelity and retained identity keep their explicit graph projection modes. The selection covers nine actual-output facets: native evidence, formal structure, predication/roles, operator scope, binding/attachment through actual `declared_binding_site` hypotheses, packed choice compatibility, provider answers, incomplete/unavailable coverage, and retained consumer fidelity. It chooses the first matching bounded object per facet in immutable active-layer/collection order, without selecting for correctness. The native question freezes an actual `native.block` identity so the public output-first native scoring contract can assess complete original-block tokenization. Operator scope selects an actual operator/binder term; binding selects an actual `declared_binding_site` role, rather than an unattached cue/proxy. A missing facet stays explicit. The exposed development panel is purposive, not a probability sample or a book-wide accuracy denominator.

The bounded packet restrictions are explicit in `manifest.json`: at most 12,000 source characters per involved original natural unit, 1,600 direct noncoverage occurrence characters, and a 128 KiB graph preview. Oversized graph skips remain in the manifest. These limits keep actual protected author packets interpretable; they do not reinterpret missing/partial outputs as success. Selected objects carry exact layer/collection/local identities, real original occurrence extents and witness-source pins. Witness closure is interpretation context, not an enlargement of the assessed output population.

After selection, the existing protected owner creates the reference set from `sample.json`:

```sh
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-output-first-facet-panel-2 --split dev \
  --guideline characterization-reference-2 \
  --guideline-text domains/statistics/characterization-task-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/output-panel/sample.json \
  --project nce-grinstead-snell-full-book --json
```

Record its exact receipt and set ID, then deliver protected witness packets:

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/output-panel/prepare_output_panel.py packets --set-id SET_ID
```

`operation_assessment.author_packet` authenticates the source frame and exact selected output, then supplies bounded retained witness closure through the owning projection. Fresh authors judge those packets independently. This preparation contains no authored expected answers or semantic grades.
