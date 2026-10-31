"""Replay retained native OCR through pure enrichment/admission, without model inference."""
from __future__ import annotations

import argparse
import copy
import json
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

from corpus_structure.ingest.pdf import PdfConversion, PdfConverter, PdfRecipe, publication_payload
from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
from corpus_structure.ingest.pdf_enrichment import PdfEnrichmentRequest, compute_enrichment
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot, load_snapshot, native_nodes
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product

HERE=Path(__file__).resolve().parent

class NoInferenceConverter(PdfConverter):
    def formula_stage(self):
        raise AssertionError('retained prose replay must not invoke formula inference')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--admit',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('retain prior replay; select a new output file')
    schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
    results=[]
    for name in ('raster-only','broken-visible','broken-invisible'):
        original=(HERE/'inputs'/f'{name}.pdf').read_bytes()
        native=(HERE/'raw'/f'{name}-native.json').read_bytes()
        recipe=(HERE/'raw'/f'{name}-recipe.json').read_bytes()
        report=json.loads((HERE/'raw'/f'{name}-report.json').read_bytes())
        candidates=tuple(CandidatePage(
            row['page_no'],row['has_words'],row['has_chars'],
            tuple(InlineCandidate.from_wire(item) for item in row['candidates']),
            row['has_vectors'],row['native_text_quality'],tuple(row['ocr_regions']),
        ) for row in report['candidates'])
        conversion=PdfConversion(sha256(original).hexdigest(),recipe,
            NativeSnapshot(native,sha256(native).hexdigest(),json.loads(native)['version']),
            report['status'],(),(),(),None,inline_candidates=candidates)
        document=load_snapshot(conversion.native)
        request=PdfEnrichmentRequest(conversion,original,frozenset(native_nodes(document)),r'[=+]',r'[A-Za-z ]+',.75)
        enriched=compute_enrichment(request,NoInferenceConverter(PdfRecipe.from_bytes(recipe)))
        assert enriched.native.digest==conversion.native.digest
        assert not enriched.outcomes and not enriched.mappings
        assert enriched.candidate_pages==candidates
        assert all(page.usable_words and page.has_vectors for page in candidates)
        record=dict(name=name,enrichment='passed',native_digest=conversion.native.digest,admission='not_run')
        if args.admit:
            payload=publication_payload(conversion,product_key='qualified',schema_digest=sha256(schema).hexdigest())
            prepared=prepare_pdf_product(payload,original,schema,recipe)
            assert prepared.values()['inline_candidate_pages']==report['candidates']
            invalid=copy.deepcopy(payload)
            invalid['inline_candidate_pages'][0]['ocr_regions'][0]['lines'][0]['words'][0]['left']+=1
            try:
                prepare_pdf_product(invalid,original,schema,recipe)
            except ValueError:
                record['transform_negative']='passed'
            else:
                raise AssertionError('corrupt OCR raster-to-PDF mapping was admitted')
            record.update(admission='passed',product_digest=prepared.digest)
        results.append(record)
    output=dict(outcome='passed',scope='retained three one-page inputs; no inference or database publication',results=results)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))

if __name__=='__main__':
    main()
