"""Literal archive/provider controls for the actual generated PostgreSQL compiler.

These finite archived facts test native lowering fidelity and refusal, without
claiming that the literal release is a separately prepared/admitted user model.
"""

from hashlib import sha256

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_compiler_native import compiler_native_sql
from corpus_structure.semantic.data_operation_subjects import subject_scope_values
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from semantic.data_operation_kernel_support import STORAGE
from semantic.test_data_operation_provider_profiles import _facts

SOURCE = "a" * 64
RELEASE = "release:literal-native-compiler"


def _install(connection):
    program = compiler_native_sql(get_metadata(), subject_scopes=subject_scope_values())
    digest = sha256(program.encode()).hexdigest()
    execute_native_sql(
        connection,
        program.replace("__DDO_SOURCE_DIGEST__", SOURCE).replace("__DDO_LOWERING_DIGEST__", digest),
    )
    return digest


def _archive(connection, *, binding=None, mutation=None, provider=None):
    kind = "primitive:string"
    role = dict(name="result", direction="output", kind=kind)
    operation = dict(
        semantic_id="compiler:literal",
        subject="literal-subject",
        replicate_policy="deterministic-single-result",
        roles=[role],
        binding="literal-binding",
        behavior="literal-implementation",
        profile="deterministic",
        support_policy={},
        coverage={},
        outcomes=[],
        state_dimensions=[],
        transitions=[],
        effects=[],
        capabilities={},
        assets=[],
    )
    archive = dict(
        subject_definitions=[dict(semantic_id="literal-subject", scope="invocation")],
        kinds=[dict(semantic_id=kind, facts={"json": {"universe": "ordinary"}})],
        identities=[
            dict(owner=kind, domain="kind", key="kind:literal-string"),
            *(
                dict(owner=operation["semantic_id"], domain=domain, key=domain + ":literal")
                for domain in ("definition", "eligibility", "recipe")
            ),
        ],
        operations=[operation],
        bindings=[
            dict(
                semantic_id="literal-binding", expression=binding or dict(operator="scan", roles=[])
            )
        ],
    )
    support = dict(
        policy={},
        coverage={},
        outcomes=[],
        replicate_policy="deterministic-single-result",
        state_dimensions=[],
        transitions=[],
        effects=[],
        capabilities={},
        provenance="value_substitution",
        assets=[],
        numerical_policy=None,
        result_fields={},
    )
    if provider is not None:
        profile, source = provider
        assets = [
            dict(
                reference="provider:profile",
                contract=source.name,
                role="provider-inference-profile",
                content_digest=source.digest,
            )
        ]
        operation["assets"] = assets
        support["assets"] = assets
        support["provider_profile"] = {**profile, "contract": source.name, "sha256": source.digest}
    projected_operation = dict(
        operation_id=operation["semantic_id"],
        subject_definition=operation["subject"],
        recipe="recipe:literal",
        profile="deterministic",
        implementation_revision="literal-implementation",
        input_roles=[],
        output_roles=[
            {**role, "kind_contract": "kind:literal-string", "identity_requirements": []}
        ],
        support_contract=support,
        binding=archive["bindings"][0]["expression"],
        definition="definition:literal",
        eligibility="eligibility:literal",
    )
    if mutation == "subject":
        archive["subject_definitions"][0]["scope"] = "unknown-scope"
    if mutation == "projection":
        projected_operation["profile"] = "forged"
    model_bytes = canonical_bytes(archive)
    payload = dict(
        model_digest=sha256(model_bytes).hexdigest(),
        native_digest=SOURCE,
        kinds=[
            dict(
                kind_contract="kind:literal-string",
                kind=kind,
                body_schema={"type": "string"},
                meaning_schema={"type": "array"},
                member_schema={"not": {}},
                member_contracts=[],
                families=[],
                universe="ordinary",
            )
        ],
        operations=[projected_operation],
    )
    release = get_metadata().tables["sem.release"]
    connection.execute(
        insert(release).values(
            release_id=RELEASE,
            content_digest=sha256(b"literal").hexdigest(),
            profile="semantic-2",
            prepared_bytes=b"literal",
            manifest_bytes=b"{}",
        )
    )
    artifacts = get_metadata().tables["sem.artifact"]
    for name, content in (
        ("data_operations.json", model_bytes),
        ("data_operation_native_definitions.json", canonical_bytes(payload)),
    ):
        connection.execute(
            insert(artifacts).values(
                release_id=RELEASE,
                artifact_name=name,
                media_type="application/json",
                content=content,
                content_digest=sha256(content).hexdigest(),
            )
        )
    if provider is not None:
        _, source = provider
        connection.execute(
            insert(get_metadata().tables["sem.input"]).values(
                release_id=RELEASE,
                input_kind="dependency",
                input_name="data-operations/contracts/" + source.name,
                content=source.content,
                content_digest=source.digest,
            )
        )
    return {**payload, "release_id": RELEASE}, archive


