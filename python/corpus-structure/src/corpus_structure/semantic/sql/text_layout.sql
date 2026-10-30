SET LOCAL ROLE corpus_sem_publisher;
INSERT INTO sem.physical_contract(physical_id,checks,source_digest) SELECT '{physical_id}',checks,source_digest FROM sem.physical_contract WHERE physical_id='physical:8647234638afd6bb2a79c05411ccbae24ab8ac0624954a5808fb78d907129a25' ON CONFLICT DO NOTHING;
SET LOCAL ROLE __MIGRATION_OWNER__;
CREATE TRIGGER token_layout_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON ops.rendition_build FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();
SET LOCAL ROLE corpus_sem_publisher;
