"""Forward realization of typed positioned grammar nodes on retained text products."""
from pglast import ast,parse_sql
from pglast.stream import RawStream
from sqlalchemy.schema import AddConstraint,CheckConstraint
from sqlalchemy.dialects.postgresql import dialect
from .metadata import metadata
from .native_products import NativeProduct,closure_products
from .source_view_native import native_admission_sql
from .migrations import ALEMBIC_DIR


def native_syntax_products(model=None):
    relations=('kb.parsing_node','kb.parsing_layer_node')
    sql='SET LOCAL ROLE corpus_sem_publisher;\n'
    for name in relations:
        for column in ('syntax_kind','upstream_role','grammar_revision'):
            sql+='ALTER TABLE '+name+' ADD COLUMN '+column+' text;\n'
        sql+="DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='"+name+"'::regclass AND contype='c' LOOP EXECUTE format('ALTER TABLE "+name+" DROP CONSTRAINT %I',n); END LOOP; END $checks$;\n"
        for constraint in metadata.tables[name].constraints:
            if isinstance(constraint,CheckConstraint):sql+=str(AddConstraint(constraint,isolate_from_table=False).compile(dialect=dialect())).strip()+';\n'
    physical,kernels,_=closure_products(model)
    for raw in parse_sql(kernels.content.decode()):
        stmt=raw.stmt
        if stmt is None or isinstance(stmt,ast.CreateTrigStmt):continue
        if isinstance(stmt,ast.InsertStmt) and stmt.relation is not None and stmt.relation.schemaname=='sem' and stmt.relation.relname=='physical_contract':continue
        sql+=RawStream()(stmt).replace('__migration_owner__','__MIGRATION_OWNER__')+';\n'
    sql+='\nDO $reference$'+physical.content.decode().split('DO $reference$',1)[1]
    previous=ALEMBIC_DIR.joinpath('versions/semantic_0052_admission.sql').read_text()
    admission=native_admission_sql(sql,model,extra_relations=relations,base_admission=previous)
    return NativeProduct('semantic_0053_positioned_syntax.sql',sql.encode()),NativeProduct('semantic_0053_admission.sql',admission.encode())
