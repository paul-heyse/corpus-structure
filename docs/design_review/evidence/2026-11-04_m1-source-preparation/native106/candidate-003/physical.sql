ALTER TABLE ops.task_dependency DROP CONSTRAINT ck_task_dependency_physical_6fe2d0b78b;
ALTER TABLE ops.task_dependency ADD CONSTRAINT ck_task_dependency_physical_c683b2f601 CHECK (kind IN ('ancestor_source_view','source_view_interpretation','source_view_product'));
