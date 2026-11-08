# Chandra mixed-cohort inputs

**Tested · 2026-11-08.** Nine PDFs and 15 physical pages were frozen for CH-10, with
their input SHA-256 pins, parent source pins, and physical page maps in [cohort.json](cohort.json).
The two NIST PRI pages are previously observed development controls. Keep them separate
from the 13 other cohort pages when deciding whether automatic acquisition is warranted.

The retained NIST and Forbes selections are native page excerpts. The two DailyMed
selections are native excerpts from the label sections containing the molecular drawings.
MuPDF 1.23.10 `mutool merge` produced the native excerpts. Keep CDC's whole Arabic PDF
to preserve the document-level AcroForm and its widgets. The NARA input is a single-page
wrapper around the selected archival JPEG. PDFium preserved the embedded JPEG byte for
byte as checked by `pdfimages -j`. The wrapper gives it a 1200-point page height and
keeps the source aspect ratio.

## Original-source expectations

| Cohort input | Independently observable control |
| --- | --- |
| NIST PRI, local pages 1–2 | Known controls from parent pages 141 and 206. Check return-edge direction on the first and two separate parallel arrows on the second. [Earlier control receipt](../natural-diagram.json) |
| NIST PMD, local pages 1–2 | The `Start` node is on page 1. On page 2, the first decision's Yes branch goes to design and data collection, while No goes directly to fitting. The final decision's No branch returns to model selection and Yes goes to `End`. The page-1 connector alone does not establish the cross-page edge. |
| NIST PMC, local page 1 | The prose refers to a possible flowchart without drawing that flowchart on the page. Do not return generated edge evidence as an original graph. |
| NIST EDA, local page 1 | The two-by-three graphic has six distinct labeled subplots. Upper-left is response and predicted values against the independent variable, lower-middle is the histogram, and lower-right is the normal probability plot. The axes are printed and individual point values would be graphical estimates. |
| Forbes, local page 1 | Tables 4.2 and 4.3 are separate. Preserve Table 4.2's (1/4, 1/2, 1/4) in its X rows and Table 4.3's (11/16, 5/16) in its Y rows. Prose beginning below Table 4.3 is outside both grids. |
| CDC Arabic, local pages 1–5 | Preserve Arabic right-to-left sentences with embedded Latin acronyms and numeric suffixes. Page 2 has two separate blank name fields and two unselected alternatives in the `Behalf` group. The two visible Arabic labels distinguish acting for oneself from acting for another person. Native field objects 125, 126, 211, and the group children 124 and 123 distinguish text from radio state. Missing `/V`, actual `/AS`, and a visually empty field have different meanings. Independently check typed discovery of the Arabic heading and actual widget-to-label association. |
| NARA Alaska, local page 1 | The original archival scan has handwriting, strikeouts and ruled fields. Read `Haines Town`, distinguish final field count 336 from Washington total population 343, and associate dwelling units 61 with its printed row. The blank right-side count under persons on ICRs is not the separate printed-row handwritten zero on the left. A visually completed field has no native PDF widget. |
| DailyMed hydrochloride, local page 1 | Check the displayed levalbuterol stereocenter, connectivity and separate HCl marker against the drawing and adjacent author-supplied name. Keep atom placement separate from interpretation. |
| DailyMed tartrate, local page 1 | The left structure has a stereocenter and an explicit multiplicity of two. The right-hand L-tartrate structure is a separate component with its own stereochemistry. The adjacent author text independently identifies the (2:1) salt. A single flattened molecule or one component alone does not preserve the diagram. |

For each material disagreement, record the original input pin, physical page, exact
visible region, supported field or relation, and available incumbent and candidate addresses.
Assess wrong values and unsupported edges independently of a successful parse. Separate
qualified negative, unsupported, and unassessed cases. Where an item warrants evaluation
in actual search or packet delivery, record the precise query or packet result separately
from OCR observations. The hand-entered expectations above cover the listed fields;
they do not qualify the entirety of each page.

Source locations for the public specimens are the [CDC Arabic artifact catalog](https://stacks.cdc.gov/view/cdc/116394),
the [National Archives sample inventory](https://www.archives.gov/developer/1950-census),
and the DailyMed labels for [hydrochloride](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=7e2644e6-36c5-4988-8e52-bec90e2cd2f0)
and [tartrate](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=70a35706-d7a8-4a48-98c6-1cab1c42fe8d).
