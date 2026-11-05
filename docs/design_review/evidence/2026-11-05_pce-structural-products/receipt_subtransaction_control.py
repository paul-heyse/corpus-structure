"""Receipt inserted under savepoint must not deliver labels before top-level commit."""
import json
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.evaluate.review_assessments import record_review_exposure, iter_assessment_review_rows

with open_runtime_engine(Settings(), purpose='evaluate') as e, e.connect() as c:
    tx = c.begin()
    try:
        project = c.scalar(text('SELECT project_id FROM eval.reference_set WHERE id=18'))
        with c.begin_nested():
            receipt = record_review_exposure(c, project_id=project, set_id=18,
                purpose='native precommit privacy control', recipient_class='local evaluator',
                authorization_basis='Operator-approved already-exposed feature_fit cohort18 only')
        try:
            rows = list(iter_assessment_review_rows(c, project_id=project, set_id=18, exposure_receipt_id=receipt))
        except DBAPIError:
            report = {'outcome': 'passed', 'precommit_label_delivery': False}
        else:
            report = {'outcome': 'failed', 'precommit_label_delivery': True,
                      'returned_row_count': len(rows)}
        print(json.dumps(report))
        Path(__file__).with_name('raw').joinpath('receipt-savepoint-146.json').write_text(json.dumps(report)+'\n')
    finally:
        tx.rollback()
