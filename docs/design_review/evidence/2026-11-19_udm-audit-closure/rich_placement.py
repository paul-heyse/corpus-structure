"""Observe current rich views over the preserved E1-E3 statistical annotations.

This offline inquiry acquires no native standing. Its exact prepared packet and typed
located reports can be submitted through the normal external/native stage route.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import ExternalExecutorContract, SubjectContext
from corpus_structure.semantic.data_operation_support import AuthoredFactSupportReference
from corpus_structure.semantic.declared_math_products import math_operation_declarations
from corpus_structure.semantic.declared_proposal_frames import DeclaredProposalFrame
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.external_extraction import (
    external_extraction_operation_sources,
    locate_external_extraction,
    rich_external_declarations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.math_context import acquire_analysis_context_profile
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.proposals import ProposalSentence, native_address
from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
from corpus_structure.semantic.regeneration import acquire_pack
from corpus_structure.semantic.rich_consolidation import consolidate_rich_knowledge
from corpus_structure.semantic.rich_cpu_inputs import RichKernelInputs
from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
from corpus_structure.semantic.rich_knowledge_sources import (
    rich_knowledge_declarations,
    rich_knowledge_inputs,
)
from corpus_structure.semantic.rich_policy_binding import rich_policy_value
from corpus_structure.semantic.rich_relations import RichRelationKernel
from corpus_structure.semantic.source_products import native_projection_identity
from corpus_structure.semantic.types import ResolvedDependencies

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "ddo-rich-placement-bounded"
NS = "https://corpus-structure.dev/semantic/data-operation-"


def prepare():
    acquired = acquire_pack(ROOT / "domains/statistics")
    bundle, deps = rich_knowledge_inputs(
        acquired.bundle,
        ResolvedDependencies(),
        domain_rules=(ROOT / "domains/statistics/schema/rules.yaml").read_bytes(),
        core_rules=(ROOT / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    sources = combine_primary_sources(
        rich_knowledge_operation_sources(), external_extraction_operation_sources()
    )
    deps = data_operation_dependencies(
        deps,
        (
            *rich_knowledge_declarations(deps),
            record_policy_kind_declarations(),
            math_operation_declarations(),
            rich_external_declarations(
                ExternalExecutorContract(
                    "external-executor-v1",
                    "Preserve independently authored E1-E3 statistical source annotations.",
                    "preserved-reference-author",
                    None,
                    "declared-inputs-only",
                )
            ),
        ),
        sources,
    )
    prepared = prepare_release(bundle, deps)
    return prepared, bound_data_operation_model(prepared)


def packet(unit):
    path = ROOT / "domains/statistics/reference" / unit / "packet.md"
    sentences = re.findall(r"^\[(s\d+)\] (.*)$", path.read_text(), re.MULTILINE)
    text = "\n".join(value for _, value in sentences)
    pieces = []
    offset = 0
    for index, (_, value) in enumerate(sentences):
        if index:
            pieces.append(dict(kind="synthetic_separator", start=offset - 1, end=offset))
        pieces.append(
            dict(
                kind="native_text",
                item_ref=f"#/texts/{index}",
                source_field="text",
                start=offset,
                end=offset + len(value),
            )
        )
        offset += len(value) + 1
    from corpus_structure.semantic.original_documents import original_document_subject

    document = "preserved-reference:" + sha256(path.read_bytes()).hexdigest()
    source = dict(
        document=document,
        document_subject=original_document_subject(document),
        projection="pending",
        section_pointer="#/groups/0",
        membership="descendants",
    )
    items = [dict(self_ref=f"#/texts/{index}") for index in range(len(sentences))]
    projection = native_projection_identity(text, pieces, items, [], [])
    source["projection"] = projection
    selectors = [dict(projection=projection)]
    body = dict(
        source=source,
        text=text,
        pieces=pieces,
        items=items,
        ancestors=[],
        recognition=[],
        selectors=selectors,
    )
    pin = dict(
        format="declared-native-source-v1",
        source=json.dumps(["unadmitted-source:" + unit, None], separators=(",", ":")),
        source_product="unadmitted-source:" + unit,
        kind_contract="unadmitted-source-contract",
        subject="source-view:" + unit,
        subject_definition="original-source-view",
        project_id=PROJECT,
        original_source=document,
        analyzed_scope_meaning=canonical_bytes(
            semantic_value(dict(source=source, selectors=selectors))
        ).decode(),
        document=document,
        projection_digest=projection,
        section_pointer="#/groups/0",
        membership="descendants",
    )
    base = DeclaredNativeFrameSource(canonical_bytes(body).decode(), canonical_bytes(pin).decode())
    primary = [piece for piece in pieces if piece["kind"] == "native_text"]
    frame = DeclaredProposalFrame(
        base.source_content,
        base.pin_content,
        sentence_values=tuple(
            ProposalSentence(
                identifier,
                native_address(base, start=piece["start"], end=piece["end"]),
                piece["start"],
                piece["end"],
            )
            for (identifier, _), piece in zip(sentences, primary, strict=True)
        ),
    )
    return dict(
        version="external-extraction-input-1",
        unit_ref=frame.unit_ref,
        source_pin=pin,
        frame=source_value(frame.record),
        guideline="Preserved independent Weibull source annotations, retaining proposed standing.",
        known_reference_standing="authored",
        known_classes=source_value({}),
        known_entities=[],
        bootstrap_terms=[],
        macros=source_value({}),
        native_observations=source_value([]),
        scope_standing="explicitly-none",
    )


def value(raw):
    if isinstance(raw, list):
        return [value(child) for child in raw]
    if not isinstance(raw, dict):
        return raw
    if set(raw) == {"ref"}:
        return dict(kind="entity", target=raw["ref"])
    if raw.get("t") in {"formula", "set"}:
        return dict(
            kind=raw["t"],
            language="latex",
            expression=raw["latex"],
            bindings=[
                dict(
                    kind=binding["bind"],
                    symbol=symbol,
                    **{
                        ("parameter" if key == "param" else key): child
                        for key, child in binding.items()
                        if key != "bind"
                    },
                )
                for symbol, binding in raw["symbols"].items()
            ],
        )
    if "op" in raw:
        tag = raw["op"]
        if tag == "and":
            return dict(kind="all", terms=value(raw["args"]))
        return dict(kind=tag, **{key: value(child) for key, child in raw.items() if key != "op"})
    return {key: value(child) for key, child in raw.items()}


def response(prepared, unit, source_packet):
    raw = json.loads((ROOT / "domains/statistics/reference" / unit / "batch.json").read_text())
    classes = {row["local_ref"]: row["type"] for row in raw["entities"]}
    statements = {row["local_ref"] for row in raw["statements"]}

    def prop(subject, name):
        if subject in statements:
            return None
        definition = prepared.index.definitions[
            "SourceStatement" if subject in statements else classes[subject]
        ]
        return next((item.iri for item in definition.properties if item.name == name), None)

    def qualification(raw):
        result = dict(modality=raw.get("modality", "asserted"), polarity=True)
        for key, child in raw.items():
            if key == "modality":
                continue
            if key in {"param_values", "param_mapping"}:
                result[key] = {
                    name: dict(key=name, value=value(item)) for name, item in child.items()
                }
            else:
                result["condition" if key == "conditions" else key] = value(child)
        return result

    def evidence(row):
        return [dict(item) for item in row["evidence"]]

    rows = []
    for entity in raw["entities"]:
        identifier = entity["local_ref"]
        attributes = []
        citation = next(
            (evidence(claim) for claim in raw["claims"] if claim["subject"] == identifier),
            evidence(raw["claims"][0]),
        )
        if entity["type"] == "RandomVariable":
            for name, text, establishment in (
                ("symbol", entity["symbol"], "stated"),
                ("scope_locator", source_packet["unit_ref"], "agent_asserted"),
            ):
                attributes.append(
                    dict(
                        predicate=prop(identifier, name),
                        value=dict(kind="text", text=text),
                        qualification=qualification({}),
                        establishment=establishment,
                        evidence=citation,
                    )
                )
        for name, child in entity["identity"].items():
            attributes.append(
                dict(
                    predicate=prop(identifier, name),
                    value=(
                        dict(kind="entity", target=child)
                        if name == "family"
                        else dict(kind="text", text=child)
                    ),
                    qualification=qualification({}),
                    establishment="stated",
                    evidence=citation,
                )
            )
        rows.append(
            dict(
                id=identifier,
                class_iri=prepared.index.definitions[entity["type"]].iri,
                label=entity["label"],
                attributes=attributes,
            )
        )
    return dict(
        unit_ref=source_packet["unit_ref"],
        entities=rows,
        statements=[
            dict(
                id=row["local_ref"],
                kind=row["kind"],
                anchor=source_packet["unit_ref"] if row["anchor"] == "unit" else row["anchor"][0],
            )
            for row in raw["statements"]
        ],
        claims=[
            dict(
                id=row["local_ref"],
                subject=row["subject"],
                predicate=prop(row["subject"], row["predicate"]),
                object=value(row["object"]),
                qualification=qualification(row["qualifiers"]),
                establishment="stated",
                statement=row["statement"],
                **({"statement_role": row["statement_role"]} if "statement_role" in row else {}),
                evidence=evidence(row),
            )
            for row in raw["claims"]
            if prop(row["subject"], row["predicate"]) is not None
        ],
        identity_exclusions=[],
        alternatives=raw["alternatives"],
        unsupported=[
            dict(
                id=row["local_ref"],
                kind="unsupported_source_meaning",
                text=row["quote"],
                reason=row["reason"],
                evidence=[dict(sentence=row["sentence"], quote=row["quote"], role="primary")],
            )
            for row in raw["unsupported"]
        ]
        + [
            dict(
                id=row["local_ref"],
                kind="unsupported_historical_predicate",
                text=row["predicate"],
                reason="The current external ingress cannot represent this statement-subject claim. Preserve the source report without inferring a replacement.",
                evidence=evidence(row),
            )
            for row in raw["claims"]
            if prop(row["subject"], row["predicate"]) is None
        ],
    )


def cohort_inputs(prepared, model):
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    context = SubjectContext(
        PROJECT, "bounded-weibull-knowledge", None, b"{}", subject_definition="knowledge-universe"
    )
    roles, cohort = [], []
    for unit in ("E1", "E2", "E3"):
        source_packet = packet(unit)
        authored = response(prepared, unit, source_packet)
        located = locate_external_extraction(
            prepared,
            source_packet,
            authored,
            model=model,
            placement_policy=PlacementPolicy(),
            check_active=lambda: None,
        )
        pin = source_packet["source_pin"]
        from corpus_structure.semantic.data_operation_identity import decode_semantic_value

        source_context = SubjectContext(
            PROJECT,
            pin["subject"],
            pin["original_source"],
            json_bytes(decode_semantic_value(json.loads(pin["analyzed_scope_meaning"]))),
            subject_definition=pin["subject_definition"],
        )
        for name, class_name, body in (
            ("proposals", "DdoLocatedExternalExtraction", located),
            ("proposal_contexts", "DdoExternalExtractionPacket", source_packet),
        ):
            roles.append(
                CPUInputRole(
                    name,
                    None,
                    1,
                    "unadmitted:" + unit + ":" + name,
                    None,
                    kinds[NS + "external-extraction/" + class_name],
                    source_context,
                    body,
                    (
                        AuthoredFactSupportReference(
                            admission_id="unadmitted-reference:" + unit,
                            source_reference="domains/statistics/reference/" + unit,
                        ),
                    ),
                    producer_output=None,
                )
            )
        source_path = ROOT / "domains/statistics/reference" / unit
        cohort.append(
            dict(
                unit=unit,
                source_hashes={
                    name: sha256((source_path / name).read_bytes()).hexdigest()
                    for name in ("packet.md", "batch.json")
                },
                original_annotation=json.loads((source_path / "batch.json").read_bytes()),
                packet=source_packet,
                authored=authored,
                located=located,
            )
        )
    policy = rich_policy_value(prepared, model).model_dump(mode="python")
    roles.append(
        CPUInputRole(
            "policy",
            None,
            1,
            "unadmitted:policy",
            None,
            kinds[NS + "rich-knowledge/DdoRichConsolidationPolicy"],
            context,
            policy,
            (
                AuthoredFactSupportReference(
                    admission_id="unadmitted-policy",
                    source_reference="domains/statistics/schema/rules.yaml",
                ),
            ),
            producer_output=None,
        )
    )
    recipe = next(
        item.key
        for item in model.identities
        if item.domain == "recipe" and item.owner == "rich.consolidate"
    )
    inputs = RichKernelInputs(
        recipe, context, tuple(roles), parameters=b'["mapping",[]]', replicate=None
    )
    return inputs, cohort


def authored_propositions(prepared, model):
    """Retain checked domain meaning as explicit authorship, without source receipts."""
    from corpus_structure.semantic.data_operation_identity import canonical_identity
    from corpus_structure.semantic.rich_consolidation import RichAssembly
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichAuthoredPacket,
        DdoRichAuthoredProposition,
        DdoRichAuthoredPropositions,
        DdoRichEntity,
        DdoRichOccurrence,
    )
    from corpus_structure.semantic.rich_proposal_lowering import lower_rich_proposals

    inputs, cohort = cohort_inputs(prepared, model)
    builder = RichAssembly(prepared, model, inputs)
    lower_rich_proposals(builder, check_active=lambda: None)
    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    members = []
    omitted = []
    for packet in builder.graph().members:
        body = packet.body
        identifier = packet.member_id
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(
                update={
                    "source_members": (),
                    "identities": tuple(
                        identity.model_copy(update={"source_context": None})
                        for identity in body.identities
                    ),
                }
            )
        elif isinstance(body, DdoRichOccurrence):
            identifier = canonical_identity(
                "rich-authored-proposition",
                [
                    inputs.context.identity_record,
                    body.fact_id,
                    body.observed_qualification_value,
                    sorted(set(body.dependencies)),
                ],
            ).key
            body = DdoRichAuthoredProposition(
                member_type="authored-proposition",
                proposition_id=identifier,
                fact_id=body.fact_id,
                observed_qualification_value=body.observed_qualification_value,
                dependencies=body.dependencies,
            )
        if body.member_type in {"diagnostic", "identity-resolution"}:
            omitted.append(dict(member_type=body.member_type, member_id=packet.member_id))
        else:
            members.append(
                DdoRichAuthoredPacket(
                    member_id=identifier,
                    kind_contract=kinds[NS + "rich-knowledge/" + type(body).__name__],
                    context=packet.context,
                    body=body,
                )
            )
    authored = DdoRichAuthoredPropositions(
        version="rich-authored-propositions-1",
        standing="authored-propositions",
        members=tuple(members),
        macros={},
    )
    from corpus_structure.semantic.rich_graph_validation import read_rich_graph

    read_rich_graph(prepared, model, context=inputs.context, graph=authored, inputs=())
    return inputs.context, authored, cohort, omitted


def main(prepared=None, model=None):

    if prepared is None:
        prepared, model = prepare()
    inputs, cohort = cohort_inputs(prepared, model)
    observed = []

    class ObservedKernel(RichRelationKernel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, observe_inputs=observed.append)

    with patch("corpus_structure.semantic.rich_relations.RichRelationKernel", ObservedKernel):
        result = consolidate_rich_knowledge(
            prepared, model, inputs=inputs, check_active=lambda: None
        )
    output = Path(__file__).parent
    (output / "rich-cohort.json").write_bytes(
        json_bytes(
            dict(standing="offline-unadmitted-reference-cohort", project=PROJECT, cohort=cohort)
        )
    )
    report = dict(
        standing="offline-unadmitted-observation",
        release_id=prepared.release_id,
        observations=observed,
        member_count=len(result.members),
        selected_fact_count=len(result.eligibility.selected_fact_ids),
        selected_occurrence_count=len(result.eligibility.selected_occurrence_ids),
        limit="Three independently authored source units represent this bounded project. Full-book project-wide sizes remain unobserved. Native role admission has not been performed.",
    )
    (output / "rich-placement.json").write_bytes(json_bytes(report))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
