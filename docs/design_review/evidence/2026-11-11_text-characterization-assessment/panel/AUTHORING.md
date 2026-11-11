# Independent source-only authoring instructions

Use the frozen `author-unit-ID.json` packet and its corresponding selected `source-view-ID.json`
packet, plus the characterization reference guideline. A and B must run in fresh Sol/high sessions
without reading each other's answers, producer outputs, candidate parse trees, tokenizers or NLP
models. C later reads the source and retained A/B passes and supplies adjudication reasons.

For each unit, copy its frozen envelope from `source_frame.evaluation_frame`:

- `protocol`: `source-operation-reference-1`
- `release_id`, `rubric_version`, `context_policy`, `operation_question`, `operation_version`,
  `domain`, `direction`: exact frozen values
- `unit_ref`: frame `unit`; `guideline`: frame `guideline_version`
- `reason`: substantive source-only authoring account; `adjudication_passes`: empty for A/B
- `cases`: independently authored case list

Each case names its frozen `opportunity_id` and `facet`, unique `case_id`, honest `inspected_scope`,
judged `source_state` (`stated`, `unstated`, `unresolved`, `inapplicable`, `uninspected`),
`judgment` (`supported`, `unsupported`, `ambiguous`, `unassessed`), independent `alternatives`,
source-grounded `explanation`, `assessor_provenance` with actor/source-only exposure, and the
question's `required_family`. `anchor_ids` may be empty: the frozen opportunity already fixes
ordered real source extents. Initially uninspected opportunity state may be independently judged.
Uninspected cases remain unassessed. Do not assign output IDs, layer pins or contribution IDs.

For compatible native questions, supply `native_reference` with explicit version
`spacy-native-reference-v1`, scheme `spacy`, exact complete original block `text`, independent
`words` and parallel boolean `spaces`. Those arrays must reconstruct the exact text, including
newlines/whitespace tokens where necessary. Do not normalize or obtain tokenization from a model.
Native-reference cases have empty alternatives and no graph/candidate selectors.

- Sentence questions: kind `spans`, span_key `sents`, labeled false, independent block-relative
  sentence start/end extents.
- Token questions: kind `tokenization`; independent atom-preserving words/spaces are the gold.
- Dependency question: kind `dependencies`; zero-based head indices/self-headed root and original
  spaCy dependency labels. Missing independent labels remain explicit null pairs.

For other questions, independently author the declared semantic structure and permissible
alternatives. Pure scalar/source properties may use value alternatives and a narrow declared
collection selector. Role, scope, binding and choice expectations require a source-semantic graph
with independent local IDs, directed edges, ordered source extents, shared identities and correlated
branches preserved. Do not reproduce a producer trace, invent future execution identity or reduce
those questions to label presence. Source-semantic graph projection excludes incidental execution
identity and scores. If the available source does not justify an answer, record that limitation;
do not invent a forced reading to satisfy a case count.

Source-side coverage questions specify the source scope that examination must cover, not a claim
that a future runtime succeeded. Source-first preservation questions identify original extents and
occurrences; later output-first inspection binds exact layer/choice identities and actual replay.