def _admit(connection, payload):
    return connection.scalar(
        text("SELECT sem.admit_data_operation_definitions(CAST(:payload AS jsonb))"),
        {"payload": canonical_bytes(payload).decode()},
    )


def test_current_native_compiler_lowers_exact_literal_archive_and_replays(native_rollback):
    connection = native_rollback.connection
    digest = _install(connection)
    payload, _ = _archive(connection)
    expected = dict(release_id=RELEASE, model_digest=payload["model_digest"])
    assert _admit(connection, payload) == expected
    assert _admit(connection, payload) == expected
    retained = (
        connection.execute(
            select(get_metadata().tables["sem.data_operation_definition"]).where(
                get_metadata().tables["sem.data_operation_definition"].c.release_id == RELEASE
            )
        )
        .mappings()
        .one()
    )
    assert retained["definition_identity"] == "definition:literal"
    assert retained["eligibility_identity"] == "eligibility:literal"
    assert retained["binding_expression"] == {"operator": "scan", "roles": []}
    assert retained["quantified"] is False
    assert retained["dependencies"] == {"required": [], "potential": []}
    assert retained["validity_family"] is None and retained["command_class"] is None
    assert (
        connection.scalar(
            text(
                "SELECT lowering_digest FROM sem.data_operation_release WHERE release_id=:release"
            ),
            {"release": RELEASE},
        )
        == digest
    )
    assert (
        connection.scalar(text("SELECT sem.data_operation_native_descriptor()->>'source_digest'"))
        == SOURCE
    )


@pytest.mark.parametrize("mutation", ["native", "projection", "archive", "subject", "stable-kind"])
def test_native_compiler_refuses_changed_evidence_without_partial_facts(native_rollback, mutation):
    connection = native_rollback.connection
    _install(connection)
    payload, _ = _archive(connection, mutation=mutation)
    if mutation == "native":
        payload["native_digest"] = "b" * 64
    elif mutation == "archive":
        payload["model_digest"] = "c" * 64
    elif mutation == "stable-kind":
        wrong = {**payload["kinds"][0], "body_schema": {"type": "integer"}}
        connection.execute(insert(get_metadata().tables["sem.data_kind_contract"]).values(**wrong))
    expected_error = {
        "native": "native source correspondence mismatch",
        "projection": "native definition projection disagrees with archived operation facts",
        "archive": "effective operation archive is absent or differs",
        "subject": "release subject definitions are unavailable or invalid",
        "stable-kind": "kind contract changed under stable identity",
    }[mutation]
    with pytest.raises(DBAPIError, match=expected_error), connection.begin_nested():
        _admit(connection, payload)
    assert (
        connection.scalar(
            text("SELECT count(*) FROM sem.data_operation_definition WHERE release_id=:release"),
            {"release": RELEASE},
        )
        == 0
    )


