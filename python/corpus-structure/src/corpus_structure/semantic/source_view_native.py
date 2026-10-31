"""Frozen forward realization of native section views and their actual consumers."""
from pathlib import Path

from sqlalchemy.schema import AddConstraint,CheckConstraint,ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata
from .native_products import NativeProduct,physical_products

RELATIONS=frozenset({'kb.source_view','ops.run_source_view','ops.native_source_frame',
                     'ops.native_source_frame_sentence','ops.native_region_artifact','ops.task_dependency'})
ALTERED=('kb.observation','data.evidence_source','eval.reference_unit','eval.reference_frame')


def source_view_products(model=None):
    from .native_products import closure_products,consolidation_products
    from .native_shapes import record_shape_guards
    from .pdf_contracts import trusted_pdf_context,PDF_CONTRACT_DIGEST,pdf_shape_guard_sql

    referenced=sorted({fk.referred_table.fullname for name in RELATIONS for fk in metadata.tables[name].foreign_key_constraints if fk.referred_table.fullname not in RELATIONS})
    sql='SET LOCAL ROLE corpus_sem_publisher;\n'
    for name in referenced:sql+=f'GRANT REFERENCES ON {name} TO __MIGRATION_OWNER__;\n'
    sql+='SET LOCAL ROLE __MIGRATION_OWNER__;\n' 
    for product in physical_products():
        if product.name in RELATIONS or any(product.name.startswith(n+'/') for n in RELATIONS) or any(product.name==str(i.name) for n in RELATIONS for i in metadata.tables[n].indexes):
            sql+=product.content.decode()+'\n'
    for name in sorted(RELATIONS):
        sql+=f'ALTER TABLE {name} OWNER TO corpus_sem_publisher;\n'
    sql+='SET LOCAL ROLE corpus_sem_publisher;\n'
    for name in referenced:sql+=f'REVOKE REFERENCES ON {name} FROM __MIGRATION_OWNER__;\n'
    for name in sorted(RELATIONS):
        sql+=f'CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {name} FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\n'
        sql+=f'GRANT SELECT ON {name} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;\n'
    sql+="ALTER TABLE kb.native_document_item ADD COLUMN native_json jsonb;\n"
    sql+="ALTER TABLE kb.native_document_item DISABLE TRIGGER semantic_immutable;\n"
    sql+="UPDATE kb.native_document_item i SET native_json=p.native_json #> string_to_array(substr(i.pointer,3),'/') FROM ops.native_document_product p WHERE p.task_id=i.task_id AND p.product_key=i.product_key;\n"
    sql+="ALTER TABLE kb.native_document_item ALTER COLUMN native_json SET NOT NULL;\n"
    sql+="ALTER TABLE kb.native_document_item ENABLE TRIGGER semantic_immutable;\n"
    for name in ALTERED:
        relation=metadata.tables[name]
        sql+=f"DO $owner$ DECLARE r text; BEGIN SELECT pg_get_userbyid(relowner) INTO r FROM pg_class WHERE oid='{name}'::regclass; EXECUTE format('GRANT REFERENCES ON kb.source_view TO %I',r); EXECUTE format('SET LOCAL ROLE %I',r); END $owner$;\n"
        for column in relation.columns:
            if column.name in {'source_view_id','native_address','projection_digest'}:
                kind='bigint' if column.name=='source_view_id' else 'text'
                sql+=f'ALTER TABLE {name} ADD COLUMN {column.name} {kind};\n'
        if name!='kb.observation':
            sql+=f'ALTER TABLE {name} ALTER COLUMN rendition_id DROP NOT NULL;\n'
        if name=='eval.reference_frame':
            sql+=f'ALTER TABLE {name} ALTER COLUMN rendition_digest DROP NOT NULL;\n'
        sql+=f"DO $constraints$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='{name}'::regclass AND contype='c' LOOP EXECUTE format('ALTER TABLE {name} DROP CONSTRAINT %I',n); END LOOP; END $constraints$;\n"
        for constraint in relation.constraints:
            if (isinstance(constraint,ForeignKeyConstraint) and any(e.parent.name=='source_view_id' for e in constraint.elements)) or isinstance(constraint,CheckConstraint):
                sql+=str(AddConstraint(constraint,isolate_from_table=False).compile(dialect=dialect())).strip()+';\n'
        sql+='SET LOCAL ROLE corpus_sem_publisher;\n'
    source=Path(__file__).with_name('sql')
    views=(source/'source_views.sql').read_text().replace('-- {source_view_shape_guard}',record_shape_guards(trusted_pdf_context().boundary,'PdfSourceViewPublication','product'))
    sql+=views+'\n'
    # Redeploy changed consumers from reviewed templates; 0047 stays immutable.
    sql+=(source/'native_documents.sql').read_text().replace('-- {pdf_shape_guard}',pdf_shape_guard_sql()).replace('{pdf_contract_digest}',PDF_CONTRACT_DIGEST).replace('{native_schema_digest}',trusted_pdf_context().native_schema_digest)+'\n'

    sql+=(source/'native_task_completion.sql').read_text()+'\n'
    from pglast import parse_sql,ast
    from pglast.stream import RawStream
    physical,kernels,_=closure_products(model)
    # Existing triggers keep their ownership and point to the replaced reviewed functions.
    sql+='\n'.join(RawStream()(statement.stmt).replace('__migration_owner__','__MIGRATION_OWNER__')+';' for statement in parse_sql(kernels.content.decode()) if statement.stmt is not None and not isinstance(statement.stmt,ast.CreateTrigStmt) and not (isinstance(statement.stmt,ast.InsertStmt) and statement.stmt.relation is not None and statement.stmt.relation.schemaname=='sem' and statement.stmt.relation.relname=='physical_contract'))+'\n'

    sql+='\nDO $reference$'+physical.content.decode().split('DO $reference$',1)[1]
    admission=native_admission_sql(sql,model)
    return (NativeProduct('semantic_0048_source_views.sql',sql.encode()),
            NativeProduct('semantic_0048_admission.sql',admission.encode()))


