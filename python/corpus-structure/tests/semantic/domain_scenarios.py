"""Explicit synthetic semantic scenarios used by domain operation tests."""

from collections.abc import Sequence
from dataclasses import replace
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, insert, select

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic._operation_ids import CutId, RunId
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    seal_cut,
)
from corpus_structure.semantic.proposals import (
    SEMANTIC_AGENT_VERSION,
    locate_proposal,
    native_source_frame,
    proposal_inputs,
)
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceRow,
    PublicationBatch,
    SelectionRow,
    SupportRow,
    ValueRow,
)
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import PreparedRelease


class DomainFixtureConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    math: dict[str, Any] | None = None
    variant: str | None = None


def build_domain_case(
    admin: Engine,
    writer: Engine,
    path: Path,
    *,
    rules: bytes = b"rules: []\n",
    graph: bool = False,
    duplicate: bool = False,
    formulas: Sequence[str] = (),
    known: bool = False,
    local_known: bool = False,
    input_noise: bool = False,
    nary: bool = False,
    broken: bool = False,
    claim_chain: bool = False,
    cycle: bool = False,
    condition: dict[str, Any] | None = None,
    report_count: int = 1,
    global_person_identity: bool = False,
    authored_alternative: bool = False,
    integer_alias: bool = False,
    math: dict[str, Any] | None = None,
    second_math: dict[str, Any] | None = None,
    statement_packets: str | None = None,
    attribute_assertions: bool = False,
    incomplete_key: bool = False,
    isolated_entity: bool = False,
    membership_subtype: bool = False,
    unselected_report: bool = False,
) -> tuple[PreparedRelease, RunId, CutId]:
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema: dict[str, Any] = {
        "id": "https://example.org/domain",
        "name": "domain",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Person": {"is_a": "Entity", "attributes": {"name": {"range": "string"}}}},
    }
    if incomplete_key:
        schema["classes"]["Person"]["attributes"]["serial"] = {"required": True}
        schema["classes"]["Person"]["unique_keys"] = {
            "serial_key": {"unique_key_slots": ["serial"]}
        }
    if input_noise:
        schema["classes"]["Person"]["attributes"]["note"] = {"range": "string"}
    if integer_alias:
        schema["types"] = {"SmallCount": {"typeof": "integer"}}
        schema["classes"]["Person"]["attributes"]["name"] = {
            "range": "SmallCount",
            "minimum_value": 0,
        }
    if global_person_identity:
        schema["classes"]["Person"]["annotations"] = {"cs:scope": "global", "cs:case": "preserve"}
    if known:
        schema["classes"]["Person"]["unique_keys"] = {"by_name": {"unique_key_slots": ["name"]}}
    if graph:
        schema["classes"]["Person"]["attributes"].update(
            {
                "parent": {"range": "Person", "inverse": "child", "multivalued": True},
                "child": {"range": "Person", "multivalued": True},
            }
        )
    if membership_subtype:
        schema["classes"]["PersonSubtype"] = {"is_a": "Person"}
    if formulas:
        schema["classes"]["Formula"] = {
            "is_a": "ExpressionValue",
            "attributes": {"kind": {"equals_string": "formula"}},
        }
        schema["classes"]["Person"]["attributes"]["name"] = {
            "range": "Formula",
            "inlined": True,
            "annotations": {"cs:role": "predicate", "cs:constraint_scope": "accepted_value"},
        }
    if nary:
        endpoint = "Endpoint" if broken else "Person"
        if broken:
            schema["classes"]["Endpoint"] = {
                "is_a": "Entity",
                "attributes": {"business": {"range": "string", "required": True}},
                "unique_keys": {"business_key": {"unique_key_slots": ["business"]}},
            }
        schema["classes"]["RoleEntry"] = {
            "attributes": {
                "key": {"identifier": True},
                "target": {"range": endpoint, "required": True},
                "ref": {"range": "string"},
            }
        }
        schema["classes"]["NaryValue"] = {
            "is_a": "Value",
            "attributes": {
                "kind": {"equals_string": "nary"},
                "endpoint": {"range": endpoint, "required": True},
                "ref": {"range": "string"},
                "roles": {"range": "RoleEntry", "inlined": True, "multivalued": True},
            },
        }
        schema["classes"]["Person"]["attributes"]["relation"] = {
            "range": "NaryValue",
            "inlined": True,
        }
    deps = domain_rule_inputs(ResolvedDependencies(), rules)
    bundle = SourceBundle(
        "domain",
        (
            SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )
    bundle = observation_inputs(proposal_inputs(bundle, deps))
    bundle, deps = analytical_inputs(bundle, deps)
    from corpus_structure.semantic.composed import composed_dependencies

    from .method_dimensions_support import fixture_execution_inputs

    deps = composed_dependencies(
        deps, fixture_execution_inputs("pdf.controlled-source", "coverage.witness")
    )
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, deps, profile)
    with admin.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="source", project_id="p", release_id=prepared.release_id
            )
        )
    if known:
        from corpus_structure.semantic.consolidation import SourceItem, assemble
        from corpus_structure.semantic.publication import EvidenceRow, SelectionRow, publish_batch

        evidence = (EvidenceRow("initial-evidence", "prior-source", "prior#unit", "fixture", "1"),)
        initial = assemble(
            prepared,
            "source",
            "input-knowledge",
            tuple(
                SourceItem(
                    "known:alice",
                    "Person",
                    name,
                    value,
                    {"modality": "asserted", "polarity": True},
                    "prior-source",
                    name,
                    "stated",
                    evidence,
                )
                for name, value in [
                    ("id", "known:alice"),
                    ("name", "Alice"),
                    *([("note", "irrelevant")] if input_noise else []),
                ]
            ),
        )
        publish_batch(
            writer,
            replace(
                initial, selection=tuple(SelectionRow(f.fact_id) for f in initial.fact)
            ).bind_preparation(prepared),
        )
    double_source = duplicate or statement_packets == "different"
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    paragraphs = ("Alice is here.",) * (2 if double_source else 1)
    original = write_controlled_pdf(path, paragraphs)
    with writer.begin() as conn:
        document = register_document(
            conn,
            project_id="p",
            source_uri="page.html",
            original_path=str(path),
            original=original,
            metadata={"page": "page"},
            mime="application/pdf",
        )
        document_key = conn.execute(
            select(table("kb.document").c.key).where(table("kb.document").c.id == document)
        ).scalar_one()
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "source", 1 if known else 0, b"{}"),
            kind="full",
            options={"corpus": {"documents": [document_key]}},
            code_commit="test",
        )
    views = publish_controlled_pdf_views(
        writer,
        prepared=prepared,
        run_id=run,
        document_id=document,
        original=original,
        paragraphs=paragraphs,
    )
    with writer.begin() as conn:
        view = views[0]
        cid = record_method(
            conn,
            SimpleNamespace(
                name="agent.opus",
                version=SEMANTIC_AGENT_VERSION,
                family="agent",
                tier="agent",
                confidence_source="agent",
                unit_type="source_view",
                Config=DomainFixtureConfig,
            ),
            "extract",
            {"math": math} if math is not None else {},
            "config",
            prepared=prepared,
        )
        sentence_offsets = (("s1", 0, 14),) + ((("s2", 15, 29),) if duplicate else ())
        frame = native_source_frame(view, sentence_offsets)
        from corpus_structure.semantic.proposals import proposal_packet

        packet = proposal_packet(prepared, frame, guideline="", configuration={})
        task = create_task(
            conn,
            run_id=run,
            config_id=cid,
            stage="propose",
            unit_type="source_view",
            unit_id=view.ref.id,
            unit_key=view.ref.key,
            input_hash="input",
            packet_hash=packet.hash,
            agent=True,
        )
        lease = claim_tasks(conn, run_id=run, config_id=cid, holder="worker", agent=True)[0]
        from corpus_structure.semantic.source_frames import capture_source_frame

        capture_source_frame(conn, task, packet)
    raw: dict[str, Any] = {
        "unit_ref": view.ref.key,
        "entities": [{"id": "person", "class_iri": "https://example.org/Person", "label": "Alice"}],
        "statements": [
            {"id": "s", "kind": "remark", "anchor": "s1" if statement_packets else view.ref.key}
        ],
        "claims": [
            {
                "id": "c",
                "subject": "person",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "statement": "s",
                "statement_role": "conclusion",
                "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
            }
        ],
        "alternatives": [],
        "unsupported": [
            {
                "id": "u",
                "kind": "uninterpreted",
                "reason": "not expressed by selected schema",
                "text": "Alice is here.",
                "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
            }
        ],
    }
    if known:
        if local_known:
            raw["entities"][0]["attributes"] = [
                {
                    "predicate": "https://example.org/name",
                    "value": {"kind": "text", "text": "Alice"},
                    "qualification": {"modality": "asserted", "polarity": True},
                    "establishment": "stated",
                    "evidence": [{"sentence": "s1", "quote": "Alice is here.", "role": "primary"}],
                }
            ]
        else:
            raw["entities"] = []
            raw["claims"][0]["subject"] = "known:alice"
    if graph:
        raw["entities"].append(
            {"id": "other", "class_iri": "https://example.org/Person", "label": "Bob"}
        )
        raw["claims"].append(
            {
                **raw["claims"][0],
                "id": "relation",
                "predicate": "https://example.org/parent",
                "object": {"kind": "entity", "target": "other"},
            }
        )
    if isolated_entity:
        raw["entities"].append(
            {"id": "isolated", "class_iri": "https://example.org/Person", "label": "Isolate"}
        )
    if duplicate:
        raw["statements"].append({"id": "s2", "kind": "theorem", "anchor": "s2"})
        raw["claims"].append({**raw["claims"][0], "id": "duplicate", "statement": "s2"})
    if formulas:
        base = raw["claims"][0]
        raw["claims"] = [
            {
                **base,
                "id": "formula" + str(i),
                "object": {"kind": "formula", "language": "latex", "expression": value},
            }
            for i, value in enumerate(formulas)
        ]
    if nary:
        raw["entities"].append(
            {
                "id": "other",
                "class_iri": "https://example.org/" + ("Endpoint" if broken else "Person"),
                "reference": {"description": "outside unresolved person"},
            }
        )
        raw["claims"][0].update(
            predicate="https://example.org/relation",
            object={
                "kind": "nary",
                "endpoint": "other",
                "ref": "other",
                "roles": {"r": {"key": "r", "target": "other", "ref": "other"}},
            },
        )
    if claim_chain:
        base = raw["claims"][0]
        raw["claims"] = [
            {**base, "id": "p1"},
            {**base, "id": "p2"},
            {
                **base,
                "id": "d1",
                "qualification": {
                    **base["qualification"],
                    "condition": {"kind": "claim", "ref": "p1"},
                },
            },
            {
                **base,
                "id": "d2",
                "qualification": {
                    **base["qualification"],
                    "condition": {"kind": "claim", "ref": "p2"},
                },
            },
        ]
    if cycle:
        base = raw["claims"][0]
        raw["claims"] = [
            {
                **base,
                "id": "a",
                "qualification": {
                    **base["qualification"],
                    "condition": {"kind": "claim", "ref": "b"},
                },
            },
            {
                **base,
                "id": "b",
                "qualification": {
                    **base["qualification"],
                    "condition": {"kind": "claim", "ref": "a"},
                },
            },
        ]
    if integer_alias:
        raw["claims"][0]["object"] = {"kind": "number", "number": 4}
    if report_count == 2 and formulas:
        raw["claims"][0]["object"]["bindings"] = [{"symbol": "x", "kind": "free"}]
    if authored_alternative:
        raw["alternatives"] = [
            {
                "id": "choice",
                "members": [c["id"] for c in raw["claims"]],
                "faithful": True,
                "reason": "source explicitly contrasts these possibilities",
            }
        ]
    if condition is not None:
        for claim in raw["claims"]:
            claim["qualification"] = {**claim["qualification"], "condition": condition}
    if attribute_assertions:
        raw["entities"][0]["attributes"] = [
            {
                "predicate": "https://example.org/name",
                "value": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "supposed", "polarity": False},
                "establishment": "agent_asserted",
                "evidence": [
                    {"sentence": "s1", "quote": "Alice is here.", "role": "primary"},
                    {"sentence": "s1", "quote": "Alice is here.", "role": "supporting"},
                ],
            }
        ]
    located = (
        locate_proposal(
            prepared, raw, frame, known_classes={"known:alice": ("https://example.org/Person",)}
        )
        if known
        else locate_proposal(prepared, raw, frame)
    )
    stored = located.stored.model_dump(mode="python")
    if statement_packets:
        # Reproduce reports captured before anchor normalization, without editing stored rows.
        stored["statements"][0]["anchor"] = "s1"
    with writer.begin() as conn:
        complete_task(
            conn,
            task_id=task,
            attempt=lease.attempt,
            holder="worker",
            prepared=prepared,
            observations=[
                {
                    "payload_definition": "AgentStoredBatch",
                    "item_key": "proposal",
                    "kind": "claim_proposal",
                    "payload": stored,
                    "source_view_id": view.ref.id,
                }
            ],
        )
        if report_count == 2:
            import copy

            second = copy.deepcopy(raw)
            if formulas:
                second["claims"][0]["object"]["bindings"] = [{"symbol": "x", "kind": "constant"}]
            second_view = views[1] if statement_packets == "different" else view
            second_unit = second_view.ref.key
            second["unit_ref"] = second_unit
            if statement_packets == "different":
                second["statements"][0]["kind"] = "theorem"
            second_frame = native_source_frame(second_view, (("s1", 0, 14),))
            second_packet = proposal_packet(prepared, second_frame, guideline="", configuration={})
            second_located = locate_proposal(prepared, second, second_frame)
            second_config = record_method(
                conn,
                SimpleNamespace(
                    name="agent.opus",
                    version=SEMANTIC_AGENT_VERSION,
                    family="agent",
                    tier="agent",
                    confidence_source="agent",
                    unit_type="source_view",
                    Config=DomainFixtureConfig,
                ),
                "extract",
                {
                    "variant": "second",
                    **(
                        {"math": second_math if second_math is not None else math}
                        if second_math is not None or math is not None
                        else {}
                    ),
                },
                "config-second",
                prepared=prepared,
            )
            second_task = create_task(
                conn,
                run_id=run,
                config_id=second_config,
                stage="propose",
                unit_type="source_view",
                unit_id=second_view.ref.id,
                unit_key=second_unit,
                input_hash="input-second",
                packet_hash=second_packet.hash,
                agent=True,
            )
            capture_source_frame(conn, second_task, second_packet)
            second_lease = claim_tasks(
                conn, run_id=run, config_id=second_config, holder="worker", agent=True
            )[0]
            second_stored = second_located.stored.model_dump(mode="python")
            if statement_packets:
                second_stored["statements"][0]["anchor"] = "s1"
            complete_task(
                conn,
                task_id=second_task,
                attempt=second_lease.attempt,
                holder="worker",
                prepared=prepared,
                observations=[
                    {
                        "payload_definition": "AgentStoredBatch",
                        "item_key": "proposal",
                        "kind": "claim_proposal",
                        "payload": second_stored,
                        "source_view_id": second_view.ref.id,
                    }
                ],
            )
        cut = seal_cut(conn, run, "final", final=True)
    if unselected_report:
        # A real protected report in another run is deliberately outside this cut.
        # Reuse the admitted model/configuration, not forged observation storage.
        foreign_original = write_controlled_pdf(
            path.with_name("outside-cut.pdf"), ("Alice is here.", "Outside cut report.")
        )
        with writer.begin() as conn:
            foreign_document = register_document(
                conn,
                project_id="p",
                source_uri="outside-cut.pdf",
                original_path=str(path.with_name("outside-cut.pdf")),
                original=foreign_original,
                metadata={"page": "outside"},
                mime="application/pdf",
            )
            foreign_document_key = conn.execute(
                select(table("kb.document").c.key).where(
                    table("kb.document").c.id == foreign_document
                )
            ).scalar_one()
            foreign_run = create_run(
                conn,
                project_id="p",
                binding=OperationBinding(prepared.release_id, "source", 1 if known else 0, b"{}"),
                kind="full",
                options={"corpus": {"documents": [foreign_document_key]}},
                code_commit="test",
            )
        (foreign_view,) = publish_controlled_pdf_views(
            writer,
            prepared=prepared,
            run_id=foreign_run,
            document_id=foreign_document,
            original=foreign_original,
            paragraphs=("Alice is here.",),
        )
        foreign_frame = native_source_frame(foreign_view, (("s1", 0, 14),))
        foreign_packet = proposal_packet(prepared, foreign_frame, guideline="", configuration={})
        foreign_raw = {
            **raw,
            "unit_ref": foreign_view.ref.key,
            "statements": [
                {**statement, "anchor": foreign_view.ref.key} for statement in raw["statements"]
            ],
        }
        foreign_stored = locate_proposal(prepared, foreign_raw, foreign_frame).stored.model_dump(
            mode="python"
        )
        with writer.begin() as conn:
            foreign_task = create_task(
                conn,
                run_id=foreign_run,
                config_id=cid,
                stage="propose",
                unit_type="source_view",
                unit_id=foreign_view.ref.id,
                unit_key=foreign_view.ref.key,
                input_hash="outside-cut",
                packet_hash=foreign_packet.hash,
                agent=True,
            )
            capture_source_frame(conn, foreign_task, foreign_packet)
            foreign_lease = claim_tasks(
                conn, run_id=foreign_run, config_id=cid, holder="worker", agent=True
            )[0]
            complete_task(
                conn,
                task_id=foreign_task,
                attempt=foreign_lease.attempt,
                holder="worker",
                prepared=prepared,
                observations=[
                    {
                        "payload_definition": "AgentStoredBatch",
                        "item_key": "proposal",
                        "kind": "claim_proposal",
                        "payload": foreign_stored,
                        "source_view_id": foreign_view.ref.id,
                    }
                ],
            )
    return prepared, run, cut