def test_native_provider_attestation_keeps_semantic_and_execution_profiles_distinct(
    native_rollback,
):
    connection = native_rollback.connection
    _install(connection)
    profile, original, _, _ = _facts()
    _, moved, _, _ = _facts(threads=16)

    def check(attestation):
        connection.execute(
            text(
                "SELECT sem.ddo_validate_provider_attestation(CAST(:attestation AS jsonb),CAST(:profile AS jsonb))"
            ),
            {
                "attestation": canonical_bytes(attestation).decode(),
                "profile": canonical_bytes(profile).decode(),
            },
        )

    check(original)
    check(moved)
    wrong = _facts(model="model:B")[1]
    with pytest.raises(DBAPIError, match="semantic subset differs"), connection.begin_nested():
        check({**wrong, "identity": profile["identity"], "meaning": profile["meaning"]})
    with pytest.raises(DBAPIError, match="attestation differs"), connection.begin_nested():
        check({**original, "execution_identity": "execution-profile:forged"})


def test_native_kind_input_closure_keeps_only_complete_concrete_descendants(native_rollback):
    connection = native_rollback.connection
    _install(connection)
    archive = dict(
        kinds=[
            dict(semantic_id=name, facts={"json": {"abstract": abstract}}, complete=complete)
            for name, abstract, complete in (
                ("base", True, True),
                ("left", False, True),
                ("right", False, False),
                ("leaf", False, True),
            )
        ],
        edges=[
            dict(source=child, target=parent, relation="inherits")
            for child, parent in (("left", "base"), ("right", "base"), ("leaf", "left"))
        ],
        identities=[
            dict(owner=name, domain="kind", key="kind:" + name)
            for name in ("base", "left", "right", "leaf")
        ],
    )
    assert connection.scalar(
        text("SELECT sem.ddo_input_kind_contracts(CAST(:model AS jsonb),'base')"),
        {"model": canonical_bytes(archive).decode()},
    ) == ["kind:leaf", "kind:left"]


@pytest.mark.parametrize("change", ["none", "digest", "canonical", "identity"])
def test_native_provider_profile_authenticates_exact_canonical_asset(native_rollback, change):
    import json

    connection = native_rollback.connection
    _install(connection)
    _archive(connection)
    profile, _, source, _ = _facts()
    if change == "identity":
        profile = {**profile, "identity": "inference:forged"}
    content = (
        json.dumps(profile, indent=2).encode()
        if change == "canonical"
        else canonical_bytes(profile)
    )
    digest = sha256(content).hexdigest()
    connection.execute(
        insert(get_metadata().tables["sem.input"]).values(
            release_id=RELEASE,
            input_kind="dependency",
            input_name="data-operations/contracts/" + source.name,
            content=content,
            content_digest=digest,
        )
    )
    operation = {
        "assets": [
            dict(
                role="provider-inference-profile",
                contract=source.name,
                content_digest="f" * 64 if change == "digest" else digest,
            )
        ]
    }

    def read():
        return connection.scalar(
            text("SELECT sem.ddo_provider_profile(:release,CAST(:operation AS jsonb))"),
            {"release": RELEASE, "operation": canonical_bytes(operation).decode()},
        )

    if change == "none":
        assert read() == {**profile, "contract": source.name, "sha256": digest}
    else:
        with (
            pytest.raises(
                DBAPIError,
                match="captured digest differs"
                if change == "digest"
                else "canonical meaning differs",
            ),
            connection.begin_nested(),
        ):
            read()
    assert (
        connection.scalar(
            text("SELECT sem.ddo_provider_profile(:release,'{\"assets\":[]}'::jsonb)"),
            {"release": RELEASE},
        )
        is None
    )


