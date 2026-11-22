"""Read-only JSON/native codec probe on an explicitly acquired qualification database."""
from copy import deepcopy
from statistics import median
from time import perf_counter
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'python/corpus-structure/tests'))
import psycopg
from semantic.demand_result_support import demand_result_page
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_wire import wire_contracts

rows=[]
with psycopg.connect('host=/var/run/postgresql port=5434 dbname=corpus_structure_sbx09_bounded_qualification user=paul') as c:
    identity=c.execute("SELECT current_database(),(SELECT oid::bigint FROM pg_database WHERE datname=current_database()),(pg_control_system()).system_identifier::text,current_setting('server_version')").fetchone()
    assert identity[:3] == ('corpus_structure_sbx09_bounded_qualification',136550030,'7701811359771751232'),identity
    c.execute("SET LOCAL statement_timeout='5s'")
    c.execute("SET LOCAL auto_explain.log_parameter_max_length=0")
    c.execute("SET LOCAL log_parameter_max_length=0")
    schema=json_bytes(wire_contracts()['read_demand_result']['output']).decode()
    page=demand_result_page()
    cases=[]
    for depth in (0,10,20,32):
        body=['string','one']
        for _ in range(depth):body=['sequence',[body]]
        cases.append((f'depth-{depth}',body))
    for width in (100,1000,10000):
        cases.append((f'width-{width}',['sequence',[['string','one'] for _ in range(width)]]))
    for label,body in cases:
        raw=deepcopy(page)
        raw['uses'][0]['products'][0]['body']=body
        content=json_bytes(raw).decode()
        expressions={
            'jsonb_cast':("SELECT octet_length(CAST(CAST(%s AS jsonb) AS text))",(content,)),
            'pg_jsonschema':("SELECT public.json_matches_schema(CAST(CAST(%s AS jsonb) AS json),CAST(CAST(%s AS jsonb) AS json))",(schema,content)),
            'native_canonical_json':("SELECT octet_length(data.canonical_json(CAST(%s AS jsonb)))",(content,)),
            'native_json_meaning':("SELECT octet_length(data.ddo_json_meaning(CAST(%s AS jsonb))::text)",(json_bytes(body).decode(),)),
        }
        for name,(sql,params) in expressions.items():
            samples=[]
            for _ in range(3):
                start=perf_counter();result=c.execute(sql,params).fetchone()[0];samples.append(perf_counter()-start)
                if name=='pg_jsonschema':assert result is True
            rows.append({'case':label,'bytes':len(content.encode()),'operation':name,'median_ms':round(median(samples)*1000,3),'samples_ms':[round(t*1000,3) for t in samples]})
        print(label,flush=True)
    c.rollback()
print(json.dumps({'identity':identity,'samples':rows,'scope':'client elapsed on read-only SELECT, three warm-session repetitions, 5s local statement limit'},indent=2))
