"""One native cell-aware formula-enrichment prototype, not application support."""
import json
from pathlib import Path
import pypdfium2 as pdf
from docling.document_converter import DocumentConverter,PdfFormatOption
from docling.datamodel.base_models import InputFormat,ItemAndImageEnrichmentElement
from docling.datamodel.pipeline_options import PdfPipelineOptions,CodeFormulaVlmOptions
from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
from docling_core.types.doc import DoclingDocument,DocItemLabel,RichTableCell,ProvenanceItem
B=Path(__file__).resolve().parent;R=B/'raw'
formula=CodeFormulaVlmOptions.from_preset('codeformulav2')
formula.model_spec.revision=json.loads((R/'heron-85.models.json').read_text())['docling-project/CodeFormulaV2']
opts=PdfPipelineOptions(do_formula_enrichment=True,code_formula_options=formula,accelerator_options=AcceleratorOptions(num_threads=8,device=AcceleratorDevice.CUDA))
converter=DocumentConverter(allowed_formats=[InputFormat.PDF],format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=opts)})
converter.initialize_pipeline(InputFormat.PDF)
pipeline=next(iter(converter.initialized_pipelines.values()))
stage=next(s for s in pipeline.enrichment_pipe if 'CodeFormula' in type(s).__name__)
doc=DoclingDocument.model_validate_json((R/'heron-85.document.json').read_text())
table=doc.tables[0];idx=next(i for i,c in enumerate(table.data.table_cells) if c.start_row_offset_idx==1 and c.start_col_offset_idx==1)
cell=table.data.table_cells[idx];box=cell.bbox
D=pdf.PdfDocument(str(B.parents[3]/'docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf'));page=D[84]
image=page.render(scale=3).to_pil();crop=image.crop((int((box.l-5)*3),int((box.t-5)*3),int((box.r+5)*3),int((box.b+5)*3)));crop.save(R/'cell-crop.png')
item=doc.add_text(label=DocItemLabel.FORMULA,text=cell.text,orig=cell.text,parent=table,prov=ProvenanceItem(page_no=85,bbox=box,charspan=(0,len(cell.text))))
result=list(stage(doc,[ItemAndImageEnrichmentElement(item=item,image=crop)]))[0]
table.data.table_cells[idx]=RichTableCell(**cell.model_dump(),ref=result.get_ref())
doc.validate_document();doc.save_as_json(R/'cell-derived.document.json')
(R/'cell-result.json').write_text(json.dumps({'original_cell':cell.text,'recognized':result.text,'formula_ref':result.self_ref,'row':cell.start_row_offset_idx,'col':cell.start_col_offset_idx,'meaning':'one successful native prototype; not full table coverage or protected publication'},indent=2))
page.close();D.close();print((R/'cell-result.json').read_text())
