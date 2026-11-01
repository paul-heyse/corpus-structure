
INSERT INTO ops.pdf_product(task_id,product_key,content_digest,kind,artifact_digest,release_id,contract_digest)
 SELECT p.task_id,p.product_key,p.content_digest,'native',b.artifact_digest,p.release_id,p.contract_digest
 FROM ops.native_document_product p JOIN ops.source_build b USING(task_id);
INSERT INTO kb.pdf_occurrence(task_id,product_key,occurrence_id,kind,address_space,precision,body)
 SELECT task_id,product_key,pointer,CASE WHEN label='formula' THEN 'formula' ELSE 'item' END,'native_item','item',jsonb_build_object('pointer',pointer,'native_value',native_json) FROM kb.native_document_item;
INSERT INTO kb.pdf_occurrence(task_id,product_key,occurrence_id,kind,address_space,precision,body)
 SELECT i.task_id,i.product_key,i.pointer||'/data/table_cells/'||(c.n-1)::text,'cell','native_cell','cell',jsonb_build_object('pointer',i.pointer,'cell_index',c.n-1,'native_value',c.value,'regions',i.native_json->'prov')
 FROM kb.native_document_item i CROSS JOIN LATERAL jsonb_array_elements(COALESCE(i.native_json->'data'->'table_cells','[]')) WITH ORDINALITY c(value,n) WHERE i.label='table';
DO $backfill$ DECLARE product record; BEGIN FOR product IN SELECT task_id,product_key FROM ops.native_document_product LOOP
 PERFORM ops.register_native_pdf(product.task_id,product.product_key); END LOOP; END $backfill$;
