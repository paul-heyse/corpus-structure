"""Fenced original PDF producer and immutable recovery contributor custody."""


def pdf_spool_native_sql() -> str:
    return """
CREATE OR REPLACE FUNCTION ops.register_pdf_spool_producer(p_build text,p_task bigint,
 p_attempt bigint,p_holder text,p_runtime text,p_device bigint,p_inode bigint,p_premises bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; basis_ record; premises_ jsonb; id_ text;
 prior ops.pdf_spool_producer;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'stage_pdf_producer');
 SELECT * INTO STRICT basis_ FROM ops.read_pdf_producer_basis(p_task,p_attempt,p_holder,p_runtime);
 premises_:=convert_from(p_premises,'UTF8')::jsonb;
 IF p_device IS NULL OR p_device<0 OR p_inode IS NULL OR p_inode<1
 OR premises_->'producer' IS DISTINCT FROM to_jsonb(basis_)
 OR premises_->>'source_digest' IS DISTINCT FROM b.source_digest
 OR premises_->>'native_recipe_digest' IS DISTINCT FROM b.recipe_digest
 OR premises_->>'native_schema_digest' IS DISTINCT FROM b.schema_digest
 OR COALESCE(premises_->>'payload_schema_digest','') !~ '^[0-9a-f]{64}$'
 OR jsonb_typeof(premises_->'packages') IS DISTINCT FROM 'array'
 OR jsonb_array_length(premises_->'packages')=0 THEN
 RAISE EXCEPTION 'PDF spool producer premises differ from admitted native basis' USING ERRCODE='23514';
 END IF;
 id_:=encode(sha256(convert_to(jsonb_build_array(p_build,p_task,p_attempt,p_holder,
 p_device,p_inode)::text,'UTF8')),'hex');
 INSERT INTO ops.pdf_spool_producer(producer_id,build_id,task_id,attempt,holder,
 writer_device,writer_inode,premises_bytes)
 VALUES(id_,p_build,p_task,p_attempt,p_holder,p_device,p_inode,p_premises)
 ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT prior FROM ops.pdf_spool_producer WHERE producer_id=id_;
 IF prior.premises_bytes IS DISTINCT FROM p_premises THEN
 RAISE EXCEPTION 'PDF spool producer replay differs' USING ERRCODE='23514'; END IF;
 RETURN id_;
END $$;
CREATE OR REPLACE FUNCTION ops.register_pdf_spool_contributor(p_build text,p_task bigint,
 p_attempt bigint,p_holder text,p_runtime text,p_producer text,p_manifest bytea,p_selected bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; producer_ ops.pdf_spool_producer; current_ record;
 original_ jsonb; current_basis_ jsonb; current_premises_ jsonb; header_ jsonb; declaration_ jsonb;
 lines_ text[]; line_ text; entry_ jsonb; selected_ jsonb; replay_ jsonb;
 inventory_ jsonb:='[]'::jsonb; id_ text; manifest_ text; selection_ text;
 prior ops.pdf_spool_contributor;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'stage_pdf_producer');
 SELECT * INTO STRICT current_ FROM ops.read_pdf_producer_basis(p_task,p_attempt,p_holder,p_runtime);
 SELECT * INTO STRICT producer_ FROM ops.pdf_spool_producer WHERE producer_id=p_producer;
 original_:=convert_from(producer_.premises_bytes,'UTF8')::jsonb;
 current_basis_:=to_jsonb(current_)-'runtime_id'-'runtime_manifest_digest';
 SELECT convert_from(premises_bytes,'UTF8')::jsonb INTO STRICT current_premises_
 FROM ops.pdf_spool_producer WHERE build_id=p_build AND attempt=p_attempt AND holder=p_holder;
 IF producer_.build_id IS DISTINCT FROM p_build OR producer_.task_id IS DISTINCT FROM p_task
 OR producer_.attempt>p_attempt OR (producer_.attempt=p_attempt AND producer_.holder<>p_holder)
 OR ((original_->'producer')-'runtime_id'-'runtime_manifest_digest') IS DISTINCT FROM current_basis_
 OR original_->>'source_digest' IS DISTINCT FROM b.source_digest
 OR original_->>'native_recipe_digest' IS DISTINCT FROM b.recipe_digest
 OR original_->>'native_schema_digest' IS DISTINCT FROM b.schema_digest
 OR (original_-'producer') IS DISTINCT FROM (current_premises_-'producer') THEN
 RAISE EXCEPTION 'PDF spool contributor has no matching original producer' USING ERRCODE='23514'; END IF;
 IF p_manifest IS NULL OR octet_length(p_manifest)=0 OR right(convert_from(p_manifest,'UTF8'),1)<>E'\\n' THEN
 RAISE EXCEPTION 'PDF spool manifest has no durable complete entries' USING ERRCODE='23514'; END IF;
 lines_:=string_to_array(rtrim(convert_from(p_manifest,'UTF8'),E'\\n'),E'\\n');
 IF cardinality(lines_)<2 THEN RAISE EXCEPTION 'PDF spool manifest lacks producer declaration'; END IF;
 header_:=lines_[1]::jsonb; declaration_:=lines_[2]::jsonb;
 IF header_->>'version' IS DISTINCT FROM 'pdf-build-spool-1'
 OR header_->>'build_id' IS DISTINCT FROM p_build
 OR (header_->>'task_id')::bigint IS DISTINCT FROM producer_.task_id
 OR (header_->>'attempt')::bigint IS DISTINCT FROM producer_.attempt
 OR header_->>'holder' IS DISTINCT FROM producer_.holder
 OR (header_->'writer'->>'device')::bigint IS DISTINCT FROM producer_.writer_device
 OR (header_->'writer'->>'inode')::bigint IS DISTINCT FROM producer_.writer_inode
 OR declaration_->>'producer_id' IS DISTINCT FROM p_producer
 OR declaration_->'premises' IS DISTINCT FROM original_ THEN
 RAISE EXCEPTION 'PDF manifest differs from immutable original producer custody' USING ERRCODE='23514'; END IF;
 FOREACH line_ IN ARRAY lines_[3:] LOOP
 entry_:=line_::jsonb;
 IF entry_ ? 'replay' THEN inventory_:=inventory_||jsonb_build_array(entry_->'replay');
 ELSIF NOT entry_ ? 'completion' THEN
 RAISE EXCEPTION 'PDF spool manifest entry is not declared'; END IF;
 END LOOP;
 selected_:=convert_from(p_selected,'UTF8')::jsonb;
 IF jsonb_typeof(selected_) IS DISTINCT FROM 'array' OR jsonb_array_length(selected_)=0 THEN
 RAISE EXCEPTION 'PDF spool contributor selected no files'; END IF;
 FOR replay_ IN SELECT value FROM jsonb_array_elements(selected_) LOOP
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(inventory_) member WHERE member.value=replay_)
 OR COALESCE(replay_->>'digest','') !~ '^[0-9a-f]{64}$'
 OR (replay_->>'byte_length')::bigint<0
 OR nullif(replay_->>'path','') IS NULL THEN
 RAISE EXCEPTION 'selected PDF replay differs from original manifest membership' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(selected_) IS DISTINCT FROM (
 SELECT count(DISTINCT value->>'path') FROM jsonb_array_elements(selected_)) THEN
 RAISE EXCEPTION 'PDF spool contributor repeats a selected path'; END IF;
 manifest_:=encode(sha256(p_manifest),'hex'); selection_:=encode(sha256(p_selected),'hex');
 id_:=encode(sha256(convert_to(jsonb_build_array(p_build,p_producer,manifest_,selection_)::text,'UTF8')),'hex');
 INSERT INTO ops.pdf_spool_contributor(contributor_id,build_id,producer_id,manifest_digest,
 selection_digest,manifest_bytes,selected_replays,adopter_attempt,adopter_holder)
 VALUES(id_,p_build,p_producer,manifest_,selection_,p_manifest,p_selected,p_attempt,p_holder)
 ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT prior FROM ops.pdf_spool_contributor WHERE contributor_id=id_;
 IF prior.manifest_bytes IS DISTINCT FROM p_manifest OR prior.selected_replays IS DISTINCT FROM p_selected THEN
 RAISE EXCEPTION 'PDF contributor replay differs'; END IF;
 RETURN id_;
END $$;
CREATE OR REPLACE FUNCTION ops.pdf_spool_contributors(p_build text)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT COALESCE(jsonb_agg(jsonb_build_object(
 'producer_id',p.producer_id,'task_id',p.task_id,'producer_attempt',p.attempt,
 'producer_holder',p.holder,'runtime_id',convert_from(p.premises_bytes,'UTF8')::jsonb->'producer'->>'runtime_id',
 'runtime_manifest_digest',convert_from(p.premises_bytes,'UTF8')::jsonb->'producer'->>'runtime_manifest_digest',
 'manifest_digest',c.manifest_digest,'selection_digest',c.selection_digest,
 'adopter_attempt',c.adopter_attempt,'adopter_holder',c.adopter_holder
 ) ORDER BY p.producer_id,c.manifest_digest,c.selection_digest),'[]'::jsonb)
 FROM ops.pdf_spool_contributor c JOIN ops.pdf_spool_producer p USING(producer_id)
 WHERE c.build_id=p_build
$$;
CREATE OR REPLACE FUNCTION ops.read_pdf_spool_contributors(p_build text,p_task bigint,p_attempt bigint,p_holder text)
RETURNS TABLE(producer_id text,task_id bigint,producer_attempt bigint,producer_holder text,
 runtime_id text,runtime_manifest_digest text,manifest_digest text,selection_digest text,
 adopter_attempt bigint,adopter_holder text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_build b WHERE b.build_id=p_build AND b.task_id=p_task) THEN
 RAISE EXCEPTION 'PDF contributor read has no owned build'; END IF;
 RETURN QUERY SELECT * FROM jsonb_to_recordset(ops.pdf_spool_contributors(p_build)) AS r(
 producer_id text,task_id bigint,producer_attempt bigint,producer_holder text,
 runtime_id text,runtime_manifest_digest text,manifest_digest text,selection_digest text,
 adopter_attempt bigint,adopter_holder text) ORDER BY r.producer_id,r.manifest_digest,r.selection_digest;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_spool_contributors(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.register_pdf_spool_producer(text,bigint,bigint,text,text,bigint,bigint,bytea) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.register_pdf_spool_contributor(text,bigint,bigint,text,text,text,bytea,bytea) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.read_pdf_spool_contributors(text,bigint,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.register_pdf_spool_producer(text,bigint,bigint,text,text,bigint,bigint,bytea),
 ops.register_pdf_spool_contributor(text,bigint,bigint,text,text,text,bytea,bytea),
 ops.read_pdf_spool_contributors(text,bigint,bigint,text) TO corpus_sem_writer;
"""
