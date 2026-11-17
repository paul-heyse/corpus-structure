"""Independent physical obligations for native release lowering and bounded lookup."""

from corpus_structure.semantic.metadata import table


def test_native_fact_tables_keep_release_and_current_lowering_distinct():
    release = table("sem.data_operation_release")
    assert {"model_digest", "native_definitions_digest", "native_kernel_digest", "lowering_digest"} <= set(release.c.keys())
    assert list(table("sem.data_subject_scope").primary_key.columns.keys()) == ["release_id", "subject_definition"]
    operation = table("sem.data_operation_definition")
    for name in ("binding_expression", "definition_identity", "eligibility_identity", "quantified", "dependencies"):
        assert not operation.c[name].nullable
    assert not table("sem.runtime_binding").c.execution_profile.nullable


def test_frontier_indexes_follow_actual_lookup_keys():
    def indexes(name):
        return {tuple(column.name for column in index.columns): index for index in table(name).indexes}

    assert ("demand_id", "id") in indexes("ops.data_obligation")
    assert ("request_id", "generation") in indexes("ops.data_derivation")
    assert ("product_id", "member_id") in indexes("ops.data_derivation_output")
    assert ("owner_xid",) in indexes("ops.data_demand_read")
    assert ("demand_id", "name", "context_key", "created_at", "id") in indexes("ops.data_population")
    use_indexes = indexes("ops.demand_use")
    assert use_indexes[("demand_id", "fate")].dialect_options["postgresql"]["include"] == ["obligation_id", "derivation_id", "created_at"]
    assert str(use_indexes[("derivation_id",)].dialect_options["postgresql"]["where"]) == "derivation_id IS NOT NULL"