Z = "realization:test"
C = "https://example/Thing"
P = "https://example/label"


@cache
def fixture_model(
    scope: Literal["shape", "accepted_value", "occurrence", "context"] = "accepted_value",
    unique=False,
    label_range="string",
    inlined=False,
    record_target=False,
    minimum=None,
    maximum=None,
    qualification=False,
    conditional=False,
    composed=True,
):
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    label: dict[str, Any] = {
        "range": label_range,
        "inlined": inlined,
        "annotations": {"cs:constraint_scope": scope, "cs:case": "casefold"},
    }
    if minimum is not None:
        label["minimum_value"] = minimum
    if maximum is not None:
        label["maximum_value"] = maximum
    thing: dict[str, Any] = {"attributes": {"label": label}}
    if unique:
        thing["unique_keys"] = {"label_identity": {"unique_key_slots": ["label"]}}
    schema: dict[str, Any] = {
        "id": "https://example/publication-fixture",
        "name": "publication",
        "prefixes": {"ex": "https://example/"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "http://www.w3.org/2001/XMLSchema#string"},
            "decimal": {"base": "Decimal", "uri": "http://www.w3.org/2001/XMLSchema#decimal"},
            "boolean": {"base": "bool", "uri": "http://www.w3.org/2001/XMLSchema#boolean"},
        },
        "classes": {
            "Thing": thing,
            "Record": {
                "attributes": {
                    "target": {
                        "range": "Thing",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    }
                }
            }
            if record_target
            else {},
            "ExpectedRecord": {},
            "OtherRecord": {},
            "Qualification": {
                "attributes": {
                    "modality": {
                        "range": "string",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    },
                    "polarity": {
                        "range": "boolean",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    },
                    "attribution": {
                        "range": "string",
                        "annotations": {
                            "cs:key_role": "provenance",
                            "cs:constraint_scope": "shape",
                        },
                    },
                    "score": {
                        "range": "decimal",
                        "minimum_value": 0,
                        "annotations": {"cs:constraint_scope": "accepted_value"},
                    },
                }
            },
        },
    }
    if conditional:
        thing["rules"] = [
            {
                "preconditions": {"slot_conditions": {"label": {"value_presence": "PRESENT"}}},
                "postconditions": {"slot_conditions": {"label": {"equals_string": "ready"}}},
            }
        ]
    if not qualification:
        del schema["classes"]["Qualification"]
    bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies

    deps = (
        composed_dependencies(ResolvedDependencies())
        if conditional or composed
        else ResolvedDependencies()
    )
    profile = PreparationProfile(
        version="semantic-2" if conditional or composed else "semantic-1", constraint_scope=scope
    )
    return bundle, prepare_release(bundle, deps, profile)


