"""Actual release-scoped relational execution contracts and native consumers."""

import pytest
from sqlalchemy import text


def test_execution_table_posture(semantic_db_engine, admitter):
    with admitter.connect() as conn:
        columns = conn.execute(
            text("""
            SELECT attname,format_type(atttypid,atttypmod),attnotnull
            FROM pg_attribute WHERE attrelid='sem.execution_edge'::regclass
              AND attnum>0 AND NOT attisdropped ORDER BY attnum
        """)
        ).all()
        assert columns == [
            (name, "text", True)
            for name in ("release_id", "transition_id", "prior_state", "result_state")
        ]
        assert (
            conn.scalar(
                text("""
            SELECT confrelid::regclass::text FROM pg_constraint
            WHERE conrelid='sem.execution_edge'::regclass AND contype='f'
        """)
            )
            == "sem.execution_transition"
        )
        for principal in (
            "corpus_sem_writer",
            "corpus_sem_reader",
            "corpus_sem_evaluator",
            "corpus_sem_admitter",
        ):
            assert (
                conn.scalar(
                    text("""
                SELECT has_table_privilege(:principal,'sem.execution_edge','SELECT')
                  AND NOT has_table_privilege(:principal,'sem.execution_edge',
                                              'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            """),
                    {"principal": principal},
                )
                is True
            )


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "moved",
        "transition",
        "version",
        "effect_version",
        "binding_only",
        "duplicate",
        "unresolved",
    ],
)
def test_changed_effect_requirements_refuse_before_authoring(change):
    from dataclasses import replace

    import yaml

    from corpus_structure.semantic.contracts import (
        compile_execution_model,
        trusted_execution_inputs,
    )
    from corpus_structure.semantic.types import PreparationError, SourceArtifact

    inputs = trusted_execution_inputs()
    compile_execution_model(inputs)
    expected = {
        "unknown": ("unsupported_effect", "delete_archive"),
        "moved": ("unsupported_effect_profile", "archive"),
        "transition": ("unsupported_effect_profile", "capture_cut"),
        "version": ("unsupported_effect_profile", "archive"),
        "effect_version": ("unsupported_effect", "persist_exact_archive"),
        "binding_only": ("implementation_effects", "archive"),
        "duplicate": ("duplicate_definition", "effect_definitions"),
        "unresolved": ("unresolved_contract_reference", "archive"),
    }[change]
    catalog = yaml.safe_load(inputs.catalog.content)
    operations = {o["id"]: o for o in catalog["operations"]}
    bindings = {b["id"]: b for b in catalog["implementations"]}
    if change == "unknown":
        catalog["effect_definitions"].append(
            {"id": "delete_archive", "version": "1", "meaning": "delete archived source bytes"}
        )
        operations["archive"]["effects"] = ["delete_archive"]
        bindings["archive"]["effects"] = ["delete_archive"]
    elif change == "moved":
        operations["archive"]["effects"] = ["construct_new_run"]
        bindings["archive"]["effects"] = ["construct_new_run"]
    elif change == "transition":
        next(t for t in catalog["transitions"] if t["id"] == "run_final_cut")["effects"] = [
            "immutable_cut"
        ]
    elif change == "version":
        bindings["archive"]["version"] = "999"
    elif change == "effect_version":
        next(e for e in catalog["effect_definitions"] if e["id"] == "persist_exact_archive")[
            "version"
        ] = "2"
    elif change == "binding_only":
        bindings["archive"]["effects"] = ["construct_new_run"]
    elif change == "duplicate":
        catalog["effect_definitions"].append(dict(catalog["effect_definitions"][0]))
    else:
        operations["archive"]["effects"] = ["unresolved_required_effect"]
        bindings["archive"]["effects"] = ["unresolved_required_effect"]
    candidate = replace(
        inputs, catalog=SourceArtifact(inputs.catalog.name, yaml.safe_dump(catalog).encode())
    )
    with pytest.raises(PreparationError) as refused:
        compile_execution_model(candidate)
    diagnostics = refused.value.diagnostics
    assert expected in {(diagnostic.code, diagnostic.location) for diagnostic in diagnostics}
    if expected[0] in {"unsupported_effect", "unsupported_effect_profile"}:
        diagnostic = next(
            diagnostic
            for diagnostic in diagnostics
            if (diagnostic.code, diagnostic.location) == expected
        )
        if change in {"unknown", "effect_version"}:
            full_expected = (
                "delete_archive" if change == "unknown" else "persist_exact_archive",
                "owned effect implementation",
                "None" if change == "unknown" else "'1'",
                "1" if change == "unknown" else "2",
                "implement this effect version and derive a new reviewed release before admission",
            )
        else:
            if change == "transition":
                owned = {
                    "effects": ("final_cut_seals_source_atomically", "immutable_cut"),
                    "implementation": "cut",
                    "transitions": {
                        "run_final_cut": ("capture_final_cut", "seal_source_production")
                    },
                    "version": "1",
                }
                changed = {
                    "implementation": "cut",
                    "version": "1",
                    "effects": ("final_cut_seals_source_atomically", "immutable_cut"),
                    "transitions": {"run_final_cut": ("immutable_cut",)},
                }
                consumer = "semantic.operations:seal_cut"
            else:
                owned = {
                    "effects": ("persist_exact_archive",),
                    "implementation": "archive",
                    "transitions": {},
                    "version": "1",
                }
                changed = {
                    "implementation": "archive",
                    "version": "999" if change == "version" else "1",
                    "effects": ("construct_new_run",)
                    if change == "moved"
                    else ("persist_exact_archive",),
                    "transitions": {},
                }
                consumer = "semantic.releases:persist_release"
            full_expected = (
                expected[1],
                consumer,
                repr(owned),
                repr(changed),
                "implement the required bounded effect profile, then "
                "ci schema derive --out <new-directory> and deploy a reviewed forward revision",
            )
        assert (
            diagnostic.contract_id,
            diagnostic.consumer,
            diagnostic.expected,
            diagnostic.actual,
            diagnostic.remedy,
        ) == full_expected


