"""Bounded reproductions of correction-view contract gaps; no database effects."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter, ValidationError
from corpus_structure.semantic.operation_reporting import validation_failure_report
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_records import NativeSchemaMapping, NativeMappingError

error = next(Draft202012Validator({'type': 'integer'}).iter_errors('s' * 16384))
r = validation_failure_report(error, detail=True, raw_evidence=True, max_errors=1, max_bytes=1024).model_dump(mode='json', exclude_none=True)
result = {'raw_bound': {'report_bytes':len(canonical_bytes(r)), 'message_chars':len(r['observations'][0]['message']), 'nodes':len(r['correction_detail']['nodes']), 'render_complete':r['correction_detail']['render_complete']}}
try:
    TypeAdapter(list[int]).validate_python(['bad'] * 20)
except ValidationError as error:
    r = validation_failure_report(error, detail=True, max_errors=1, max_bytes=1024).model_dump(mode='json', exclude_none=True)
    result['item_bound'] = {'observations':len(r['observations']), 'nodes':len(r['correction_detail']['nodes'])}
m = NativeSchemaMapping(b'{}', {}, Draft202012Validator({}), {})
try:
    m.validate({'items':[float('inf')]}, detail=True)
except NativeMappingError as error:
    r = validation_failure_report(error, detail=True).model_dump(mode='json', exclude_none=True)
    result['finite_location'] = {'original_path':error.path, 'observations':r['observations'], 'correction_detail':r.get('correction_detail')}
print(json.dumps(result, sort_keys=True))
