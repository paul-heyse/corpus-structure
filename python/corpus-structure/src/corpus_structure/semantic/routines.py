"""Reviewed PostgreSQL gap companion: protected staging, semantic checks and publication.

Fixed relation and column names come from the immutable transport contract. Domain
identifiers are data, never SQL identifiers. Deploy this with the bootstrap migration.
"""
from __future__ import annotations

from dataclasses import fields

from sqlalchemy import Connection

from .publication import STAGE_TYPES


_CANONICAL = r'''
CREATE OR REPLACE FUNCTION data.canonical_json(p jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog AS $fn$
 SELECT CASE jsonb_typeof(p)
 WHEN 'array' THEN '[' || COALESCE((SELECT string_agg(data.canonical_json(value), ',' ORDER BY ord) FROM jsonb_array_elements(p) WITH ORDINALITY x(value,ord)), '') || ']'
 WHEN 'object' THEN '{' || COALESCE((SELECT string_agg(to_json(key)::text || ':' || data.canonical_json(value), ',' ORDER BY key COLLATE "C") FROM jsonb_each(p)), '') || '}'
 ELSE p::text END
$fn$;
CREATE OR REPLACE FUNCTION data.compare_decimal(a text,b text) RETURNS integer
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog AS $fn$
DECLARE ai text; bi text; af text; bf text; sign integer:=1; result integer;
BEGIN
 IF a::text LIKE '-%' AND b::text NOT LIKE '-%' THEN RETURN -1; END IF;
 IF b::text LIKE '-%' AND a::text NOT LIKE '-%' THEN RETURN 1; END IF;
 IF a LIKE '-%' THEN sign:=-1; END IF;
 ai:=split_part(ltrim(a,'-'),'.',1); bi:=split_part(ltrim(b,'-'),'.',1);
 af:=split_part(a,'.',2); bf:=split_part(b,'.',2);
 IF length(ai)<>length(bi) THEN result:=CASE WHEN length(ai)<length(bi) THEN -1 ELSE 1 END;
 ELSIF ai COLLATE "C"<>bi COLLATE "C" THEN result:=CASE WHEN ai COLLATE "C"<bi COLLATE "C" THEN -1 ELSE 1 END;
 ELSE af:=rpad(af,greatest(length(af),length(bf)),'0'); bf:=rpad(bf,length(af),'0');
 result:=CASE WHEN af COLLATE "C"=bf COLLATE "C" THEN 0 WHEN af COLLATE "C"<bf COLLATE "C" THEN -1 ELSE 1 END;
 END IF;
 RETURN result*sign;
END $fn$;
CREATE OR REPLACE FUNCTION data.value_meaning(r text,z text,v text,path text[] DEFAULT '{}',qual boolean DEFAULT false) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $fn$
DECLARE x data.typed_value%ROWTYPE; result jsonb; child jsonb;
BEGIN
 IF v=ANY(path) THEN RAISE EXCEPTION 'cyclic typed value' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF x.kind='null' THEN RETURN jsonb_build_array('null');
 ELSIF x.kind IN ('string','date','datetime','float') THEN RETURN jsonb_build_array(x.kind,x.text_value);
 ELSIF x.kind='entity' THEN RETURN jsonb_build_array('string',x.entity_id);
 ELSIF x.kind='integer' THEN RETURN jsonb_build_array('integer',COALESCE(x.text_value,x.integer_value::text));
 ELSIF x.kind IN ('decimal','number') THEN RETURN jsonb_build_array('decimal',x.decimal_lexical);
 ELSIF x.kind='boolean' THEN RETURN jsonb_build_array('boolean',x.boolean_value);
 ELSIF x.kind='sequence' THEN
 SELECT COALESCE(jsonb_agg(data.value_meaning(r,z,child_value_id,path||v) ORDER BY position),'[]'::jsonb) INTO result FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=v;
 RETURN jsonb_build_array('sequence',result);
 ELSIF x.kind IN ('mapping','record','interval','expression','missing') THEN
 SELECT COALESCE(jsonb_agg(jsonb_build_array(vr.role,
 CASE WHEN qual AND pa.constraints->>'case_policy'='casefold' AND cv.kind='string'
 THEN jsonb_build_array('string',casefold(cv.text_value COLLATE pg_catalog.pg_unicode_fast))
 ELSE data.value_meaning(r,z,vr.child_value_id,path||v) END) ORDER BY vr.role COLLATE "C"),'[]'::jsonb)
 INTO result FROM data.value_role vr
 JOIN data.typed_value cv ON (cv.release_id,cv.realization_id,cv.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
 LEFT JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND pa.constraints->>'name'=vr.role
 WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=v
 AND (NOT qual OR COALESCE(pa.constraints->>'key_role','meaning') <> 'provenance');
 RETURN jsonb_build_array('mapping',result);
 END IF;
 RAISE EXCEPTION 'unsupported typed value kind %',x.kind USING ERRCODE='23514';
END $fn$;
CREATE OR REPLACE FUNCTION data.value_matches(r text,z text,v text,rng text,inlined boolean) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $fn$
DECLARE x data.typed_value%ROWTYPE;
BEGIN
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF rng IN ('string','uri','uriorcurie') THEN RETURN x.kind='string';
 ELSIF rng='integer' THEN RETURN x.kind='integer';
 ELSIF rng='decimal' THEN RETURN x.kind IN ('decimal','number');
 ELSIF rng='boolean' THEN RETURN x.kind='boolean';
 ELSIF rng IN ('float','double') THEN RETURN x.kind='float';
 ELSIF rng IN ('date','datetime') THEN RETURN x.kind=rng;
 ELSIF EXISTS(SELECT FROM sem.vocabulary_member WHERE release_id=r AND vocabulary_id=rng) THEN
 RETURN x.kind='string' AND EXISTS(SELECT FROM sem.vocabulary_member WHERE release_id=r AND vocabulary_id=rng AND value=x.text_value);
 ELSIF EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name=rng) THEN
 IF inlined THEN RETURN x.datatype IS NOT NULL AND (x.datatype=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng) OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=x.datatype AND ancestor_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng))); END IF;
 RETURN x.kind='entity' AND EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=x.entity_id AND (m.class_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng) OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=m.class_id AND ancestor_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng))));
 END IF;
 RETURN false;
END $fn$;
'''

