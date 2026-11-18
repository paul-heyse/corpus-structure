# Witnessed enrichment

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
The three identities below were re-read at that source by reading the current owners of table
interpretation, local interpretation reports and structural dossiers. Their first publication
was 2026-11-06 at audit publication `86425f72e`, and their full earlier text is in Git there
and at `fbd3f2a98`. Source paths omit `python/corpus-structure/src/corpus_structure/`.

The anchors of these three identities use upper-case ids (`#DA-055`, `#DA-056`, `#DA-057`),
unlike every other page of this account. They are kept as they are because existing links use
them.

<a id="reconciliation-at-the-november-8-baseline"></a>
<a id="DA-055"></a>
<a id="DA-056"></a>
<a id="DA-057"></a>

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-055 | Corrected, holds | Header levels and separate note or unit attachments get separate axes; only competing readings of the same level and role are exclusive (`methods/table_interpretation.py:313–333`) |
| DA-056 | Corrected (`f3f2d1ca5`) | The gap recorded as open on 2026-11-08 (an event probability could contradict the displayed support) was corrected one hour after that restatement, and this page was not updated then. Each marginal and each event is now bounded against the displayed support (`semantic/local_interpretation_reports.py:285–308`), on the bind path that `semantic/contributions.py:267–270` and `semantic/observations.py:374` reach. The native counterpart, in a hand-written SQL file, was deleted in `3812d31cf`, and no generated native module checks event probabilities (search of `semantic/*native*.py` for probability, marginal and event checks only). Whether native admission still needs these checks was not established |
| DA-057 | Corrected, holds | Member identity includes the definition interpretation and the applicability outcome (`methods/structural_products.py:1235–1257`), and admission derives it again with the same fields (`semantic/structural_admission.py:242–248`) |

The [WCE coordinator](../../plans/witnessed-corpus-enrichment_2026-11-05.md) holds the recorded
disposition of the original findings.
