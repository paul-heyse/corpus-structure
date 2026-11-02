DO $placement$ BEGIN IF EXISTS(SELECT 1 AS anon_1 
FROM kb.source_view AS prior 
WHERE NOT (EXISTS (SELECT 1 AS anon_2 
FROM ops.pdf_published_revision AS published JOIN kb.pdf_record_access AS address ON address.product_id = published.build_id AND address.revision_id = published.build_id AND address.pointer = prior.section_pointer 
WHERE published.task_id = prior.native_task_id AND published.product_key = prior.native_product_key AND published.logical_digest = prior.native_content_digest))) THEN RAISE EXCEPTION 'unbound legacy published address in %; preserve archived revision', 'kb.source_view' USING ERRCODE='55000'; END IF;
IF EXISTS(SELECT 1 AS anon_1 
FROM ops.native_region_artifact AS prior 
WHERE NOT (EXISTS (SELECT 1 AS anon_2 
FROM ops.pdf_published_revision AS published JOIN kb.pdf_record_region AS address ON address.product_id = published.build_id AND address.revision_id = published.build_id AND address.pointer = prior.pointer AND address.region_index = prior.region_index 
WHERE published.task_id = prior.native_task_id AND published.product_key = prior.native_product_key AND published.logical_digest = prior.native_content_digest))) THEN RAISE EXCEPTION 'unbound legacy published address in %; preserve archived revision', 'ops.native_region_artifact' USING ERRCODE='55000'; END IF; END $placement$;;

ALTER TABLE ops.pdf_published_revision ADD CONSTRAINT uq_pdf_published_revision_build_id_task_id_product_key__6c20 UNIQUE (build_id, task_id, product_key, logical_digest);

ALTER TABLE kb.source_view ADD COLUMN native_build_id TEXT;

ALTER TABLE kb.source_view ADD COLUMN native_revision_id TEXT;

ALTER TABLE ops.native_region_artifact ADD COLUMN native_build_id TEXT;

ALTER TABLE ops.native_region_artifact ADD COLUMN native_revision_id TEXT;

DO $placement$
DECLARE owner_name text; previous_role text:=current_setting('role');
BEGIN
 IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid='kb.source_view'::regclass
 AND tgname='semantic_immutable' AND NOT tgisinternal AND tgenabled='O') THEN
 RAISE EXCEPTION 'published address migration requires enabled semantic_immutable on kb.source_view'
 USING ERRCODE='55000'; END IF;
 SELECT pg_get_userbyid(relowner) INTO STRICT owner_name FROM pg_class
 WHERE oid='kb.source_view'::regclass;
 EXECUTE format('SET LOCAL ROLE %I',owner_name);
 ALTER TABLE kb.source_view DISABLE TRIGGER semantic_immutable;
 UPDATE kb.source_view SET native_build_id=ops.pdf_published_revision.build_id, native_revision_id=ops.pdf_published_revision.build_id FROM ops.pdf_published_revision WHERE kb.source_view.native_task_id = ops.pdf_published_revision.task_id AND kb.source_view.native_product_key = ops.pdf_published_revision.product_key AND kb.source_view.native_content_digest = ops.pdf_published_revision.logical_digest;
 ALTER TABLE kb.source_view ENABLE TRIGGER semantic_immutable;
 IF previous_role='none' THEN EXECUTE 'SET LOCAL ROLE NONE';
 ELSE EXECUTE format('SET LOCAL ROLE %I',previous_role); END IF;
END $placement$;
DO $placement$
DECLARE owner_name text; previous_role text:=current_setting('role');
BEGIN
 IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid='ops.native_region_artifact'::regclass
 AND tgname='semantic_immutable' AND NOT tgisinternal AND tgenabled='O') THEN
 RAISE EXCEPTION 'published address migration requires enabled semantic_immutable on ops.native_region_artifact'
 USING ERRCODE='55000'; END IF;
 SELECT pg_get_userbyid(relowner) INTO STRICT owner_name FROM pg_class
 WHERE oid='ops.native_region_artifact'::regclass;
 EXECUTE format('SET LOCAL ROLE %I',owner_name);
 ALTER TABLE ops.native_region_artifact DISABLE TRIGGER semantic_immutable;
 UPDATE ops.native_region_artifact SET native_build_id=ops.pdf_published_revision.build_id, native_revision_id=ops.pdf_published_revision.build_id FROM ops.pdf_published_revision WHERE ops.native_region_artifact.native_task_id = ops.pdf_published_revision.task_id AND ops.native_region_artifact.native_product_key = ops.pdf_published_revision.product_key AND ops.native_region_artifact.native_content_digest = ops.pdf_published_revision.logical_digest;
 ALTER TABLE ops.native_region_artifact ENABLE TRIGGER semantic_immutable;
 IF previous_role='none' THEN EXECUTE 'SET LOCAL ROLE NONE';
 ELSE EXECUTE format('SET LOCAL ROLE %I',previous_role); END IF;
END $placement$;;

ALTER TABLE kb.source_view ALTER COLUMN native_build_id SET NOT NULL;

ALTER TABLE kb.source_view ALTER COLUMN native_revision_id SET NOT NULL;

ALTER TABLE ops.native_region_artifact ALTER COLUMN native_build_id SET NOT NULL;

ALTER TABLE ops.native_region_artifact ALTER COLUMN native_revision_id SET NOT NULL;

ALTER TABLE kb.source_view DROP CONSTRAINT fk_source_view_native_task_id_native_product_key_sectio_e425;

ALTER TABLE kb.source_view ADD CONSTRAINT fk_source_view_native_build_id_native_revision_id_secti_79ff FOREIGN KEY(native_build_id, native_revision_id, section_pointer) REFERENCES kb.pdf_record_access (product_id, revision_id, pointer);

ALTER TABLE kb.source_view ADD CONSTRAINT fk_source_view_native_build_id_native_task_id_native_pr_bef7 FOREIGN KEY(native_build_id, native_task_id, native_product_key, native_content_digest) REFERENCES ops.pdf_published_revision (build_id, task_id, product_key, logical_digest);

ALTER TABLE kb.source_view ADD CONSTRAINT ck_source_view_physical_73dfcc4ba8 CHECK (native_build_id = native_revision_id);

ALTER TABLE ops.native_region_artifact DROP CONSTRAINT fk_native_region_artifact_native_task_id_native_product_512c;

ALTER TABLE ops.native_region_artifact ADD CONSTRAINT fk_native_region_artifact_native_build_id_native_task_i_e848 FOREIGN KEY(native_build_id, native_task_id, native_product_key, native_content_digest) REFERENCES ops.pdf_published_revision (build_id, task_id, product_key, logical_digest);

ALTER TABLE ops.native_region_artifact ADD CONSTRAINT fk_native_region_artifact_native_build_id_native_revisi_6345 FOREIGN KEY(native_build_id, native_revision_id, pointer, region_index) REFERENCES kb.pdf_record_region (product_id, revision_id, pointer, region_index);

ALTER TABLE ops.native_region_artifact ADD CONSTRAINT ck_native_region_artifact_physical_73dfcc4ba8 CHECK (native_build_id = native_revision_id);

