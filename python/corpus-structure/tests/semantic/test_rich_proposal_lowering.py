"""Source proposal lowerer consumes actual located packets and source-scoped contexts."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

from corpus_structure.methods.llm.cascade import PlacementPolicy
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import (
    ExternalExecutorContract,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_support import (
    AuthoredFactSupportReference,
    ComputationalSupportReference,
)
from corpus_structure.semantic.declared_math_products import math_operation_declarations
from corpus_structure.semantic.external_extraction import (
    external_extraction_operation_sources,
    locate_external_extraction,
    rich_external_declarations,
)
from corpus_structure.semantic.math_context import acquire_analysis_context_profile
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
from corpus_structure.semantic.rich_consolidation import consolidate_rich_knowledge
from corpus_structure.semantic.rich_cpu_inputs import RichKernelInputs
from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAlternative,
    DdoRichDiagnostic,
    DdoRichEntity,
    DdoRichIdentityExclusion,
    DdoRichOccurrence,
)
from corpus_structure.semantic.rich_knowledge_sources import (
    rich_knowledge_declarations,
    rich_knowledge_inputs,
)
from corpus_structure.semantic.rich_policy_binding import rich_policy_value
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.proposals_support import batch
from semantic.record_contracts_support import release_inputs
from semantic.test_external_rich_extraction import packet


def test_actual_source_proposal_context_and_constraint_survive_rich_cpu_lowering():
    bundle = release_inputs()[0]
    source = SourceArtifact(
        "source-rich-example",
        (
            """id: urn:source-rich-example
name: source_rich_example
imports: [ROOT]
prefixes: {r: 'urn:source-rich-example:'}
default_prefix: r
classes:
  ScientificSubject:
    is_a: Entity
    attributes:
      value:
        range: Value
        inlined: true
        multivalued: true
        annotations: {cs:constraint_scope: accepted_value, cs:role: predicate}