def test_native_relower_requires_finalization_and_retains_admitted_immutable_facts(native_rollback):
    connection = native_rollback.connection
    digest = _install(connection)
    payload, _ = _archive(
        connection, binding={"operator": "forall", "children": [{"operator": "scan", "roles": []}]}
    )
    _admit(connection, payload)
    assert (
        connection.scalar(
            text("SELECT quantified FROM sem.data_operation_definition WHERE release_id=:release"),
            {"release": RELEASE},
        )
        is True
    )
    with pytest.raises(DBAPIError, match="already admitted finalized"), connection.begin_nested():
        connection.execute(
            text("SELECT sem.relower_admitted_data_operation_release(:release)"),
            {"release": RELEASE},
        )
    connection.execute(
        insert(get_metadata().tables["sem.release_finalization"]).values(
            release_id=RELEASE, content_digest=sha256(b"literal").hexdigest()
        )
    )
    expected = {"release_id": RELEASE, "model_digest": payload["model_digest"]}
    with pytest.raises(DBAPIError, match="immutable semantic content"), connection.begin_nested():
        connection.scalar(
            text("SELECT sem.relower_admitted_data_operation_release(:release)"),
            {"release": RELEASE},
        )
    # Model an authenticated forward DATA step's bounded retirement of these
    # exact intrinsic guards. The savepoint rolls back both DDL and data, so
    # normal immutable admission remains protected after this control.
    with connection.begin_nested() as data_step:
        for relation in (
            "sem.data_operation_definition",
            "sem.data_operation_release",
            "sem.runtime_binding",
        ):
            connection.exec_driver_sql(
                "ALTER TABLE " + relation + " DISABLE TRIGGER semantic_immutable"
            )
        assert (
            connection.scalar(
                text("SELECT sem.relower_admitted_data_operation_release(:release)"),
                {"release": RELEASE},
            )
            == expected
        )
        assert (
            connection.scalar(
                text(
                    "SELECT lowering_digest FROM sem.data_operation_release WHERE release_id=:release"
                ),
                {"release": RELEASE},
            )
            == digest
        )
        data_step.rollback()
    with pytest.raises(DBAPIError, match="immutable semantic content"), connection.begin_nested():
        connection.execute(
            text(
                "UPDATE sem.data_operation_definition SET recipe='recipe:forged' WHERE release_id=:release"
            ),
            {"release": RELEASE},
        )
    assert (
        connection.scalar(
            text("SELECT recipe FROM sem.data_operation_definition WHERE release_id=:release"),
            {"release": RELEASE},
        )
        == "recipe:literal"
    )


