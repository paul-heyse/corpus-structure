# Independent source author B

Date: 2026-11-06. Protocol: `gs120-source-author-1`.

The twelve `packet-<first>-<last>.json` files contain 129 manually authored source cases and 219 exact evidence anchors. This is a selective inventory, not a census. The author read only the twelve neutral Grinstead–Snell source packets and these author B files. No producer outputs, other authors, plans, tests, or original PDFs were inspected.

The inventory distinguishes definitions, parameter declarations, support and scope restrictions, directed implications, counterexamples, model assumptions, numerical examples, exercise questions, procedural states and stopping rules, transformations, table cell roles, physical units, and qualifications. Topics include probability distributions and simulation, exponential waiting times and queue counts, transformed densities, independence testing, expectation and its existence conditions, variance, conditional expectation, fair-game strategies, and discrete/continuous convolution.

Each case records a stable B identifier, granular facet, expected source roles/relationships, exact quoted evidence, source state, judgment, reason and missing facets. Evidence uses zero-based half-open Unicode offsets in the view's `passage.text`. It retains the matching native piece, native item/cell pointer, native provenance, source/view identity and exact supplied excerpt-to-parent page map. A supported judgment describes only the quoted facet. It does not establish a whole derivation, an exercise answer, empirical validity, or a source-wide absence claim.

Coverage accounts for all 40 supplied views and every physical page 191–310. Listed regions identify the text/cell pieces actually read; many read candidates did not become cases. A few captions inspected in native context have no matching projection piece and are separately marked as context-only. The first packet also records the exact tail range read. All original visual regions remain uninspected. Caption-only graphic cases are unassessed. Broken equations are left unresolved; no formulas were assembled from isolated characters or repaired from mathematical expectations.

Eighteen physical pages have no text projection pieces in these inputs: 211–212, 221–222, 231–232, 251–254, 261–264, 281, 291–292, and 301. These pages remain uninspected. Other pages have selective textual coverage; this does not establish complete inspection of any page. Page 282 has only a heading candidate inspected. Original graphs, images, axes, curve alignment, visual-only symbols, unlisted native regions and unsampled table rows remain gaps.

Validation passed on 2026-11-06:

```sh
python docs/design_review/evidence/2026-11-06_wce-gs120/authors/b/author_inventory.py
python docs/design_review/evidence/2026-11-06_wce-gs120/authors/b/verify_inventory.py
```

The first command serializes the manually authored cases and verifies exact source-piece equality. The second independently validates the saved JSON against input hashes, actual projection slices, native items/cells, source/view identities, page maps, ID uniqueness, vocabulary, all views, and all 120 page entries. The receipt is `verification.json`. These checks validate anchoring and inventory structure, not the mathematical truth of a source claim or completeness of this selective inventory.