_VALIDATOR = r'''
CREATE OR REPLACE FUNCTION data.validate_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $fn$
DECLARE a record; x record; n bigint; primitive text; lexical text; value_count bigint;
BEGIN
 IF EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND (m.establishment='' OR NOT EXISTS(SELECT FROM data.membership_support ms WHERE (ms.release_id,ms.realization_id,ms.entity_id,ms.class_id)=(m.release_id,m.realization_id,m.entity_id,m.class_id)))) THEN RAISE EXCEPTION 'membership requires establishment and support' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.derivation d LEFT JOIN data.derivation_premise dp ON (dp.release_id,dp.realization_id,dp.derivation_id)=(d.release_id,d.realization_id,d.derivation_id) WHERE d.release_id=r AND d.realization_id=z GROUP BY d.derivation_id HAVING count(dp.position)=0 OR min(dp.position)<>0 OR max(dp.position)<>count(dp.position)-1) THEN RAISE EXCEPTION 'derivation requires ordered premises' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND c.name='Qualification' WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.qualification_value_id)) THEN RAISE EXCEPTION 'fact requires typed qualification' USING ERRCODE='23514'; END IF;
 -- Every value is interpreted, including disconnected nested nodes. No caller digest is trusted.
 FOR x IN SELECT * FROM data.typed_value WHERE release_id=r AND realization_id=z LOOP
 PERFORM data.value_meaning(r,z,x.value_id);
 IF x.opaque_payload IS NOT NULL OR x.language IS NOT NULL THEN RAISE EXCEPTION 'unsupported opaque/language value' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('string','date','datetime','float') AND x.text_value IS NULL THEN RAISE EXCEPTION 'missing scalar text' USING ERRCODE='23514'; END IF;
 IF x.kind='integer' THEN
 lexical:=COALESCE(x.text_value,x.integer_value::text);
 IF lexical IS NULL OR lexical !~ '^(0|-[1-9][0-9]*|[1-9][0-9]*)$' OR (x.integer_value IS NOT NULL AND lexical<>x.integer_value::text) THEN RAISE EXCEPTION 'invalid exact integer' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind IN ('decimal','number') THEN
 lexical:=x.decimal_lexical;
 IF lexical IS NULL OR lexical !~ '^(0|-?[1-9][0-9]*|-?(0|[1-9][0-9]*)\.[0-9]*[1-9])$' OR (x.numeric_value IS NOT NULL AND lexical::numeric<>x.numeric_value) THEN RAISE EXCEPTION 'invalid exact decimal' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind='boolean' AND x.boolean_value IS NULL THEN RAISE EXCEPTION 'missing boolean' USING ERRCODE='23514'; END IF;
 IF x.kind='float' AND x.text_value !~ '^-?0x(0\.0p\+0|[01]\.[0-9a-f]{13}p[+-][0-9]+)$' THEN RAISE EXCEPTION 'invalid finite float hex' USING ERRCODE='23514'; END IF;
 IF x.kind='date' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR to_char(x.text_value::date,'YYYY-MM-DD')<>x.text_value) THEN RAISE EXCEPTION 'invalid canonical date' USING ERRCODE='23514'; END IF;
 IF x.kind='datetime' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{6})?\+00:00$' OR extract(year FROM x.text_value::timestamptz) NOT BETWEEN 1 AND 9999) THEN RAISE EXCEPTION 'invalid canonical UTC datetime' USING ERRCODE='23514'; END IF;
 IF x.kind NOT IN ('sequence','mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id) THEN RAISE EXCEPTION 'scalar has child roles' USING ERRCODE='23514'; END IF;
 IF x.kind='sequence' AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY parent_value_id HAVING min(position)<>0 OR max(position)<>count(*)-1 OR count(DISTINCT position)<>count(*) OR bool_or(role<>'item')) THEN RAISE EXCEPTION 'invalid ordered sequence' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY role HAVING count(*)<>1 OR min(position)<>0) THEN RAISE EXCEPTION 'duplicate mapping role' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('record','interval','expression','missing') OR (x.kind='mapping' AND x.datatype IS NOT NULL) THEN
 IF x.datatype IS NULL OR NOT EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=x.datatype) THEN RAISE EXCEPTION 'undeclared record class' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.value_role vr WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=x.value_id AND NOT EXISTS(SELECT FROM sem.property_applicability pa WHERE pa.release_id=r AND pa.class_id=x.datatype AND pa.constraints->>'name'=vr.role)) THEN RAISE EXCEPTION 'undeclared record property' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT * FROM sem.property_applicability WHERE release_id=r AND class_id=x.datatype LOOP
 SELECT count(*) INTO n FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name';
 IF n=0 AND (a.required OR COALESCE(a.minimum_cardinality,0)>0) THEN RAISE EXCEPTION 'missing required record property %',a.property_id USING ERRCODE='23514'; END IF;
 FOR primitive IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name' LOOP
 IF a.multivalued THEN
 IF NOT EXISTS(SELECT FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=primitive AND kind='sequence') THEN RAISE EXCEPTION 'multivalue requires sequence' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO value_count FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive;
 IF value_count<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR (a.maximum_cardinality IS NOT NULL AND value_count>a.maximum_cardinality) THEN RAISE EXCEPTION 'record cardinality' USING ERRCODE='23514'; END IF;
 FOR lexical IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive LOOP
 PERFORM data.validate_property(r,z,lexical,a.range_name,a.constraints);
 END LOOP;
 ELSE PERFORM data.validate_property(r,z,primitive,a.range_name,a.constraints);
 END IF;
 END LOOP;
 END LOOP;
 END IF;
 END LOOP;
 -- Range/applicability reads include the complete admitted state plus this candidate.
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id)) THEN RAISE EXCEPTION 'fact property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT f.object_value_id,pa.range_name,pa.constraints FROM data.fact f JOIN data.membership m ON (m.release_id,m.realization_id,m.entity_id)=(f.release_id,f.realization_id,f.subject_id) JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=m.class_id AND pa.property_id=f.property_id WHERE f.release_id=r AND f.realization_id=z LOOP
 PERFORM data.validate_property(r,z,a.object_value_id,a.range_name,a.constraints);
 END LOOP;
 -- Cardinality counts semantic values, never evidence occurrences.
 FOR a IN SELECT m.entity_id,pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z LOOP
 SELECT count(DISTINCT data.canonical_json(data.value_meaning(r,z,f.object_value_id))) INTO n FROM data.fact f
 WHERE f.release_id=r AND f.realization_id=z AND f.subject_id=a.entity_id AND f.property_id=a.property_id
 AND (a.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)));
 IF n<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR n>COALESCE(a.maximum_cardinality,CASE WHEN a.multivalued THEN 9223372036854775807 ELSE 1 END) THEN RAISE EXCEPTION 'property cardinality %/%',a.entity_id,a.property_id USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Identity groups use each declared member, with admitted case policy and complete scope.
 IF EXISTS(
 WITH key_parts AS (
 SELECT m.entity_id,m.class_id,i.group_id,i.position,
 count(DISTINCT f.fact_id) AS count_values,
 min(data.canonical_json(CASE WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS part
 FROM data.membership m JOIN sem.identity_slot i ON i.release_id=r AND i.class_id=m.class_id
 JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=i.class_id AND pa.property_id=i.property_id
 LEFT JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.subject_id=m.entity_id AND f.property_id=i.property_id
 LEFT JOIN data.typed_value tv ON (tv.release_id,tv.realization_id,tv.value_id)=(f.release_id,f.realization_id,f.object_value_id)
 WHERE m.release_id=r AND m.realization_id=z GROUP BY m.entity_id,m.class_id,i.group_id,i.position),
 keys AS(SELECT entity_id,class_id,group_id,string_agg(part,',' ORDER BY position) AS value,bool_and(count_values=1) AS complete FROM key_parts GROUP BY entity_id,class_id,group_id)
 SELECT FROM keys GROUP BY class_id,group_id,value HAVING count(*)>1 OR NOT bool_and(complete)
 ) THEN RAISE EXCEPTION 'missing, multivalued or nonunique entity identity' USING ERRCODE='23514'; END IF;
END $fn$;
CREATE OR REPLACE FUNCTION data.validate_property(r text,z text,v text,rng text,c jsonb) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $fn$
DECLARE x data.typed_value%ROWTYPE;
BEGIN
 IF NOT data.value_matches(r,z,v,rng,COALESCE((c->>'inlined')::boolean,false)) THEN RAISE EXCEPTION 'value violates declared range %',rng USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF c->>'equals_string' IS NOT NULL AND (x.kind<>'string' OR x.text_value<>c->>'equals_string') THEN RAISE EXCEPTION 'value violates equals_string' USING ERRCODE='23514'; END IF;
 IF c->>'minimum' IS NOT NULL OR c->>'maximum' IS NOT NULL THEN
 IF x.kind NOT IN ('integer','decimal','number') THEN RAISE EXCEPTION 'unsupported numeric constraint kind' USING ERRCODE='23514'; END IF;
 IF (c->>'minimum' IS NOT NULL AND data.compare_decimal(COALESCE(x.decimal_lexical,x.text_value,x.integer_value::text),c->>'minimum')<0) OR (c->>'maximum' IS NOT NULL AND data.compare_decimal(COALESCE(x.decimal_lexical,x.text_value,x.integer_value::text),c->>'maximum')>0) THEN RAISE EXCEPTION 'numeric bound' USING ERRCODE='23514'; END IF;
 END IF;
END $fn$;
'''