@pytest.mark.parametrize("change", ["none", "version", "profile", "attestation"])
def test_native_runtime_provider_requires_its_captured_operation_and_attestation(
    native_rollback, change
):
    connection = native_rollback.connection
    _install(connection)
    profile, attestation, source, _ = _facts()
    payload, _ = _archive(connection, provider=(profile, source))
    _admit(connection, payload)
    retained_profile = {**profile, "contract": source.name, "sha256": source.digest}
    if change == "profile":
        retained_profile = {**retained_profile, "identity": "inference:forged"}
    if change == "attestation":
        attestation = {**attestation, "execution_identity": "execution-profile:forged"}
    manifest = dict(
        version="wrong-version" if change == "version" else "data-operation-runtime-binding-v2",
        execution_profile=attestation["execution_identity"],
        provider_profiles={
            "compiler:literal": dict(profile=retained_profile, attestation=attestation)
        },
    )
    connection.execute(
        insert(get_metadata().tables["sem.runtime_binding"]).values(
            release_id=RELEASE,
            runtime_id="runtime:literal",
            manifest_bytes=canonical_bytes(manifest),
            execution_profile=attestation["execution_identity"],
            archive_bytes=b"literal-runtime",
        )
    )

    def require():
        return connection.scalar(
            text(
                "SELECT ops.ddo_require_provider_profile(:release,'compiler:literal','runtime:literal')"
            ),
            {"release": RELEASE},
        )

    if change == "none":
        assert require() == profile["identity"]
    else:
        with (
            pytest.raises(
                DBAPIError,
                match="attestation differs"
                if change == "attestation"
                else "authentic producing provider profile",
            ),
            connection.begin_nested(),
        ):
            require()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_stale_lowering_refuses_reads_and_demands_until_existing_release_is_relowered(ddo_kernel):
    from native_refusals import native_refusal

    from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )
    from semantic.data_operation_declaration_support import root_subject

    release = ddo_kernel["prepared"].release_id
    with ddo_kernel["engine"].connect() as connection:
        transaction = connection.begin()
        try:
            storage = DataOperationStorage(connection)

            def register(subject):
                intent = freeze_demand(
                    ddo_kernel["model"],
                    roots=(root_subject(subject=subject, source="source:test", scope={"page": 1}),),
                    targets=("urn:ddo-test:source",),
                    inference="inference:test",
                    execution_profile="execution:test",
                )
                return DemandPlanner(ddo_kernel["model"], storage).register(
                    intent, project="ddo-test", release=release, runtime=ddo_kernel["runtime"]
                )

            digest_query = text(
                "SELECT lowering_digest FROM sem.data_operation_release WHERE release_id=:release"
            )
            params = {"release": release}
            original = connection.scalar(digest_query, params)
            assert original
            assert register("lowering:before")["demand_id"]
            assert (
                storage.inspect_data_operation_release({"release_id": release})["release_id"]
                == release
            )
            for relation in (
                "sem.data_operation_definition",
                "sem.data_operation_release",
                "sem.runtime_binding",
            ):
                connection.exec_driver_sql(
                    "ALTER TABLE " + relation + " DISABLE TRIGGER semantic_immutable"
                )
            connection.execute(
                text(
                    "UPDATE sem.data_operation_release SET lowering_digest='authored-stale-lowering' WHERE release_id=:release"
                ),
                params,
            )
            for relation in (
                "sem.data_operation_definition",
                "sem.data_operation_release",
                "sem.runtime_binding",
            ):
                connection.exec_driver_sql(
                    "ALTER TABLE " + relation + " ENABLE TRIGGER semantic_immutable"
                )
            with connection.begin_nested() as savepoint:
                with native_refusal(
                    "23514", message="read-only inspection native source correspondence differs"
                ):
                    storage.inspect_data_operation_release({"release_id": release})
                savepoint.rollback()
            with connection.begin_nested() as savepoint:
                with native_refusal(
                    "P0001", message="demand differs from authenticated effective model/selection"
                ):
                    register("lowering:stale")
                savepoint.rollback()
            projection = read_native_definition_projection(
                ddo_kernel["prepared"], model=ddo_kernel["model"]
            )
            payload = canonical_bytes({**projection, "release_id": release}).decode()
            with connection.begin_nested() as savepoint:
                with native_refusal(
                    "P0001", message="release facts changed under admitted release"
                ):
                    connection.execute(
                        text(
                            "SELECT sem.admit_data_operation_definitions(CAST(:payload AS jsonb))"
                        ),
                        {"payload": payload},
                    )
                savepoint.rollback()
            assert connection.scalar(digest_query, params) == "authored-stale-lowering"
            for relation in (
                "sem.data_operation_definition",
                "sem.data_operation_release",
                "sem.runtime_binding",
            ):
                connection.exec_driver_sql(
                    "ALTER TABLE " + relation + " DISABLE TRIGGER semantic_immutable"
                )
            repaired = connection.scalar(
                text("SELECT sem.relower_admitted_data_operation_release(:release)"), params
            )
            assert repaired["release_id"] == release
            assert connection.scalar(digest_query, params) == original
            for relation in (
                "sem.data_operation_definition",
                "sem.data_operation_release",
                "sem.runtime_binding",
            ):
                connection.exec_driver_sql(
                    "ALTER TABLE " + relation + " ENABLE TRIGGER semantic_immutable"
                )
            assert (
                storage.inspect_data_operation_release({"release_id": release})["release_id"]
                == release
            )
            assert register("lowering:after")["demand_id"]
        finally:
            transaction.rollback()
