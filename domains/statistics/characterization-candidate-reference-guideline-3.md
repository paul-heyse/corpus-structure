# Candidate-question characterization reference guideline

Version: characterization-candidate-reference-3. This adds host/referent question assessment to
[characterization-reference-2](characterization-task-reference-guideline.md). All source-only A/B/C
custody, independent question selection, exact source extents, permissible alternatives, separate
source/output denominators and honest unavailable scope in that guideline remain applicable.
Existing sets and references are immutable. This guideline supplies no production candidates.

Use task `host_choice` for family `character_host_choice_v1` and task `referent_choice` for
`character_referent_choice_v1`, with role scheme `model-question-source-v1`. Reference version is
`characterization-task-reference-v1`; these are additive task variants, not reinterpretations of
variable binding or modal force. An unsupported family/task pairing is contract-unavailable.

The independently authored reference names an `operator` entity anchored at the exact focal
qualifier/mention. Its explicit value is `<task>:<retained answer state>`, for example
`host_choice:proposed`, `referent_choice:no_match`, `referent_choice:missing_candidate`,
`referent_choice:insufficient_evidence`, or `referent_choice:withheld`. The directed `focus` role
connects that question entity to a `source` entity at the same ordered focal source extents.
For a supported positive answer, `host` or `referent` edges connect the question entity to exact
source entities at the selected host/antecedent extents. Complete named slots can close both
`focus` and the relevant endpoint relation. Literal source endpoint entities do not normalize to a
nominal head or a source-text match; they retain the full exact endpoint selected by the question.

A compatible offered host set supplies multiple host edges, one per distinct member. It is not
several exclusive choices or a fabricated union. Nonpositive states retain their own state/focus
but imply no invented host/referent edge. Source evidence can justify unresolved or permissible
alternatives rather than a forced unique antecedent. Missing a candidate is distinct from absence
of an antecedent. Withheld inference is not positive linguistic evidence.

The grader joins selected durable option keys to the exact retained frozen candidate population,
authenticates each candidate's original ordered extents against its qualified retained endpoint,
and preserves explicit external choice requirements. It never authors an answer from a source
scan, accepts an unoffered ID, or substitutes equal text at another occurrence. Output-first
assessment considers only its frozen question roots; context supplied to interpret an answer
is not additional assessed membership.
