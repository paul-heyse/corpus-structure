SET LOCAL ROLE corpus_sem_publisher;
CREATE INDEX IF NOT EXISTS ix_parsing_layer_component_task_id_category ON kb.parsing_layer_component (task_id, category);
CREATE INDEX IF NOT EXISTS ix_parsing_layer_component_task_id_representation_id_st_6e5c ON kb.parsing_layer_component (task_id, representation_id, start_offset, end_offset);
CREATE INDEX IF NOT EXISTS ix_parsing_layer_mapping_endpoint_target_task_id_repres_33b7 ON kb.parsing_layer_mapping_endpoint (target_task_id, representation_id, side, start_offset, end_offset);
CREATE INDEX IF NOT EXISTS ix_parsing_layer_mapping_endpoint_target_task_id_repres_13fb ON kb.parsing_layer_mapping_endpoint (target_task_id, representation_id, start_offset, end_offset);
CREATE INDEX IF NOT EXISTS ix_parsing_layer_mapping_endpoint_task_id_representatio_6cf2 ON kb.parsing_layer_mapping_endpoint (task_id, representation_id, side, start_offset, end_offset);
