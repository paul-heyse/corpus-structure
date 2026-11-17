# Witnessed enrichment

**Source `fbd3f2a98`, 2026-11-17** ([baseline and limits](README.md#baseline)). This refresh
did not re-examine the witnessed-enrichment transformations (table multiplicity, displayed
probability support, dossier meaning). The observations below keep their original evidence
dates, 2026-11-06 and 2026-11-08, and several of the modules they cited no longer exist. Their
full text is in Git at `fbd3f2a98`, and the earlier diagnosis wording at audit publication
`86425f72e`.

<a id="reconciliation-at-the-november-8-baseline"></a>
<a id="DA-055"></a>
<a id="DA-056"></a>
<a id="DA-057"></a>

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-055 | Not re-examined | Corrected at the 2026-11-08 baseline |
| DA-056 | Not re-examined; cited sources retired | The cross-result numerical consistency gap was open on 2026-11-08. `serve/table_correspondence_replay.py` is gone; detached verification is now `semantic/demand_results.py:476+` and `serve/demand_export.py:409+`. Whether the gap survives there was not traced |
| DA-057 | Changed footprint | The dossier Reader is `serve/structural_products.py:194–345`; membership, facet and policy digests are bound into the cursor (`:328–337`) |

The [WCE coordinator](../../plans/witnessed-corpus-enrichment_2026-11-05.md) holds the recorded
disposition of the original findings.
