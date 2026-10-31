"""Forward deployment of bounded derivations and native consumer custody."""
from pathlib import Path

from pglast import ast,parse_sql
from pglast.stream import RawStream
from sqlalchemy.schema import AddConstraint,CheckConstraint
from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata
from .native_products import NativeProduct,physical_products,closure_products
from .source_view_native import RELATIONS,native_admission_sql

DERIVATION='kb.native_document_derivation'


def native_consumer_products(model=None):
    from .pdf_contracts import trusted_pdf_context,pdf_shape_guard_sql
    from .native_shapes import record_shape_guards
    from .pdf_native import PDF_RELATIONS
    source=Path(__file__).with_name('sql')
    context=trusted_pdf_context()
    sql='SET LOCAL ROLE corpus_sem_publisher;\nGRANT REFERENCES ON kb.native_document_item TO __MIGRATION_OWNER__;\nSET LOCAL ROLE __MIGRATION_OWNER__;\n'
    for product in physical_products():
        if product.name==DERIVATION or product.name.startswith(DERIVATION+'/') or product.name in {str(i.name) for i in metadata.tables[DERIVATION].indexes}:
            sql+=product.content.decode()+'\n'
    sql+='ALTER TABLE '+DERIVATION+' OWNER TO corpus_sem_publisher;\nSET LOCAL ROLE corpus_sem_publisher;\nREVOKE REFERENCES ON kb.native_document_item FROM __MIGRATION_OWNER__;\n'
    sql+='''INSERT INTO kb.native_document_derivation(task_id,product_key,pointer,mapping_index,origin_pointer,source_field,start_offset,end_offset,cell_index,kind)
SELECT p.task_id,p.product_key,m.value->>'pointer',m.n-1,m.value->>'origin_pointer',m.value->>'source_field',(m.value->>'start')::bigint,(m.value->>'end')::bigint,(m.value->>'cell_index')::bigint,m.value->>'kind'
FROM ops.native_document_product p CROSS JOIN LATERAL jsonb_array_elements(COALESCE(convert_from(p.payload,'UTF8')::jsonb->'derivation_mappings','[]')) WITH ORDINALITY m(value,n);
'''
    sql+='CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON '+DERIVATION+' FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\nGRANT SELECT ON '+DERIVATION+' TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;\n'
    sql+="DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='ops.task_dependency'::regclass AND contype='c' LOOP EXECUTE format('ALTER TABLE ops.task_dependency DROP CONSTRAINT %I',n); END LOOP; END $checks$;\n"
    for constraint in metadata.tables['ops.task_dependency'].constraints:
        if isinstance(constraint,CheckConstraint):sql+=str(AddConstraint(constraint,isolate_from_table=False).compile(dialect=dialect())).strip()+';\n'
    sql+=(source/'native_references.sql').read_text()+'\n'
    sql+=(source/'native_documents.sql').read_text().replace('-- {pdf_shape_guard}',pdf_shape_guard_sql()).replace('{native_schema_digest}',context.native_schema_digest)+'\n'
    sql+=(source/'source_views.sql').read_text().replace('-- {source_view_shape_guard}',record_shape_guards(context.boundary,'PdfSourceViewPublication','product'))+'\n'
    sql+=(source/'native_task_completion.sql').read_text().replace('-- {native_input_shape_guard}',record_shape_guards(context.boundary,'PdfNativeObservationInput','native_input'))+'\n'
    physical,kernels,_=closure_products(model)
    for raw in parse_sql(kernels.content.decode()):
        stmt=raw.stmt
        if stmt is None or isinstance(stmt,ast.CreateTrigStmt):continue
        if isinstance(stmt,ast.InsertStmt) and stmt.relation is not None and stmt.relation.schemaname=='sem' and stmt.relation.relname=='physical_contract':continue
        sql+=RawStream()(stmt).replace('__migration_owner__','__MIGRATION_OWNER__')+';\n'
    sql+='\nDO $reference$'+physical.content.decode().split('DO $reference$',1)[1]
    admission=native_admission_sql(sql,model,extra_relations=sorted(RELATIONS|PDF_RELATIONS|{DERIVATION}))
    return NativeProduct('semantic_0049_native_consumers.sql',sql.encode()),NativeProduct('semantic_0049_admission.sql',admission.encode())
