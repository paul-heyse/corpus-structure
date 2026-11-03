"""Actual application controller → isolated parser → managed service → retained request receipts."""

import json
import runpy
from pathlib import Path

from corpus_structure.ingest.pdf_recognition import (
    NemotronRecipe, PreparedRecognitionSource, RecognitionWorker,
)

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def main():
    builder = runpy.run_path(str(REPO / 'fixtures/toy/build_pdf.py'))
    source = ROOT / 'runtime/controlled.pdf'
    builder['write_pdf'](source, (('Example 1', ('A = 2 + 3.',)),))
    prepared = PreparedRecognitionSource.prepare(source.read_bytes())
    recipe = NemotronRecipe(
        '81dd7609c589f3694ce75520c25af5010953231358de6aec4d03e8c6aac787e9',
        '34f566e728995769d971fc2707596bfb92c83298d357bc6ec29a7a1d3d12a74a',
        identity_assurance='trusted_managed_service', max_tokens=2048,
        detection_max_tokens=1024, max_regions=8,
    )
    runtime = Path('/home/paul/corpus-structure/services/nemotron-parse/.venv/bin/python')
    worker = RecognitionWorker(python=runtime, script=REPO/'services/nemotron-parse/worker.py',
                               endpoint='http://127.0.0.1:8035/v1', receipts=ROOT/'runtime/application')
    try:
        (page,) = tuple(worker.recognize_pages(prepared, recipe, (1,), reuse=False))
        requests = list(page.requests())
        result = dict(outcome=page.result['outcome'], page=page.page_no,
                      requests=[{'outcome': row['outcome'], 'assurance': row['identity_assurance'],
                                 'generation': row['service_generation'],
                                 'response_generation': row.get('response_generation'),
                                 'requested_model': row['requested_model'],
                                 'reported_model': row.get('response_model')}
                                for row, raw, artifacts in requests])
        (ROOT/'runtime/application-result.json').write_text(json.dumps(result,indent=2)+'\n')
        assert page.succeeded, page.result
        assert all(row['assurance']=='trusted_managed_service' for row in result['requests'])
        print(json.dumps(result))
    finally:
        assert worker._process is None, "finite page generator did not settle its owned process"


if __name__ == '__main__':
    main()
