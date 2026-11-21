"""Real external task/native source custody for controlled, independently expected domain meaning."""

from contextlib import ExitStack, contextmanager
from datetime import date
from decimal import Decimal
from functools import partial
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.rich_queries import (
    ClaimsQuery,
    ConstructionProfileQuery,
    EntityQuery,
    FamilyProfileQuery,
    OwnershipAtQuery,
)
from semantic.record_publication_native_support import query_publication
from semantic.rich_domain_external_support import (
    SOURCE_TEXT,
    controlled_source_response,
    external_recipe,
    publish_external_report,
)


@contextmanager
def current_external_journey(admin, native_settings, tmp_path, monkeypatch, *, recipe, content):
    from evaluate.declared_record_native_support import _capture_record_policy
    from pdf_controlled_support import controlled_pdf_converter

    from corpus_structure.schema.model_change import native_model_inputs
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.target_installation import capture_target_installation
    from native_test_support import principal_engine
    from semantic.current_pdf_source_support import ROOT
    from semantic.data_operation_kernel_support import Kernel, build_kernel
    from semantic.test_target_installation_native import install_target_root

    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    preparation = tmp_path / "current-external-kernel"
    preparation.mkdir()
    with ExitStack() as resources, controlled_pdf_converter(content):
        purposes = {}

        def purpose(name):
            if name not in purposes:
                engine = principal_engine(native_settings, name, admin.url.database)
                resources.callback(engine.dispose)
                purposes[name] = engine
            return purposes[name]

        stage = build_kernel(recipe, admin, purpose("write"), preparation, purpose_engine=purpose)
        kernel = Kernel(
            admin, stage.preparation, stage.identities, recipe, SimpleNamespace(purpose=purpose)
        )
        yield _capture_record_policy(kernel, tmp_path, source_count=1)


