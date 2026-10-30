"""Actual release-scoped relational execution contracts and native consumers."""

import json

from sqlalchemy import text


def test_execution_table_posture(semantic_db_engine, admitter):
    with admitter.connect() as conn:
        expected = next(t for t in conn.scalar(text('SELECT data.execution_contract_descriptor()'))['tables'] if t['relation']=='sem.execution_edge')
        actual = conn.execute(text("""SELECT pg_get_userbyid(c.relowner) owner,c.relrowsecurity,c.relforcerowsecurity,
          (SELECT jsonb_agg(jsonb_build_object('name',a.attname,'type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,'identity',a.attidentity::text,'generated',a.attgenerated::text,'default',pg_get_expr(d.adbin,d.adrelid)) ORDER BY a.attnum) FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped) columns,
          (SELECT jsonb_agg(jsonb_build_object('name',k.conname,'columns',ARRAY(SELECT a.attname::text FROM unnest(k.conkey) WITH ORDINALITY cols(num,position) JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=cols.num ORDER BY cols.position),'target',ns.nspname||'.'||remote.relname,'remote_columns',ARRAY(SELECT a.attname::text FROM unnest(k.confkey) WITH ORDINALITY cols(num,position) JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=cols.num ORDER BY cols.position),'on_update',k.confupdtype::text,'on_delete',k.confdeltype::text,'match',k.confmatchtype::text,'deferrable',k.condeferrable,'deferred',k.condeferred,'validated',k.convalidated) ORDER BY k.conname) FROM pg_constraint k JOIN pg_class remote ON remote.oid=k.confrelid JOIN pg_namespace ns ON ns.oid=remote.relnamespace WHERE k.conrelid=c.oid AND k.contype='f') foreign_keys,
          ARRAY(SELECT name||':'||has_table_privilege(name,c.oid,'SELECT')::text||':'||has_table_privilege(name,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')::text||':'||has_any_column_privilege(name,c.oid,'INSERT,UPDATE,REFERENCES')::text FROM unnest(ARRAY['corpus_sem_writer','corpus_sem_reader','corpus_sem_evaluator','corpus_sem_admitter']) name) acls
          FROM pg_class c WHERE c.oid='sem.execution_edge'::regclass""")).mappings().one()
        assert expected['columns']==actual['columns'], repr((expected,dict(actual)))
        assert expected['foreign_keys']==actual['foreign_keys'], repr((expected,dict(actual)))
        assert expected['owner']==actual['owner'], repr((expected,dict(actual)))
        assert all(v.endswith(':true:false:false') for v in actual['acls']),repr((expected,dict(actual)))
