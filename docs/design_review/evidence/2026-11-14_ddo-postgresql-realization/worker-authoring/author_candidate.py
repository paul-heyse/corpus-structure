"""Full source-owned candidate preparation; the owner always rolls its transaction back."""
import json
from corpus_structure.cli.schema import author_native_candidate
from corpus_structure.semantic.migrations import ALEMBIC_DIR, current_revision
from corpus_structure.semantic.migration_chain import registered_base
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

settings = Settings()
with open_runtime_engine(settings, 'ci-ddo-authoring-base', purpose='maintenance') as engine:
    with engine.connect() as connection:
        base = registered_base(ALEMBIC_DIR, current_revision(connection), 'semantic_ddo_context_pdf_v1')
try:
    report, products = author_native_candidate(settings, None, None, expected_predecessor=base.predecessor, native_base=base)
    print(json.dumps({'outcome':'passed','native_operations':report.native_operations,'ordinary_operations':report.ordinary_operations,'products':sorted(products), 'cleanup':'transaction rolled back by author_native_candidate'}))
except Exception as error:
    context = getattr(error, 'authoring_context', None)
    output = {'outcome':'failed','error':type(error).__name__,'message':str(error), 'authoring_context':context}
    cause = error.__cause__
    physical = getattr(cause, 'orig', None)
    if physical is not None and getattr(physical, 'diag', None) is not None:
        output['sqlstate'] = physical.sqlstate
        output['primary'] = physical.diag.message_primary
        output['detail'] = physical.diag.message_detail
    print(json.dumps(output))
    raise