@pytest.mark.parametrize("domain", ("statistics", "toy"))
def test_external_domain_recipe_composes_existing_sentence_and_packet_owners(tmp_path, domain):
    from semantic.data_operation_kernel_support import prepare_kernel

    prepared = prepare_kernel(external_recipe(tmp_path, domain=domain))
    assert all(item.complete for item in prepared.model.implementation_slices)
    assert {
        "segment.sentences/source-native",
        "prepare.external_extraction",
        "extract.rich_external",
        "locate.external_extraction",
        "rich.consolidate",
        "rich.admit",
    } <= {op.semantic_id for op in prepared.model.operations}
    external = prepared.model.operation("extract.rich_external")
    assert (
        external.external is not None
        and external.external.requested_actor == "controlled-domain-author"
    )


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.parametrize("case", ("T1", "T2", "T4", "toy"))
def test_native_controlled_external_source_retains_exact_statistics_meaning(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch, case
):
    from semantic.rich_domain_native_support import decimal_source_content

    with current_external_journey(
        semantic_bare_engine,
        native_settings,
        tmp_path,
        monkeypatch,
        recipe=external_recipe(tmp_path, domain="toy" if case == "toy" else "statistics"),
        content=decimal_source_content(SOURCE_TEXT[case]),
    ) as journey:
        selected, external_receipt, _report = publish_external_report(
            journey,
            journey.sources[0],
            partial(controlled_source_response, case=case),
            inference="actual-source-domain-" + case,
        )
        query = (
            ClaimsQuery(name="claims")
            if case == "toy"
            else (
                ConstructionProfileQuery(name="construction_profile", construction="LS")
                if case == "T1"
                else FamilyProfileQuery(
                    name="family_profile", family="normal" if case == "T2" else "lognormal"
                )
            )
        )
        rows = query_publication(selected, query)["rows"]
        assert rows
        occurrences = [item for row in rows for item in row["occurrences"]]
        assert occurrences
        for item in occurrences:
            original = item["original"]
            assert original["support_references"][0]["kind"] == "computation"
            assert item["evidence_count"] > 0
            if original["member_id"].startswith("claim:"):
                assert item["statement"]["member_id"] == "statement:controlled-statement"
            else:
                assert original["member_id"].startswith("entity:")
                assert item["statement"] is None
        assert (
            external_receipt["actor_assertion"] == "controlled-domain-author"
            and external_receipt["model_assertion"] is None
        )

        def entity(label):
            (row,) = query_publication(selected, EntityQuery(name="entity", key=label))["rows"]
            return row["entity"]["entity_id"]

        if case == "T1":
            assert (
                query_publication(
                    selected, EntityQuery(name="entity", class_name="DistributionFamily")
                )["rows"]
                == []
            )
            construction = next(
                row for row in rows if row["fact"]["predicate"].endswith("/construction_formula")
            )
            qualification = decode_semantic_value(construction["occurrences"][0]["qualification"])
            assert qualification["base_variable"] == entity("Z")
            assert qualification["condition"]["set"]["expression"] == "(0, \\infty)"
            assert not any(
                row["fact"]["predicate"].endswith("/member_of_construction") for row in rows
            )
        elif case == "T2":
            assert {
                (row["fact"]["subject_entity"], decode_semantic_value(row["object"]))
                for row in rows
                if row["fact"]["predicate"].endswith("/identical_parameter")
            } == {
                (entity("location"), entity("mean")),
                (entity("scale"), entity("standard_deviation")),
            }
            assert {
                row["fact"]["subject_entity"]
                for row in rows
                if row["fact"]["predicate"].endswith("/has_parameter")
            } == {entity("normal")}
        elif case == "T4":
            assert {
                (row["fact"]["subject_entity"], decode_semantic_value(row["object"]))
                for row in rows
                if row["fact"]["predicate"].endswith("/parameter_role")
            } == {(entity("sigma"), "shape")}
            derived = next(
                decode_semantic_value(row["object"])
                for row in rows
                if row["fact"]["predicate"].endswith("/derived_parameter")
            )
            assert derived["expression"] == "e^\\mu"
            assert derived["bindings"][1]["entity"] == entity("mu")
            assert not any(
                row["fact"]["predicate"].endswith("/identical_parameter") for row in rows
            )
        else:
            ownership = [row for row in rows if row["fact"]["predicate"].endswith("/owns")]
            assert len(ownership) == 3
            same = next(row for row in ownership if len(row["occurrences"]) == 2)
            assert {
                decode_semantic_value(item["qualification"])["filing_ref"]
                for item in same["occurrences"]
            } == {"A", "B"}
            assert {
                decode_semantic_value(item["qualification"])["attribution"]
                for row in ownership
                for item in row["occurrences"]
            } == {entity("source"), entity("other-source")}
            temporal = query_publication(
                selected,
                OwnershipAtQuery(name="ownership_at", asset=entity("asset"), date=date(2020, 7, 1)),
                limit=1,
            )
            assert temporal["rows"][0]["applicability"] == "unknown"
            more = query_publication(
                selected,
                OwnershipAtQuery(name="ownership_at", asset=entity("asset"), date=date(2020, 7, 1)),
                cursor=temporal["cursor"],
            )
            assert len(more["rows"]) == 3 and {row["applicability"] for row in more["rows"]} == {
                "unknown"
            }
            assert temporal["cut_id"] == more["cut_id"] and temporal["root"] == more["root"]
            nested = next(
                decode_semantic_value(row["object"])
                for row in rows
                if row["fact"]["predicate"].endswith("/inspection")
            )
            assert (nested["inspector"], nested["custodian"]) == (
                entity("inspector"),
                entity("custodian"),
            )
            assert nested["details"]["measured_quantity"] == dict(
                kind="quantity", number=Decimal("12.3400"), unit="kg", basis="dry-mass"
            )
        assert len(query_publication(selected, ClaimsQuery(name="claims"))["rows"]) >= 3