def native_admission_sql(sql,model=None,*,extra_relations=(),base_admission=None):
    from .native_products import consolidation_products
    from pglast import parse_sql,ast
    from pglast.stream import RawStream
    import json
    from hashlib import sha256
    from .native_products import function_bodies
    from .identity import canonical_bytes
    admission=consolidation_products(model)[-1].content.decode() if base_admission is None else base_admission
    descriptor_body=function_bodies(admission)['data.execution_contract_descriptor']
    statement=parse_sql(descriptor_body)[0].stmt
    if not isinstance(statement,ast.SelectStmt) or not statement.targetList:raise ValueError('descriptor must be literal SELECT')
    cast=statement.targetList[0].val
    if not isinstance(cast,ast.TypeCast) or not isinstance(cast.arg,ast.A_Const) or not isinstance(cast.arg.val,ast.String):raise ValueError('descriptor must be JSONB string')
    literal=cast.arg.val.sval
    if literal is None:raise ValueError("descriptor string is absent")
    descriptor=json.loads(literal)
    if base_admission is not None:
        # Retain the frozen native inventory, while refreshing model-owned deployment
        # identity and CHECK receipt inputs for the forward physical model.
        current_body=function_bodies(consolidation_products(model)[-1].content.decode())['data.execution_contract_descriptor']
        current_stmt=parse_sql(current_body)[0].stmt
        if not isinstance(current_stmt,ast.SelectStmt) or not current_stmt.targetList:raise ValueError('current descriptor must be literal SELECT')
        current_cast=current_stmt.targetList[0].val
        if not isinstance(current_cast,ast.TypeCast) or not isinstance(current_cast.arg,ast.A_Const) or not isinstance(current_cast.arg.val,ast.String):raise ValueError('current descriptor must be JSONB string')
        current_literal=current_cast.arg.val.sval
        if current_literal is None:raise ValueError("current descriptor string is absent")
        current=json.loads(current_literal)
        descriptor.update({key:value for key,value in current.items() if key not in {'functions','tables','triggers'}})
    from copy import copy
    functions={item['signature']:item for item in descriptor['functions']}
    for raw in parse_sql(sql.replace('__MIGRATION_OWNER__','corpus_migration_owner')):
        stmt=raw.stmt
        if isinstance(stmt,ast.CreateFunctionStmt):
            signature='.'.join(part.sval for part in stmt.funcname or ())+'('+','.join(RawStream()(parameter.argType) for parameter in stmt.parameters or ())+')'
            options={option.defname:option.arg for option in stmt.options or ()}
            previous=functions.get(signature,{})
            if stmt.returnType is None:raise ValueError('native function return type missing')
            result_type=copy(stmt.returnType);result_type.setof=False
            functions[signature]=dict(signature=signature,body_sha256=sha256(options['as'][0].sval.encode()).hexdigest(),language=options['language'].sval,
                security=bool(options.get('security') and options['security'].boolval),strict=bool(options.get('strict') and options['strict'].boolval),
                volatility={'immutable':'i','stable':'s','volatile':'v'}.get(options.get('volatility').sval if options.get('volatility') else 'volatile','v'),
                parallel='u',leakproof=False,setof=bool(stmt.returnType.setof),result=RawStream()(result_type),config=['search_path=pg_catalog, pg_temp'],
                owner=previous.get('owner','corpus_sem_publisher'),execute_roles=list(previous.get('execute_roles',[])))
        elif isinstance(stmt,ast.GrantStmt) and stmt.objtype is not None and stmt.objtype.name=='OBJECT_FUNCTION':
            for obj in stmt.objects or ():
                signature='.'.join(part.sval for part in obj.objname)+'('+','.join(RawStream()(arg) for arg in obj.objargs or ())+')'
                if signature not in functions:continue
                roles=set(functions[signature]['execute_roles'])
                for grantee in stmt.grantees or ():
                    if grantee.rolename:
                        if stmt.is_grant:roles.add(grantee.rolename)
                        else:roles.discard(grantee.rolename)
                functions[signature]['execute_roles']=sorted(roles)
    descriptor['functions']=sorted(functions.values(),key=lambda item:item['signature'])
    tables={item['relation']:item for item in descriptor['tables']}
    for name in extra_relations:
        relation=metadata.tables[name]
        columns=[]
        for column in relation.columns:
            kind=column.type.compile(dialect=dialect()).lower()
            if kind=='float':kind='double precision'
            columns.append(dict(name=column.name,type=kind,not_null=not column.nullable,default=None,
                identity=('a' if column.identity.always else 'd') if column.identity is not None else '',generated=''))
        tables[name]=dict(relation=name,owner='corpus_sem_publisher',columns=columns,primary_key=[c.name for c in relation.primary_key.columns],
            foreign_keys=[dict(name=dialect().identifier_preparer.format_constraint(c),columns=[v.name for v in c.columns],
                target=c.elements[0].target_fullname.rsplit('.',1)[0],remote_columns=[e.target_fullname.rsplit('.',1)[1] for e in c.elements],
                on_delete='a',on_update='a',match='s',deferrable=False,deferred=False,validated=True)
                for c in sorted(relation.foreign_key_constraints,key=lambda c:str(dialect().identifier_preparer.format_constraint(c)))])
        descriptor['triggers']=[t for t in descriptor['triggers'] if not(t['relation']==name and t['name']=='semantic_immutable')]
        descriptor['triggers'].append(dict(relation=name,name='semantic_immutable',function='sem.refuse_immutable_mutation()',type=58,columns=[],when=None,args='',deferrable=False,deferred=False))
    descriptor['tables']=sorted(tables.values(),key=lambda item:item['relation'])
    encoded=canonical_bytes(descriptor).decode().replace("'","''")
    _,separator,required=admission.partition('$descriptor$;')
    if not separator:raise ValueError('missing native descriptor boundary')
    admission="SET LOCAL ROLE corpus_sem_publisher;\nCREATE OR REPLACE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $descriptor$\n SELECT '"+encoded+"'::jsonb\n$descriptor$;"+required
    return admission
