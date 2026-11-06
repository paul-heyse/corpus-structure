# Independent source inventory C

Protocol: `gs120-source-author-1`. Author: C. Phase: independent source only.
Completed and verified: 2026-11-06.

Only the twelve neutral `source-packets/grinstead-snell-physical*.json` inputs were read for source judgments. Producer outputs, other author packets, plans, tests and STATUS were not read. No external source, prediction or reference answer informed this inventory. All writes are confined to this author folder.

The twelve matching ten-page JSON files contain 191 selected cases. These are substantial selective inventories, not a census or an assertion that unlisted distinctions are absent. They include semantic role and directed relationship judgments, rather than treating native converter labels as semantic truth. Examples distinguish an exercise request from an executed action, an assumption from a result, expected from observed counts, and formulas from surrounding explanations and scope conditions. Source transcription defects are retained instead of repaired from background mathematical knowledge.

Each case records an exact source quote, half-open Unicode character offsets in the specified source-view passage, the containing native item pointer, parent physical pages, source state and judgment. Input SHA256 is recorded independently for each ten-page packet. `coverage` and `remaining_gaps` bound what was read. Prefix limits, where used, are explicit: text past the displayed prefix was not read merely because its native piece was located.

Verification passed on 2026-11-06 using read-only `python -` assertions over all twelve authored JSON files and their neutral inputs:

- Twelve input byte SHA256 values matched.
- All 191 quoted strings equaled their exact projection slices.
- All 191 spans were contained within a piece of the recorded native pointer.
- Every recorded parent physical page mapped from that item's native provenance through the input `page_map`.
- Protocol and author fields matched.

Selected cases represent 102 physical pages. The remaining 18 pages appear in packet page maps but have no supplied projected native item provenance: 211–212, 221–222, 231–232, 251–254, 261–264, 281, 291–292 and 301. They are explicitly unassessed; this is not a claim that the original PDF pages lack content. Physical 282 has only the supplied projected header represented. Graphical pixels and precise graphical mark geometry remain uninspected throughout.

No cross-author comparison or disagreement adjudication has occurred. That requires separate authorization after this independent inventory is frozen.