def test_candidate_edge_rows_change_native_answer_without_replacing_guard(
    semantic_db_engine, semantic_writer_engine, admitter
):
    from dataclasses import replace

    import yaml
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.contracts import trusted_execution_inputs
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import SourceArtifact

    from .test_execution_release import _bundle

    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    transition = next(t for t in catalog["transitions"] if t["id"] == "run_start_source")
    transition["to_states"] = ["consolidating"]
    candidate = replace(
        inputs, catalog=SourceArtifact(inputs.catalog.name, yaml.safe_dump(catalog).encode())
    )
    deps = composed_dependencies(ResolvedDependencies(), candidate)
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(_bundle(), deps, profile)
    with admitter.begin() as conn:
        before = conn.scalar(
            text(
                "SELECT prosrc FROM pg_proc WHERE "
                "oid='ops.execution_edge(text,text,text,text)'::regprocedure"
            )
        )
        persist_release(conn, _bundle(), deps, profile, prepared)
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT ops.execution_edge(:r,'run','created','consolidating')"),
                {"r": prepared.release_id},
            )
            is True
        )
        assert (
            conn.scalar(
                text("SELECT ops.execution_edge(:r,'run','created','running')"),
                {"r": prepared.release_id},
            )
            is False
        )
        assert (
            conn.scalar(
                text(
                    "SELECT prosrc FROM pg_proc WHERE "
                    "oid='ops.execution_edge(text,text,text,text)'::regprocedure"
                )
            )
            == before
        )
    # The unchanged complete start kernel cannot silently execute an edge removed by the model.
    with (
        semantic_db_engine.begin() as conn,
        pytest.raises(DBAPIError, match="undeclared operation transition"),
        conn.begin_nested(),
    ):
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text("SELECT ops.require_transition(:r,'execute_source','created','running')"),
            {"r": prepared.release_id},
        )


@pytest.mark.parametrize("revision", ["semantic_0030", "semantic_0031", "semantic_0032"])
def test_supported_predecessors_upgrade_to_relational_execution(semantic_database_at, revision):
    from corpus_structure.semantic.migrations import upgrade

    with semantic_database_at(revision) as engine, engine.begin() as conn:
        upgrade(conn, "semantic_0033")
        assert (
            conn.scalar(text("SELECT version_num FROM semantic_alembic_version")) == "semantic_0033"
        )
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='sem' "
                    "AND table_name IN ('execution_operation','execution_transition',"
                    "'execution_edge','operation_effect','transition_effect',"
                    "'operation_property_role','scientific_decision_rule')"
                )
            )
            == 7
        )