def seed(
    engine,
    *,
    scope: Literal["shape", "accepted_value", "occurrence", "context"] = "accepted_value",
    unique=False,
    **model_options,
):
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import persist_release

    bundle, prepared = fixture_model(scope, unique, **model_options)
    composed = model_options.get("conditional", False) or model_options.get("composed", True)
    deps = composed_dependencies(ResolvedDependencies()) if composed else ResolvedDependencies()
    profile = PreparationProfile(
        version="semantic-2" if composed else "semantic-1", constraint_scope=scope
    )
    with engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=Z, release_id=prepared.release_id, project_id="p"
            )
        )
    return prepared


def batch(identity="b", *, entity="e", label="Straße", selected=True, release_id):
    f = fact_key(release_id, Z, entity, P, label, {})
    o1 = occurrence_key(release_id, Z, "source", "1" + identity)
    o2 = occurrence_key(release_id, Z, "source", "2" + identity)
    return PublicationBatch(
        release_id,
        Z,
        identity,
        entity=(EntityRow(entity),),
        membership=(MembershipRow(entity, C, "source assertion"),),
        typed_value=(ValueRow("v" + identity, "string", text_value=label),),
        fact=(FactRow(f, entity, P, "v" + identity),),
        occurrence=(
            OccurrenceRow(o1, f, "source", "1" + identity, "v" + identity),
            OccurrenceRow(o2, f, "source", "2" + identity, "v" + identity),
        ),
        support=(SupportRow(f, o1), SupportRow(f, o2)),
        selection=(SelectionRow(f),) if selected else (),
        evidence=(EvidenceRow("evidence" + identity, "urn:source", "line:1", "test", "1"),),
        membership_support=(MembershipSupportRow(entity, C, "evidence" + identity),),
    )
