"""Bounded native Docling investigations, not a production adapter."""
import argparse, json, dataclasses, traceback
from pathlib import Path
from hashlib import sha256
from importlib.metadata import version
from huggingface_hub import HfApi
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
 PdfPipelineOptions, RapidOcrOptions, OcrMode, LayoutObjectDetectionOptions,
 CodeFormulaVlmOptions, HeadingHierarchyOptions, TableStructureOptions, TableFormerMode,
)
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice

BASE=Path(__file__).resolve().parent
# Repository root is the fourth parent of this evidence folder.
SOURCE=BASE.parents[3]/'docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf'

def main():
 p=argparse.ArgumentParser();p.add_argument('--layout',default='heron');p.add_argument('--pages',default='85:85');a=p.parse_args()
 ranges=[tuple(map(int,x.split(':'))) for x in a.pages.split(',')];name=f'{a.layout}-{ranges[0][0]}-{ranges[0][1]}'
 layout=LayoutObjectDetectionOptions.from_preset('layout_heron_default' if a.layout=='heron' else 'layout_egret_large')
 formula=CodeFormulaVlmOptions.from_preset('codeformulav2',scale=2.0,expansion_factor=0.18,stop_on_repetition=True)
 manifest={}
 for spec in (layout.model_spec,formula.model_spec):
  repo=getattr(spec,'repo_id',None) or spec.default_repo_id
  rev=HfApi().model_info(repo,revision=spec.revision).sha
  spec.revision=rev;manifest[repo]=rev
 (BASE/'raw'/f'{name}.models.json').write_text(json.dumps(manifest,indent=2))
 opts=PdfPipelineOptions(do_ocr=True,ocr_options=RapidOcrOptions(backend='onnxruntime',lang=['iso:en'],model_size='small',mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS,replace_broken_text_layer=True),do_table_structure=True,table_structure_options=TableStructureOptions(mode=TableFormerMode.ACCURATE,do_cell_matching=True),do_formula_enrichment=True,code_formula_options=formula,layout_options=layout,heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),accelerator_options=AcceleratorOptions(num_threads=8,device=AcceleratorDevice.CUDA),document_timeout=600)
 (BASE/'raw'/f'{name}.options.json').write_text(opts.model_dump_json(indent=2))
 converter=DocumentConverter(allowed_formats=[InputFormat.PDF],format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=opts,backend_options=ThreadedDoclingParseBackendOptions(parser_threads=8,max_concurrent_results=8))})
 for start,end in ranges:
  name=f'{a.layout}-{start}-{end}'
  result=converter.convert(SOURCE,page_range=(start,end),raises_on_error=False)
  doc=result.document
  doc.save_as_json(BASE/'raw'/f'{name}.document.json')
  summary={'status':str(result.status),'errors':[e.model_dump(mode='json') for e in result.errors],'pages':list(doc.pages),'items':[{'ref':i.self_ref,'label':str(getattr(i,'label','')),'text':getattr(i,'text',''),'orig':getattr(i,'orig','')} for i,_ in doc.iterate_items()], 'tables':[t.data.model_dump(mode='json') for t in doc.tables]}
  (BASE/'raw'/f'{name}.summary.json').write_text(json.dumps(summary,indent=2))
  print(json.dumps({'status':summary['status'],'items':len(summary['items']),'tables':len(doc.tables),'errors':summary['errors']}),flush=True)
  result.input.release()
if __name__=='__main__':
 try:main()
 except Exception:traceback.print_exc();raise
