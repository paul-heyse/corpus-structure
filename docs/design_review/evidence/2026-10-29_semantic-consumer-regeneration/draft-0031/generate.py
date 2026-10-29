from pathlib import Path
from hashlib import sha256
import json,re
from pglast import parse_sql,ast
ROOT=Path('/home/paul/corpus-structure/python/corpus-structure')
VERSIONS=ROOT/'semantic_alembic/versions'
PENDING=Path('/tmp/sp31-pending')
source=(VERSIONS/'semantic_0030_source_frames.sql').read_text()
raw=next(raw for raw in parse_sql(source) if isinstance(raw.stmt,ast.CreateFunctionStmt) and '.'.join(n.sval for n in raw.stmt.funcname)=='data.validate_occurrence_context')
function=source[raw.stmt_location:raw.stmt_location+raw.stmt_len].strip()+';\n'
original="     AND c.name='SourceStatement')) THEN"
replacement="""     AND (c.name='SourceStatement' OR EXISTS(
      SELECT FROM sem.class_hierarchy h JOIN sem.class_definition root
       ON root.release_id=h.release_id AND root.class_id=h.ancestor_id AND root.name='SourceStatement'
      WHERE h.release_id=r AND h.class_id=c.class_id)))) THEN"""
assert function.count(original)==1
function=function.replace(original,replacement)
node=parse_sql(function)[0].stmt
body=next(option.arg[0].sval for option in node.options if option.defname=='as')
previous=(VERSIONS/'semantic_0030_admission.sql').read_text()
node=next(raw.stmt for raw in parse_sql(previous) if isinstance(raw.stmt,ast.CreateFunctionStmt) and '.'.join(n.sval for n in raw.stmt.funcname)=='data.execution_contract_descriptor')
old_body=next(option.arg[0].sval for option in node.options if option.defname=='as')
descriptor=json.loads(re.search(r"SELECT '(.*?)'::jsonb",old_body,re.S)[1].replace("''","'"))
entry=next(f for f in descriptor['functions'] if f['signature']=='data.validate_occurrence_context(text,text)')
entry['body_sha256']=sha256(body.encode()).hexdigest()
descriptor_body="\n SELECT '"+json.dumps(descriptor,sort_keys=True,separators=(',',':')).replace("'","''")+"'::jsonb;\n"
admission=previous[previous.index('CREATE OR REPLACE FUNCTION data.require_execution_release'):]
result='SET LOCAL ROLE corpus_sem_publisher;\n'+function+'REVOKE ALL ON FUNCTION data.validate_occurrence_context(text,text) FROM PUBLIC;\nCREATE OR REPLACE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $descriptor$'+descriptor_body+'$descriptor$;\n'+admission
parse_sql(result)
(PENDING/'semantic_0031_statement_inheritance.sql').write_text(result)
fingerprints=(ROOT/'src/corpus_structure/semantic/execution_admission.py').read_text()
fingerprints=re.sub(r'_DESCRIPTOR_SHA256 = ".*?"','_DESCRIPTOR_SHA256 = "'+sha256(descriptor_body.encode()).hexdigest()+'"',fingerprints)
fingerprints=fingerprints.replace('through semantic_0030.','through semantic_0031.')
(PENDING/'execution_admission.py').write_text(fingerprints)
print('model',descriptor['model_id'],'physical',descriptor['physical_id'],'changed_function',entry['signature'],'new_body',entry['body_sha256'])
