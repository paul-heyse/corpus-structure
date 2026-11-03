# Native linguistic annotation preparation

**Tested, 2026-11-03:** the private annotation producer completed on the installed CPU spaCy
3.8.18 / `en_core_web_sm` 3.8.0 model for one detached, pinned statistics paragraph. The richer
profile includes the lemmatizer and retains tagger, parser and attribute-ruler output. The
existing sentence-only profile still excludes `ner` and `lemmatizer`.

This is partial M1-04 evidence. Native operation-contract admission, method registration,
database persistence and downstream integration remain open at the
[M1 coordinator](../../../plans/first-production-milestone_2026-11-03.md). Annotation presence
does not establish linguistic accuracy, mathematical meaning, semantic acceptance, model recall,
an improvement in speed or assembled M1 qualification. No GLiNER operation ran here.

## Question and method

Can the richer producer reuse the atom-preserving `TextLayout` and consumer-owned Docs while
retaining source/product/projection/recipe references, complete needed annotation columns and
literal source coordinates through `Language.pipe(..., as_tuples=True)`?

Context7 documentation was refreshed on 2026-11-03 through `/websites/spacy_io` for
[preconstructed Doc processing](https://spacy.io/api/language#pipe) and
[complete annotation checks](https://spacy.io/api/doc#has_annotation). The installed 3.8.18
`Language._ensure_doc` / `Language.pipe` and `Doc.has_annotation` implementations were then
inspected. The receipt hashes those installed source files.

`source-paragraph.json` is an exact copy of the development artifact at
`../2026-11-03_m1-population/cpu-source-paragraph.json`, SHA-256
`9bfe3af34539e94cd7e80bd65e9ceeb9446c155a29f0d427f8ae897c3964c514`.
It retains its selected view/product/projection/recipe pins, native item pieces, original
source snapshot hash and absolute character interval 29–468. This check consumes that retained
artifact; it performs no database access or fresh source-view selection. Native imperfections
such as `theGaussian` remain unchanged. It supplies no independent reference answer.

The helper prepares a layout once, makes a literal reconstruction control, replaces the
resident pipeline's tokenizer with a refusal for the annotation call, and processes two
preconstructed Docs carrying the same explicit source/block pin. It restores the tokenizer
afterward. Source blocks remain separate, token heads remain block-local indices, and native
pieces are retained once with per-token piece indices. No mutable Doc is retained in products.

## Results

`attempt-00001.json` records **passed** for the actual local provider operation. Both detached
products are equal. Each has 77 tokens and three source-projection sentence intervals:
29–228, 229–320 and 321–468. All required `LEMMA`, `POS`, `TAG`, `MORPH`, `DEP` and `SENT_START`
columns are complete according to spaCy. The receipt binds exact input/producer/script hashes,
Python and package versions, effective profile, component factories, pipeline configuration and
dependency identity. `products-00001.json` retains the actual immutable column values.

The elapsed value in the receipt describes this single process section only. It is not a
throughput comparison. Two copies of one passage test batching and source-context carriage;
they do not establish annotation quality or a population-wide resource envelope.

Provider command (**passed**, run from the main checkout's existing environment):

```bash
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-context/python/corpus-structure/src uv run python /home/paul/.cache/corpus-structure-m1-context/docs/design_review/evidence/2026-11-03_m1-annotations/check_annotations.py --attempt 1
```

The helper refuses to overwrite either numbered output. A rerun uses a new attempt number.
The receipt names the exact isolated producer bytes; source changes require reassessment.

Focused tests (**passed**, 22 tests, 2026-11-03) cover the new controlled fixtures together with
the existing sentence tests. Fixtures independently specify repeated whitespace/words, newlines,
combining marks, non-ASCII characters, native formula/reference atom offsets, table-cell/native
piece identity, synthetic separators, missing components/columns and stale layouts. A deliberately
wrong POS label leaves the source-owned formula role and native pointer intact. These are
coordinate/contract controls, not trained-model accuracy evidence.

```bash
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-context/python/corpus-structure/src uv run pytest /home/paul/.cache/corpus-structure-m1-context/python/corpus-structure/tests/ingest/test_annotations.py /home/paul/.cache/corpus-structure-m1-context/python/corpus-structure/tests/ingest/test_sentences.py --strict-markers --strict-config -q
```

Integrated qualification, native database admission and independent linguistic accuracy:
**not_run** in this investigation. Coordinator review/finalization owns acceptance of this result.

## Integrated final private slice

**Bounded Tested, 2026-11-03.** Root integrated the richer producer and private strict record
comparison; the combined annotation/sentence/record-comparison/semantic-alignment command passed75.
Scoped Ruff and Pyrefly passed. `private-checks.json` and `combined-private-tests.log` retain that
scope. This is neither assembled M1 nor a protected reference/published-prediction journey.

Independent review found display-only math metadata was omitted from the detached product.
`AnnotationProduct.display_spans` now retains absolute shared-layout display ranges; a display-only
`x + y` test preserves coordinates/native identity despite deliberately wrong linguistic labels.
The reviewer closed that finding. Sentence-only defaults and tokenization remain unchanged.

Attempt00001 is retained with its original pre-integration producer hash. Root attempt00002 runs
the formatted/repaired producer, with its current source hash, on the same439-character development
paragraph. Two outputs agree:77 tokens, three sentences, six required annotation columns complete;
preconstructed Docs bypass tokenization and the resident pipeline is reused. This establishes
availability/coordinates for that input, not linguistic accuracy or a speed/whole-pipeline claim.

The private record scorer uses explicit source-region/release/guideline pins and independent
reference/prediction policy versions. It compares exact source occurrences one-to-one; required
roles define core agreement, complete semantic fields plus required/meaning-changing evidence
define full agreement, and supplemental evidence defines the evidence view. Candidate/unresolved
standings are separate. It refuses invalid, duplicate, stale and out-of-cut input rather than
silently reducing denominators. This early subset has no paraphrase/numeric-equivalence matcher,
protected reference persistence or completed-publication prediction adapter. M1-13 remains open.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Actual richer CPU annotation availability](records/m1.rich-annotation-operation.json) | M1-04 | passed | — | 2026-11-03 |
| [Private linguistic and record comparison checks](records/m1.private-annotation-and-comparison.json) | M1-13 | passed | — | 2026-11-03 |
<!-- evidence-index:end -->
