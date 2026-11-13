"""Synthetic source-position observation must refuse or change reusable identity."""
import json

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import claim_source_item__data_operation__ as metadata
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection

base = (
    'def claim_source_item(index: int) -> str:\n'
    '    return str(claim_source_item.__code__.co_firstlineno)\n'
    'claim_source_item__data_operation__ = ' + repr(metadata) + '\n'
)
rows = []
for prefix in ('', '\n\n'):
    code = prefix + base
    model = compile_data_operations(python_sources=PythonSourceCollection((
        PythonSource('reflection_case', code.encode(), 'reflection_case.py'),
    )))
    namespace = {}
    exec(compile(code, 'reflection_case.py', 'exec'), namespace)
    rows.append({
        'complete': model.implementation_slices[0].complete,
        'unknowns': [u.reason for u in model.implementation_slices[0].unknowns],
        'recipe': next((i.key for i in model.identities
                        if i.owner == metadata['id'] and i.domain == 'recipe'), None),
        'value': namespace['claim_source_item'](1),
    })
print(json.dumps(rows, indent=2))
assert [r['value'] for r in rows] == ['1', '3']
assert all(r['complete'] and r['recipe'] for r in rows)
assert rows[0]['recipe'] == rows[1]['recipe']
