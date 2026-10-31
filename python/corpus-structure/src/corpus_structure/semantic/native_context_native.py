"""Forward custody for independently addressed ancestor frame sources."""
from pathlib import Path
from pglast import ast,parse_sql
from pglast.stream import RawStream
from sqlalchemy.schema import AddConstraint,ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import dialect
from .metadata import metadata
from .native_products import NativeProduct,physical_products,closure_products
from .source_view_native import native_admission_sql
from .migrations import ALEMBIC_DIR


def native_context_products(model=None):
    from .pdf_contracts import trusted_pdf_context
    from .native_shapes import record_shape_guards
    boundary=trusted_pdf_context().boundary
    relation='ops.native_source_frame_source'
    sql='SET LOCAL ROLE corpus_sem_publisher;\n'
    referenced={fk.referred_table.fullname for fk in metadata.tables[relation].foreign_key_constraints}
    for name in sorted(referenced):sql+='GRANT REFERENCES ON '+name+' TO __MIGRATION_OWNER__;\n'
    sql+='SET LOCAL ROLE __MIGRATION_OWNER__;\n'
    for product in physical_products():
        if product.name==relation or product.name.startswith(relation+'/'):sql+=product.content.decode()+'\n'
    sql+='ALTER TABLE '+relation+' OWNER TO corpus_sem_publisher;\nSET LOCAL ROLE corpus_sem_publisher;\n'
    for name in sorted(referenced):sql+='REVOKE REFERENCES ON '+name+' FROM __MIGRATION_OWNER__;\n'
    sql+='''INSERT INTO ops.native_source_frame_source(task_id,unit_ref,source_view_id,product_task_id,product_key,product_digest,projection_digest,recipe_digest,section_pointer,membership,role,context_json)
 SELECT f.task_id,f.unit_ref,f.source_view_id,f.product_task_id,f.product_key,f.product_digest,f.projection_digest,f.recipe_digest,v.section_pointer,v.membership,'primary',f.context_json FROM ops.native_source_frame f JOIN kb.source_view v ON v.id=f.source_view_id;
 CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON ops.native_source_frame_source FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
 GRANT SELECT ON ops.native_source_frame_source TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
 ALTER TABLE ops.native_source_frame ADD COLUMN source_frame jsonb;
 ALTER TABLE ops.native_source_frame_sentence ADD COLUMN source_view_id bigint;
 ALTER TABLE ops.native_source_frame_sentence DISABLE TRIGGER semantic_immutable;
 UPDATE ops.native_source_frame_sentence s SET source_view_id=f.source_view_id FROM ops.native_source_frame f WHERE f.task_id=s.task_id;
 ALTER TABLE ops.native_source_frame_sentence ENABLE TRIGGER semantic_immutable;
 ALTER TABLE ops.native_source_frame_sentence ALTER COLUMN source_view_id SET NOT NULL;
'''
    for constraint in metadata.tables['ops.native_source_frame_sentence'].constraints:
        if isinstance(constraint,ForeignKeyConstraint) and any(e.parent.name=='source_view_id' for e in constraint.elements):sql+=str(AddConstraint(constraint,isolate_from_table=False).compile(dialect=dialect())).strip()+';\n'
    sql+="DO $owner$ DECLARE r text; BEGIN SELECT pg_get_userbyid(relowner) INTO r FROM pg_class WHERE oid='eval.reference_frame'::regclass; EXECUTE format('SET LOCAL ROLE %I',r); END $owner$;\nALTER TABLE eval.reference_frame ADD COLUMN source_frame jsonb;\nSET LOCAL ROLE corpus_sem_publisher;\n"
    source=Path(__file__).with_name('sql')
    sql+=(source/'source_views.sql').read_text().replace('-- {source_view_shape_guard}',record_shape_guards(boundary,'PdfSourceViewPublication','product')).replace('-- {frame_source_shape_guard}',record_shape_guards(boundary,'PdfFrameSource','p_frame')).replace('-- {native_frame_shape_guard}',record_shape_guards(boundary,'PdfNativeProposalFrame','p_frame'))+'\n'
    sql+=(source/'native_references.sql').read_text()+'\n'
    physical,kernels,_=closure_products(model)
    for raw in parse_sql(kernels.content.decode()):
        stmt=raw.stmt
        if stmt is None or isinstance(stmt,ast.CreateTrigStmt):continue
        if isinstance(stmt,ast.InsertStmt) and stmt.relation is not None and stmt.relation.schemaname=='sem' and stmt.relation.relname=='physical_contract':continue
        sql+=RawStream()(stmt).replace('__migration_owner__','__MIGRATION_OWNER__')+';\n'
    sql+='\nDO $reference$'+physical.content.decode().split('DO $reference$',1)[1]
    previous=ALEMBIC_DIR.joinpath('versions/semantic_0051_admission.sql').read_text()
    admission=native_admission_sql(sql,model,extra_relations=[relation,'ops.native_source_frame','ops.native_source_frame_sentence'],base_admission=previous)
    return NativeProduct('semantic_0052_native_context.sql',sql.encode()),NativeProduct('semantic_0052_admission.sql',admission.encode())
