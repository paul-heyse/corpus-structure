"""Lower actual located proposal members into checked project knowledge meaning."""

import json
from collections import defaultdict
from typing import Literal

import networkx as nx

from corpus_structure.core.evidence import MacroDef

from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_ports import _untrusted_value
from .identity import canonical_bytes
from .observations import source_python
from .rich_knowledge_contracts import (
    DdoRichAlternative,
    DdoRichEntity,
    DdoRichEntityIdentity,
    DdoRichIdentityResolution,
    DdoRichOccurrence,
    DdoRichPropertyValue,
    rich_context_pin,
)


def _member(parent, packet):
    return parent.model_copy(
        update={"member_id": packet["member_id"], "kind_contract": packet["kind_contract"]}
    )


def _located(evidence, *, primary=False):
    selected = [
        item
        for item in evidence
        if item.get("outcome") == "located"
        and item.get("start") is not None
        and item.get("end") is not None
        and item["start"] < item["end"]
    ]
    if primary and not any(item["role"] == "primary" for item in selected):
        return ()
    unique = {canonical_bytes(semantic_value(item)): item for item in selected}
    return tuple(unique[key] for key in sorted(unique))


def lower_rich_proposals(builder, *, check_active):
    from .data_operation_json import json_bytes
    from .data_operation_model import SubjectContext, validate_subject_context
    from .expression_context import bind_expression_context
    from .reference_positions import LocatedReference, collect_references, rewrite_references
    from .rich_knowledge import RichEntitySource, resolve_rich_entities, rich_property_value
    from .rich_proposals import read_rich_proposals
    from .rich_scientific import RichScientificSourceContext
    from .statement_types import statement_definition

    prepared, model = builder.prepared, builder.model
    sources = []
    contexts = []
    for role in builder.inputs.selected("proposal_contexts"):
        packet = prepared.validate_json(
            "DdoExternalExtractionPacket", json_bytes(role.body)
        ).model_dump(mode="python", exclude_unset=True)
        contexts.append((builder.inputs.reference(role), packet))
    for role in builder.inputs.selected("proposals"):
        check_active()
        report = read_rich_proposals(prepared, role.body)
        matches = [
            (reference, packet)
            for reference, packet in contexts
            if (packet["unit_ref"], packet["source_pin"])
            == (report["unit_ref"], report["source_pin"])
        ]
        if len(matches) != 1:
            raise ValueError(
                "located proposals require one actual matching selected interpretation packet"
            )
        context_ref, packet = matches[0]
        macros = source_python(packet["macros"])
        if not isinstance(macros, dict):
            raise ValueError(
                "proposal interpretation requires its actual explicit macro definitions"
            )
        macros = {name: MacroDef.model_validate(value) for name, value in macros.items()}
        parent = builder.inputs.reference(role)
        grouped = defaultdict(dict)
        for member in report["members"]:
            body = member["body"]
            grouped[body["proposal_type"]][body["id"]] = (member, body)
        entities = tuple(value[1] for value in grouped["entity"].values())
        exclusions = tuple(value[1] for value in grouped["identity_exclusion"].values())
        for entity in entities:
            if builder.ids.get(entity["class_iri"]) not in builder.policy.allowed_domain_contracts:
                raise ValueError(
                    "source entity class is outside the actual checked rich domain contract universe"
                )
        actual_contexts = [
            member["context"]
            for member in role.body["members"]
            if member["body"]["proposal_type"] == "entity"
        ]
        if actual_contexts and any(value != actual_contexts[0] for value in actual_contexts):
            raise ValueError(
                "one source entity proposal population requires its actual common source context"
            )
        source_context = None
        if actual_contexts:
            value = actual_contexts[0]
            source_context = SubjectContext(
                role.context.project_id,
                value["subject"],
                value["original_source"],
                json_bytes(value["analyzed_scope"]),
                subject_definition=value["subject_definition"],
            )
            validate_subject_context(model, source_context)
        else:
            # No entity identity is derived from this empty population.
            value = report["source_pin"]
            from .data_operation_identity import decode_semantic_value

            source_context = SubjectContext(
                role.context.project_id,
                value["subject"],
                value["original_source"],
                json_bytes(decode_semantic_value(json.loads(value["analyzed_scope_meaning"]))),
                subject_definition=value["subject_definition"],
            )
            validate_subject_context(model, source_context)
        address = canonical_bytes([parent.product_id, parent.member_id]).decode()
        sources.append(
            (
                role,
                parent,
                report,
                context_ref,
                packet,
                macros,
                grouped,
                RichEntitySource(address, source_context, entities, exclusions, macros),
            )
        )
    if not sources:
        return
    entity_contracts = {
        definition.iri: builder.ids[definition.iri]
        for definition in prepared.definitions
        if definition.iri in builder.ids
    }
    mappings, resolutions = resolve_rich_entities(
        prepared,
        entity_contracts=entity_contracts,
        universe=builder.context,
        sources=tuple(item[-1] for item in sources),
        known=builder.known,
    )
    by_source = {item[-1].reference: item for item in sources}
    for role, parent, report, context_ref, packet, macros, grouped, source in sources:
        mapping = mappings[source.reference]
        for local, (member, entity) in grouped["entity"].items():
            identifier = mapping[local]
            iri = entity["class_iri"]
            builder.entities[identifier] = builder.entities.get(identifier, frozenset()) | {iri}
        builder.values.entities.update(builder.entities)
    for role, parent, report, context_ref, packet, macros, grouped, source in sources:
        check_active()
        mapping = mappings[source.reference]
        statement_ids = {
            local: canonical_identity(
                "rich-source-statement",
                [builder.context.identity_record, _untrusted_value(_member(parent, value[0]))],
            ).key
            for local, value in grouped["statement"].items()
            if value[1]["kind"] != "outside"
        }
        statement_meta = statement_definition(prepared)
        for local, identifier in statement_ids.items():
            builder.entities[identifier] = frozenset({statement_meta.iri})
            builder.values.entities[identifier] = builder.entities[identifier]
            if identifier not in builder.packets:
                member, statement = grouped["statement"][local]
                builder.add(
                    DdoRichEntity(
                        member_type="entity",
                        entity_id=identifier,
                        class_contracts=(builder.ids[statement_meta.iri],),
                        identities=(
                            DdoRichEntityIdentity(
                                class_contract=builder.ids[statement_meta.iri],
                                fields=(),
                                source_context=rich_context_pin(source.context),
                                label=statement.get("title"),
                            ),
                        ),
                        source_members=(_member(parent, member),),
                    )
                )

        def class_reference(reference):
            expected = prepared.index.definitions.get(reference.range)
            if expected is None:
                raise ValueError("source reference has no actual declared class range")
            candidates = set()
            if reference.target in mapping:
                entity = grouped["entity"][reference.target][1]
                actual = prepared.index.by_iri[entity["class_iri"]]
                if actual.iri == expected.iri or expected.name in actual.ancestors:
                    candidates.add(mapping[reference.target])
            if reference.target in statement_ids and (
                statement_meta.iri == expected.iri or expected.name in statement_meta.ancestors
            ):
                candidates.add(statement_ids[reference.target])
            if reference.target in builder.entities and any(
                prepared.index.by_iri[iri].iri == expected.iri
                or expected.name in prepared.index.by_iri[iri].ancestors
                for iri in builder.entities[reference.target]
            ):
                candidates.add(reference.target)
            if len(candidates) != 1:
                raise ValueError(
                    "source reference has unavailable or ambiguous actual class membership"
                )
            return next(iter(candidates))

        def property_for(definition, predicate):
            found = tuple(prop for prop in definition.properties if prop.iri == predicate)
            if len(found) != 1:
                raise ValueError(
                    "source predicate does not identify one actual declared property owner"
                )
            return found[0]

        def source_context(original):
            value = RichScientificSourceContext(
                original=original, context=context_ref, macros=macros
            )
            existing = tuple(item for item in builder.source_contexts if item.original == original)
            if existing and any(item != value for item in existing):
                raise ValueError("one actual source member has conflicting interpretation contexts")
            if not existing:
                builder.source_contexts.append(value)

        def occurrence(
            result,
            original,
            item,
            establishment,
            evidence,
            dependencies=(),
            statement=None,
            statement_kind=None,
            statement_role=None,
        ):
            identifier = canonical_identity(
                "rich-source-occurrence",
                [
                    builder.context.identity_record,
                    _untrusted_value(original),
                    item,
                    result.fact.fact_id,
                    result.observed_qualification_value,
                ],
            ).key
            builder.add(
                DdoRichOccurrence(
                    member_type="source-occurrence",
                    occurrence_id=identifier,
                    fact_id=result.fact.fact_id,
                    original=original,
                    statement=statement,
                    observed_qualification_value=result.observed_qualification_value,
                    dependencies=tuple(sorted(dependencies)),
                    establishment=establishment,
                    statement_kind=statement_kind,
                    statement_role=statement_role,
                    evidence_count=len(evidence),
                )
            )
            source_context(original)

        # Actual key bases remain available for later closed-universe identity joins.
        for local, (member, entity) in grouped["entity"].items():
            identifier = mapping[local]
            if identifier in builder.packets:
                continue
            definition = prepared.index.by_iri[entity["class_iri"]]
            key_names = {
                name
                for group in definition.identity_groups
                if group != definition.identity_slots
                for name in group
            }
            fields = {}
            for attribute in entity.get("attributes", ()):
                prop = property_for(definition, attribute["predicate"])
                if prop.name in key_names:
                    fields[prop.name] = rich_property_value(
                        prepared,
                        definition,
                        prop,
                        bind_expression_context(attribute["value"], macros),
                        class_reference,
                    )
            if entity.get("scope") is not None and "scope_locator" in key_names:
                fields.setdefault("scope_locator", entity["scope"]["locator"])
            bases = tuple(
                DdoRichPropertyValue(
                    property_contract=builder.ids[definition.iri + "/property/" + name],
                    value_id=builder.values.lower_property(definition.name, name, value),
                )
                for name, value in sorted(fields.items())
            )
            builder.add(
                DdoRichEntity(
                    member_type="entity",
                    entity_id=identifier,
                    class_contracts=(builder.ids[definition.iri],),
                    identities=(
                        DdoRichEntityIdentity(
                            class_contract=builder.ids[definition.iri],
                            fields=bases,
                            source_context=None
                            if json.loads(
                                next(
                                    row.body
                                    for row in prepared.registry_rows
                                    if row.kind == "operation_class" and row.name == definition.name
                                )
                            ).get("cs:scope")
                            == "global"
                            else rich_context_pin(source.context),
                            label=entity.get("label"),
                        ),
                    ),
                    source_members=(_member(parent, member),),
                )
            )
        claim_facts = {identifier: identifier for identifier in builder.values._known_facts}
        claims = grouped["claim"]
        dependencies = {}
        for local, (_, claim) in claims.items():
            refs = {
                reference.target
                for class_name, value in (
                    ("Value", claim["object"]),
                    (
                        builder.kinds[builder.policy.qualification_contract].name,
                        claim["qualification"],
                    ),
                )
                for reference in collect_references(prepared, class_name, value)
                if reference.kind == "fact"
            }
            dependencies[local] = refs
        graph = nx.DiGraph(backend="networkx")
        graph.add_nodes_from(claims)
        graph.add_edges_from(
            (dependency, local)
            for local, refs in dependencies.items()
            for dependency in refs
            if dependency in claims
        )
        cyclic = (
            set().union(
                *(
                    set(component)
                    for component in nx.strongly_connected_components(graph)
                    if len(component) > 1 or any(graph.has_edge(node, node) for node in component)
                )
            )
            if graph
            else set()
        )
        blocked = (
            cyclic | set().union(*(nx.descendants(graph, node) for node in cyclic))
            if cyclic
            else set()
        )
        for local in sorted(blocked):
            builder.diagnostic(
                "cyclic-claim-reference" if local in cyclic else "blocked-claim-reference",
                "Source claim has cyclic or cycle-blocked declared dependencies",
                (_member(parent, claims[local][0]),),
            )
        ordered = nx.lexicographical_topological_sort(
            graph.subgraph(set(claims) - blocked), key=str
        )
        for local in ordered:
            check_active()
            member, claim = claims[local]
            original = _member(parent, member)
            if not dependencies[local] <= claim_facts.keys():
                builder.diagnostic(
                    "unavailable-claim-premise",
                    "Source claim references unavailable actual fact premises",
                    (original,),
                )
                continue
            evidence = _located(claim["evidence"], primary=True)
            if not evidence:
                builder.diagnostic(
                    "unlocated-primary-evidence",
                    "Source claim has no actual located primary evidence",
                    (original,),
                )
                continue
            try:
                subject = class_reference(
                    LocatedReference("class", claim["subject"], "Entity", ("subject",))
                )
                classes = builder.entities[subject]
                definitions = [
                    prepared.index.by_iri[iri]
                    for iri in classes
                    if any(
                        prop.iri == claim["predicate"]
                        for prop in prepared.index.by_iri[iri].properties
                    )
                ]
                definitions = [
                    definition
                    for definition in definitions
                    if not any(definition.name in other.ancestors for other in definitions)
                ]
                if len(definitions) != 1:
                    raise ValueError(
                        "claim predicate has ambiguous or unavailable actual subject class ownership"
                    )
                definition = definitions[0]
                prop = property_for(definition, claim["predicate"])
                value = rich_property_value(
                    prepared,
                    definition,
                    prop,
                    bind_expression_context(claim["object"], macros),
                    class_reference,
                    claim_facts,
                )
                qualification = rewrite_references(
                    prepared,
                    builder.kinds[builder.policy.qualification_contract].name,
                    bind_expression_context(claim["qualification"], macros),
                    classes=class_reference,
                    facts=claim_facts,
                    collision="equal",
                )
                selected_statement = None
                statement_kind = None
                if claim.get("statement") is not None:
                    if claim["statement"] not in statement_ids:
                        raise ValueError("claim statement context is explicitly unresolved")
                    stmt_member, stmt_body = grouped["statement"][claim["statement"]]
                    selected_statement = _member(parent, stmt_member)
                    statement_kind = stmt_body["kind"]
                result = builder.values.add_property_fact(
                    subject_entity=subject,
                    class_name=definition.name,
                    property_name=prop.name,
                    value=value,
                    qualification=qualification,
                    qualification_class=builder.kinds[builder.policy.qualification_contract].name,
                )
                claim_facts[local] = result.fact.fact_id
                occurrence(
                    result,
                    original,
                    "claim:" + local,
                    claim["establishment"],
                    evidence,
                    dependencies=tuple(claim_facts[target] for target in dependencies[local]),
                    statement=selected_statement,
                    statement_kind=statement_kind,
                    statement_role=claim.get("statement_role"),
                )
            except (KeyError, ValueError) as error:
                builder.diagnostic("unrepresentable-source-claim", str(error), (original,))
        for local, (member, entity) in grouped["entity"].items():
            definition = prepared.index.by_iri[entity["class_iri"]]
            for index, attribute in enumerate(entity.get("attributes", ())):
                check_active()
                evidence = _located(attribute["evidence"])
                original = _member(parent, member)
                if not evidence:
                    builder.diagnostic(
                        "unlocated-attribute-evidence",
                        "Source attribute lacks located evidence",
                        (original,),
                    )
                    continue
                try:
                    prop = property_for(definition, attribute["predicate"])
                    value = rich_property_value(
                        prepared,
                        definition,
                        prop,
                        bind_expression_context(attribute["value"], macros),
                        class_reference,
                        claim_facts,
                    )
                    qualification = rewrite_references(
                        prepared,
                        builder.kinds[builder.policy.qualification_contract].name,
                        bind_expression_context(attribute["qualification"], macros),
                        classes=class_reference,
                        facts=claim_facts,
                        collision="equal",
                    )
                    result = builder.values.add_property_fact(
                        subject_entity=mapping[local],
                        class_name=definition.name,
                        property_name=prop.name,
                        value=value,
                        qualification=qualification,
                        qualification_class=builder.kinds[
                            builder.policy.qualification_contract
                        ].name,
                    )
                    occurrence(
                        result,
                        original,
                        "attribute:" + str(index),
                        attribute["establishment"],
                        evidence,
                    )
                except (KeyError, ValueError) as error:
                    builder.diagnostic("unrepresentable-source-attribute", str(error), (original,))
        for local, (member, alternative) in grouped["alternative"].items():
            selected = tuple(
                claim_facts.get(reference["member_id"].removeprefix("claim:"))
                for reference in alternative["claims"]
            )
            ids = tuple(sorted({identifier for identifier in selected if identifier is not None}))
            original = _member(parent, member)
            completeness = "incomplete" if None in selected else "complete"
            if not ids:
                builder.diagnostic(
                    "unmaterialized-alternative",
                    "No actual fact meaning from this alternative could be materialized",
                    (original,),
                )
                continue
            if completeness == "complete" and len(ids) == 1:
                builder.diagnostic(
                    "equivalent-alternative",
                    "All source alternatives have the same actual canonical fact meaning",
                    (original,),
                )
                continue
            identifier = canonical_identity(
                "rich-alternative",
                [builder.context.identity_record, _untrusted_value(original), completeness, ids],
            ).key
            builder.add(
                DdoRichAlternative(
                    member_type="alternative",
                    alternative_id=identifier,
                    fact_ids=ids,
                    completeness=completeness,
                    origin="source-proposal",
                    faithful=alternative["faithful"],
                    reason=alternative["reason"],
                    source_members=(original,),
                )
            )
        from .declared_structural_references import DeclaredStructuralSource
        from .rich_identity_exclusions import rich_identity_exclusion_id, rich_located_evidence
        from .rich_knowledge_contracts import (
            DdoRichExclusionDeclaration,
            DdoRichExclusionEndpoint,
            DdoRichIdentityExclusion,
        )

        for local, (member, exclusion) in grouped["identity_exclusion"].items():
            original = _member(parent, member)

            def endpoint(value):
                if value["kind"] == "known":
                    return value["target"] if value["target"] in builder.known else None
                return mapping.get(value["target"])

            left, right = endpoint(exclusion["left"]), endpoint(exclusion["right"])
            declaration = DdoRichExclusionDeclaration(
                local_id=local,
                unit_ref=report["unit_ref"],
                source=DeclaredStructuralSource.model_validate(report["source_pin"]),
                context=rich_context_pin(source.context),
                left=DdoRichExclusionEndpoint.model_validate(exclusion["left"]),
                right=DdoRichExclusionEndpoint.model_validate(exclusion["right"]),
                reason=exclusion["reason"],
                evidence=tuple(
                    rich_located_evidence(prepared, item) for item in exclusion["evidence"]
                ),
            )
            outcome: Literal["located", "unlocated", "unresolved-endpoint"] = (
                "unlocated"
                if not _located(exclusion["evidence"], primary=True)
                else "unresolved-endpoint"
                if None in (left, right)
                else "located"
            )
            reason = {
                "unlocated": "No actual located primary evidence",
                "unresolved-endpoint": "One or both actual declared endpoints are unresolved",
                "located": "Distinct actual endpoints constrained by located source evidence",
            }[outcome]
            fields = dict(
                declaration=declaration,
                left_entity_id=left,
                right_entity_id=right,
                outcome=outcome,
                reason=reason,
                source_members=(original,),
            )
            identifier = rich_identity_exclusion_id(builder.context, **fields)
            builder.add(
                DdoRichIdentityExclusion(
                    member_type="identity-exclusion", exclusion_id=identifier, **fields
                )
            )
        for local, (member, unsupported) in grouped["unsupported"].items():
            builder.diagnostic(
                "unsupported-source-proposal", unsupported["reason"], (_member(parent, member),)
            )
    for resolution in resolutions:
        source = by_source[resolution.source_reference]
        parent, grouped = source[1], source[6]
        original = _member(parent, grouped["entity"][resolution.local_id][0])
        fields = dict(
            resolved_entity_id=resolution.entity_id,
            source_members=(original,),
            basis=resolution.basis,
            outcome=resolution.outcome,
            candidate_identity_keys=resolution.candidate_identity_keys,
            matched_entity_ids=resolution.matched_entity_ids,
            dependency_sources=tuple(
                _member(parent, grouped["entity"][local][0]) for local in resolution.dependencies
            ),
        )
        identifier = canonical_identity(
            "rich-identity-resolution",
            [
                builder.context.identity_record,
                {key: _untrusted_value(value) for key, value in fields.items()},
            ],
        ).key
        builder.add(
            DdoRichIdentityResolution(
                member_type="identity-resolution", resolution_id=identifier, **fields
            )
        )