""".replace("ROOT", bundle.root)
        ).encode(),
    )
    bundle = SourceBundle(source.name, (*bundle.sources, source))
    bundle, deps = rich_knowledge_inputs(
        bundle,
        ResolvedDependencies(),
        domain_rules=b"rules: []\n",
        context_profile=acquire_analysis_context_profile(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    rich_sources, source_sources = (
        rich_knowledge_operation_sources(),
        external_extraction_operation_sources(),
    )
    sources = PythonSourceCollection(
        tuple(
            {
                item.module: item for item in (*rich_sources.sources, *source_sources.sources)
            }.values()
        ),
        boundary_contracts=(*rich_sources.boundary_contracts, *source_sources.boundary_contracts),
    )
    model = compile_data_operations(
        bundle,
        declarations=(
            *rich_knowledge_declarations(deps),
            record_policy_kind_declarations(),
            math_operation_declarations(),
            rich_external_declarations(
                ExternalExecutorContract(
                    "external-executor-v1",
                    "Emit actual rich source proposals.",
                    "explicit-external-agent",
                    "asserted-model",
                    "declared-inputs-only",
                )
            ),
        ),
        python_sources=sources,
    )
    prepared = prepare_release(bundle, deps)
    original = packet()
    raw = batch()
    raw["unit_ref"] = original["unit_ref"]
    raw["entities"] = [
        dict(id="p", class_iri="urn:source-rich-example:ScientificSubject", label="A"),
        dict(id="q", class_iri="urn:source-rich-example:ScientificSubject", label="B"),
    ]
    raw["statements"][0]["anchor"] = original["unit_ref"]
    raw["claims"][0].update(
        predicate="urn:source-rich-example:value", object={"kind": "number", "number": Decimal("1")}
    )
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:1"
    raw["identity_exclusions"] = [
        dict(
            id="separate",
            left={"kind": "local", "target": "p"},
            right={"kind": "local", "target": "q"},
            reason="distinct source entities",
            evidence=deepcopy(raw["claims"][0]["evidence"]),
        )
    ]
    located = locate_external_extraction(
        prepared,
        original,
        raw,
        model=model,
        placement_policy=PlacementPolicy(),
        check_active=lambda: None,
    )
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    pin = original["source_pin"]
    source_context = SubjectContext(
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        json_bytes(decode_semantic_value(json_loads(pin["analyzed_scope_meaning"]))),
        subject_definition=pin["subject_definition"],
    )
    context = SubjectContext(
        pin["project_id"], "knowledge:current", None, b"{}", subject_definition="knowledge-universe"
    )
    ns = "https://corpus-structure.dev/semantic/data-operation-"

    def role(name, kind, body, header):
        support = (
            (
                AuthoredFactSupportReference(
                    admission_id="policy-authoring", source_reference="actual-policy"
                ),
            )
            if name == "policy"
            else (
                ComputationalSupportReference(
                    derivation_id="actual-episode:" + name, admission_use_id="current-use:" + name
                ),
            )
        )
        return CPUInputRole(
            name, None, 1, "product:" + name, None, ids[ns + kind], header, body, support
        )

    roles = (
        role(
            "proposals", "external-extraction/DdoLocatedExternalExtraction", located, source_context
        ),
        role(
            "proposal_contexts",
            "external-extraction/DdoExternalExtractionPacket",
            original,
            source_context,
        ),
        role(
            "policy",
            "rich-knowledge/DdoRichConsolidationPolicy",
            rich_policy_value(prepared, model).model_dump(mode="python"),
            context,
        ),
    )
    value = consolidate_rich_knowledge(
        prepared,
        model,
        inputs=RichKernelInputs.from_basis(
            RichKernelInputs(
                "actual-rich-core", context, roles, parameters=b'["mapping",[]]', replicate=None
            ).basis()
        ),
        check_active=lambda: None,
    )
    occurrences = [item.body for item in value.members if isinstance(item.body, DdoRichOccurrence)]
    assert len(occurrences) == 1 and occurrences[0].original.product_id == "product:proposals"
    assert occurrences[0].statement is not None
    assert occurrences[0].statement.member_id == "statement:s"
    constraints = [
        item.body for item in value.members if isinstance(item.body, DdoRichIdentityExclusion)
    ]
    assert len(constraints) == 1 and constraints[0].outcome == "located"
    assert constraints[0].declaration.context.original_source == pin["original_source"]
    entities = [item.body for item in value.members if isinstance(item.body, DdoRichEntity)]
    assert all(
        basis.source_context is not None
        and basis.source_context.original_source == pin["original_source"]
        for entity in entities
        for basis in entity.identities
    )
    assert len(value.eligibility.selected_fact_ids) == 1

    def run_variant(response, suffix):
        located_variant = locate_external_extraction(
            prepared,
            original,
            response,
            model=model,
            placement_policy=PlacementPolicy(),
            check_active=lambda: None,
        )
        variant_roles = tuple(
            replace(
                item,
                product_id=item.product_id + suffix,
                body=located_variant if item.role == "proposals" else item.body,
            )
            for item in roles
        )
        return consolidate_rich_knowledge(
            prepared,
            model,
            inputs=RichKernelInputs.from_basis(
                RichKernelInputs(
                    "actual-rich-core",
                    context,
                    variant_roles,
                    parameters=b'["mapping",[]]',
                    replicate=None,
                ).basis()
            ),
            check_active=lambda: None,
        )

    # Two genuine source occurrences can have one canonical meaning. Preserve
    # both witnesses without inventing a competing or incomplete alternative.
    collapsed = deepcopy(raw)
    collapsed["claims"].append({**deepcopy(collapsed["claims"][0]), "id": "c2"})
    collapsed["alternatives"] = [
        {
            "id": "same",
            "members": ["c1", "c2"],
            "faithful": True,
            "reason": "two source branches have one actual meaning",
        }
    ]
    collapsed_value = run_variant(collapsed, ":collapsed")
    assert not any(isinstance(item.body, DdoRichAlternative) for item in collapsed_value.members)
    assert any(
        isinstance(item.body, DdoRichDiagnostic) and item.body.code == "equivalent-alternative"
        for item in collapsed_value.members
    )
    assert len(collapsed_value.eligibility.selected_fact_ids) == 1
    assert len(collapsed_value.eligibility.selected_occurrence_ids) == 2

    # Several attributes of one real entity share one interpretation packet;
    # their separate occurrences do not duplicate its source context authority.
    repeated = deepcopy(raw)
    attribute = {
        "predicate": raw["claims"][0]["predicate"],
        "value": raw["claims"][0]["object"],
        "qualification": raw["claims"][0]["qualification"],
        "establishment": "stated",
        "evidence": raw["claims"][0]["evidence"],
    }
    repeated["entities"][0]["attributes"] = [deepcopy(attribute), deepcopy(attribute)]
    repeated_value = run_variant(repeated, ":attributes")
    assert len(repeated_value.eligibility.selected_fact_ids) == 1
    assert len(repeated_value.eligibility.selected_occurrence_ids) == 3
