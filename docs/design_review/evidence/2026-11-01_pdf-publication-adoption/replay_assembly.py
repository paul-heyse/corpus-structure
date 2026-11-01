"""Replay actual retained page assemblies through native reading order; no page inference."""
import json
from pathlib import Path
from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.base_models import AssembledUnit,Page,InputFormat
from docling.datamodel.document import ConversionResult,InputDocument
from docling.models.stages.reading_order.readingorder_model import ReadingOrderModel,ReadingOrderOptions
from docling_core.types.doc import BoundingBox
from corpus_structure.ingest.pdf_assembly import derive_v1_assembly_types,restore_assembly


def main():
    original=Path('docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf')
    source=InputDocument(path_or_stream=original,format=InputFormat.PDF,backend=ThreadedDoclingParseDocumentBackend)
    result=ConversionResult(input=source)
    try:
        pages=[]
        for path in sorted(Path('build/pdf-remaining-native-book/pages').glob('page-*.json')):
            value=json.loads(path.read_bytes());raw=dict(value['page']);raw['assembled']=restore_assembly(raw['assembled'],derive_v1_assembly_types(raw['assembled']));page=Page.model_validate(raw)
            page._shape_lines=[BoundingBox.model_validate(x) for x in value['shape_lines']]
            page._shape_bounding_boxes=[BoundingBox.model_validate(x) for x in value['shape_boxes']]
            pages.append(page)
        result.pages=pages
        result.assembled=AssembledUnit(elements=[e for p in pages for e in p.assembled.elements],body=[e for p in pages for e in p.assembled.body],headers=[e for p in pages for e in p.assembled.headers])
        result.document=ReadingOrderModel(ReadingOrderOptions(use_page_separators=True))(result)
        print('passed reading order',len(result.document.texts),len(result.document.tables),flush=True)
        Path('build/pdf-remaining-replayed-reading-order.json').write_text(result.document.model_dump_json())
    finally:
        source.release()


if __name__=='__main__':main()