def _transport_sql(writer: str) -> tuple[str, str, str, str]:
    create, verify, content, insert = [], [], [], []
    for name, (row_type, types) in STAGE_TYPES.items():
        columns = [f.name for f in fields(row_type)]
        definition = ",".join(f'"{column}" {typ}' for column, typ in zip(columns, types, strict=True))
        names = ",".join(f'"{column}"' for column in columns)
        create.append(f"IF to_regclass('pg_temp.sp_{name}') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_{name}({definition}) ON COMMIT DROP; GRANT INSERT ({names}) ON pg_temp.sp_{name} TO {writer};")
        signatures = ",".join("'"+c+":"+t+"'" for c,t in zip(columns,types,strict=True))
        verify.append(f"IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_{name}' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY[{signatures}]) THEN RAISE EXCEPTION 'untrusted staging relation sp_{name}'; END IF;")
        expressions = [f'"{c}"::text' if name == "typed_value" and c in {"integer_value","numeric_value"} else f'"{c}"' for c in columns]
        row = "jsonb_build_array("+",".join(expressions)+")"
        content.append(f"'{name}',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE \"C\") FROM (SELECT {row} j FROM pg_temp.sp_{name}) q),'[]'::jsonb)")
        target_columns = 'release_id,realization_id,'+names
        values = 'r,z,'+names
        if name == "occurrence":
            target_columns += ',batch_id'
            values += ',b'
        # Existing payload IDs cannot silently bind different values. Compare full row data.
        insert.append(f"INSERT INTO data.{name}({target_columns}) SELECT {values} FROM pg_temp.sp_{name} ON CONFLICT DO NOTHING; IF EXISTS(SELECT {names} FROM pg_temp.sp_{name} EXCEPT SELECT {names} FROM data.{name} WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing {name}' USING ERRCODE='23505'; END IF;")
    return "\n".join(create), "\n".join(verify), ",\n".join(content), "\n".join(insert)