@pytest.mark.parametrize("operation", ["configure_method", "register_document"])
def test_actual_global_helper_requires_its_bound_operation(operation, semantic_writer_engine):
    import json
    from dataclasses import replace
    from pathlib import Path

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operations import register_document
    from corpus_structure.semantic.regeneration import prepare_packs
    from corpus_structure.semantic.types import PreparationError

    _bundle, _deps, _profile, prepared = prepare_packs((Path("domains/statistics"),))
    row = next(r for r in prepared.registry_rows if r.kind == "execution_model")
    body = json.loads(row.body)
    body["operations"] = [o for o in body["operations"] if o["id"] != operation]
    missing = replace(
        prepared,
        registry_rows=tuple(
            replace(r, body=canonical_bytes(body)) if r is row else r
            for r in prepared.registry_rows
        ),
    )
    with semantic_writer_engine.connect() as connection, pytest.raises(PreparationError) as refused:
        if operation == "configure_method":
            from corpus_structure.semantic import operations

            # Deliberate dynamic invalid input must reach the missing-operation guard first.
            vars(operations)["record_method"](
                connection, None, "test", {}, "test", prepared=missing
            )
        else:
            register_document(
                connection,
                project_id="p",
                source_uri="urn:x",
                original_path="missing",
                original=b"",
                prepared=missing,
                mime="text/html",
            )
    assert refused.value.diagnostics[0].code == "missing_operation"
    assert refused.value.diagnostics[0].contract_id == operation


def test_explicit_transport_order_cannot_place_evidence_links_before_evidence():
    from corpus_structure.semantic.publication import STAGE_TYPES
    from corpus_structure.semantic.routines import _transport_sql

    order = [
        "identity_exclusion_evidence",
        *[name for name in STAGE_TYPES if name != "identity_exclusion_evidence"],
    ]
    with pytest.raises(ValueError, match="publication dependencies"):
        _transport_sql("corpus_sem_writer", relation_order=tuple(order))


@pytest.mark.parametrize("change", ["empty", "partial", "moved", "optionalized"])
def test_native_admission_rejects_unimplemented_scientific_layout(
    semantic_db_engine, admitter, change
):
    import json
    from hashlib import sha256
    from pathlib import Path

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.regeneration import prepare_packs
    from corpus_structure.semantic.releases import persist_release

    from .archive_faults import administrative_archive_edit

    bundle, dependencies, profile, prepared = prepare_packs((Path("domains/statistics"),))
    with admitter.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
    # Independently challenge native compatibility after the compiler has verified its source.
    # Only the authenticated administrator can inject this formerly admitted/corrupt recipe.
    with (
        semantic_db_engine.begin() as admin,
        administrative_archive_edit(admin, table("sem.artifact")),
    ):
        original = bytes(
            admin.scalar(
                text(
                    "SELECT content FROM sem.artifact WHERE release_id=:release "
                    "AND artifact_name='operation/scientific-policy.json'"
                ),
                {"release": prepared.release_id},
            )
        )
        recipe = json.loads(original)
        if change == "empty":
            recipe["comparison_paths"], recipe["array_rules"] = [], []
        elif change == "partial":
            recipe["comparison_paths"] = recipe["comparison_paths"][:1]
        elif change == "moved":
            recipe["comparison_paths"][0] = "$.unconsumed[*].comparisons[*]"
        else:
            next(rule for rule in recipe["array_rules"] if rule["field"] == "units")["required"] = (
                False
            )
        encoded = json.dumps(recipe).encode()
        admin.execute(
            text(
                "UPDATE sem.artifact SET content=:content,content_digest=:digest "
                "WHERE release_id=:release AND artifact_name='operation/scientific-policy.json'"
            ),
            {
                "content": encoded,
                "digest": sha256(encoded).hexdigest(),
                "release": prepared.release_id,
            },
        )
    with (
        pytest.raises(DBAPIError, match="unsupported scientific report layout"),
        admitter.begin() as connection,
    ):
        connection.execute(
            text("SELECT data.require_execution_release(:release)"),
            {"release": prepared.release_id},
        )
