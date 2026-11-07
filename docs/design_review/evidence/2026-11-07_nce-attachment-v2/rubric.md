# Defining-text attachment correctness v2

Assess each emitted directed attachment independently using the original text and
native coordinates in the frozen packet. Answer five separate questions for every
emitted relation. A valid term or content span can remain useful if the attachment
fails.

- `attachment_head` asks whether the exact proposed term extent names the term
  being defined. A supported alternative names the exact term anchor IDs.
- `attachment_tail` asks whether the exact proposed content extent carries the
  defining text. A supported alternative names the exact defining-text anchor IDs.
- `attachment_direction` asks whether this emitted attachment runs from the term
  to its defining content. A supported alternative uses the ordered roles
  `["term", "defining_text"]`.
- `attachment_scope` asks whether the exact proposed endpoints form a definition
  in the scope that the native passage supports. A supported alternative records
  `kind: native_section_scope`, `term` and `defining_text` as sorted lists of
  their original native section pointers, and any explicit retained scope or
  effective version. Use the packet's native section lookup. Matching section
  pointers alone do not show that prose defines a term in that scope.
- `defining_text_attachment_correctness` assesses the joint event. A supported
  event has four supported facets and one exact ordered endpoint alternative.
  A contradicted facet makes the event unsupported. Otherwise, ambiguity takes
  precedence over an unassessed facet.

Use `unsupported` for a contradicted extent, interpretation, direction or scope.
Use `ambiguous` for genuine unresolved alternatives and `unassessed` when the
source has not been adequately inspected. Preserve permissible exact alternatives
and state the independent source reason for every case. The development cohort
describes emitted events on two purposively selected views.