def deploy_routines(connection: Connection, *, publisher_role: str = "corpus_sem_publisher", writer_role: str = "corpus_sem_writer", reader_role: str = "corpus_sem_reader") -> None:
    """Deploy bodies, owners and revokes in the caller's single migration transaction."""
    connection = connection.execution_options(no_parameters=True)
    quote = connection.dialect.identifier_preparer.quote
    publisher, writer, reader = map(quote, (publisher_role, writer_role, reader_role))
    database = quote(connection.exec_driver_sql("SELECT current_database()").scalar_one())
    for statement in (
        f"REVOKE TEMP ON DATABASE {database} FROM PUBLIC",
        f"GRANT TEMP ON DATABASE {database} TO {publisher}",
        f"GRANT USAGE,CREATE ON SCHEMA data TO {publisher}",
        f"GRANT USAGE ON SCHEMA sem TO {publisher}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA sem TO {publisher}",
        f"GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA data TO {publisher}",
        f"REVOKE ALL ON ALL TABLES IN SCHEMA data FROM {writer},{reader},PUBLIC",
        f"GRANT USAGE ON SCHEMA data,sem TO {writer},{reader}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA data,sem TO {reader}",
        f"GRANT SELECT ON data.batch TO {writer}",
    ):
        connection.exec_driver_sql(statement)
    connection.exec_driver_sql(_CANONICAL)
    connection.exec_driver_sql(_VALIDATOR)
    create, verify, content, insert = _transport_sql(writer)
    connection.exec_driver_sql(f'''
CREATE OR REPLACE FUNCTION data.begin_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 {create}
END $fn$;
CREATE OR REPLACE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE actual bytea; old data.batch%ROWTYPE; rev bigint; f record; expected text;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 {verify}
 actual:=convert_to(data.canonical_json(jsonb_build_array(r,z,jsonb_build_object({content}))),'UTF8');
 IF actual<>p_content THEN RAISE EXCEPTION 'batch bytes differ from staged content' USING ERRCODE='23514'; END IF;
 SELECT * INTO old FROM data.batch WHERE release_id=r AND realization_id=z AND batch_id=b;
 IF FOUND THEN
 IF old.content<>actual THEN RAISE EXCEPTION 'batch identity content conflict' USING ERRCODE='23505'; END IF;
 RETURN old.data_revision;
 END IF;
 IF NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND state='active') THEN RAISE EXCEPTION 'realization not active in bound release' USING ERRCODE='23514'; END IF;
 -- The receipt exists in this transaction before occurrence FKs are checked.
 UPDATE data.realization SET data_revision=data_revision+1 WHERE release_id=r AND realization_id=z RETURNING data_revision INTO rev;
 INSERT INTO data.batch(release_id,realization_id,batch_id,content,content_digest,data_revision) VALUES(r,z,b,actual,encode(sha256(actual),'hex'),rev);
 {insert}
 PERFORM data.validate_state(r,z);
 FOR f IN SELECT * FROM pg_temp.sp_occurrence LOOP
 expected:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.source,f.item)),'UTF8')),'hex');
 IF expected<>f.occurrence_id THEN RAISE EXCEPTION 'invalid occurrence identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM pg_temp.sp_fact LOOP
 expected:='fact:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.subject_id,f.property_id,data.value_meaning(r,z,f.object_value_id),CASE WHEN f.qualification_value_id IS NULL THEN jsonb_build_array('mapping','[]'::jsonb) ELSE data.value_meaning(r,z,f.qualification_value_id,'{{}}',true) END)),'UTF8')),'hex');
 IF expected<>f.fact_id THEN RAISE EXCEPTION 'invalid fact identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN rev;
END $fn$;
''')
    signatures = (
        "canonical_json(jsonb)", "compare_decimal(text,text)", "value_meaning(text,text,text,text[],boolean)",
        "value_matches(text,text,text,text,boolean)", "validate_state(text,text)",
        "validate_property(text,text,text,text,jsonb)", "begin_stage()",
        "publish_batch(text,text,text,bytea)",
    )
    for signature in signatures:
        connection.exec_driver_sql(f"ALTER FUNCTION data.{signature} OWNER TO {publisher}")
        connection.exec_driver_sql(f"REVOKE ALL ON FUNCTION data.{signature} FROM PUBLIC,{writer},{reader}")
    for signature in ("begin_stage()", "publish_batch(text,text,text,bytea)"):
        connection.exec_driver_sql(f"GRANT EXECUTE ON FUNCTION data.{signature} TO {writer}")
