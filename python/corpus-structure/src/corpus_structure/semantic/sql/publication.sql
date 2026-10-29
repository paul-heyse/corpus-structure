CREATE OR REPLACE FUNCTION data.begin_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 {create}
END $fn$;
CREATE OR REPLACE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE actual bytea; old data.batch%ROWTYPE; rev bigint; f record; application record; expected text;
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
 IF EXISTS(SELECT FROM pg_temp.sp_value_role candidate JOIN data.typed_value parent ON parent.release_id=r AND parent.realization_id=z AND parent.value_id=candidate.parent_value_id WHERE NOT EXISTS(SELECT FROM data.value_role existing WHERE existing.release_id=r AND existing.realization_id=z AND (existing.parent_value_id,existing.role,existing.position,existing.child_value_id)=(candidate.parent_value_id,candidate.role,candidate.position,candidate.child_value_id))) THEN RAISE EXCEPTION 'existing typed value graph is immutable' USING ERRCODE='23514'; END IF;
 {insert}
 PERFORM data.validate_state(r,z);
 FOR f IN SELECT * FROM pg_temp.sp_occurrence LOOP
 expected:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.source,f.item)),'UTF8')),'hex');
 IF expected<>f.occurrence_id THEN RAISE EXCEPTION 'invalid occurrence identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM pg_temp.sp_fact LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'invalid fact identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM data.fact WHERE release_id=r AND realization_id=z LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'admitted fact meaning changed' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT o.*,df.subject_id,df.property_id FROM data.occurrence o JOIN data.fact df ON (df.release_id,df.realization_id,df.fact_id)=(o.release_id,o.realization_id,o.fact_id) WHERE o.release_id=r AND o.realization_id=z LOOP
 IF NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id) THEN RAISE EXCEPTION 'report property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR application IN SELECT pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id LOOP
 PERFORM data.validate_property(r,z,f.report_object_value_id,COALESCE(application.constraints->>'native_range',application.range_name),CASE WHEN application.constraint_scope='shape' THEN application.constraints ELSE application.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END LOOP;
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.report_object_value_id,f.report_qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'report meaning differs from fact' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND (c.name='Qualification' OR EXISTS(SELECT FROM sem.class_hierarchy h JOIN sem.class_definition root ON root.release_id=h.release_id AND root.class_id=h.ancestor_id AND root.name='Qualification' WHERE h.release_id=r AND h.class_id=c.class_id)) WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.report_qualification_value_id) THEN RAISE EXCEPTION 'report requires typed qualification' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN rev;
END $fn$;
