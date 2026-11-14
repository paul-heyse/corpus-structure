"""Primary execution and pure retained projection of configured named native rules."""

from __future__ import annotations

from typing import Any

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.methods.annotation_rules import (
    AnnotationRuleMatch,
    AnnotationRuleResult,
    LocatedRole,
    PreparedAnnotationRules,
)
from corpus_structure.methods.native_evidence_layers import (
    retained_annotation_products,
    retained_annotation_profile,
)
from corpus_structure.semantic.characterization import AnnotationReference
from corpus_structure.semantic.product_reference import ProductReference

from .named_nominations import NamedNomination, naming_nomination
from .nodes import identity

NAMED_FAMILY = "construction.named_rules"
NAMED_VOCABULARY = "named-annotation-match-2"


def rule_identity(rule):
    return identity(
        "named-rule", rule.model_dump(mode="json") if hasattr(rule, "model_dump") else rule
    )


def populate_named(
    layer,
    view,
    native_pin,
    native_layer,
    prepared: PreparedAnnotationRules,
    *,
    check_active=lambda: None,
    admitted=lambda a, b: True,
):
    native_payload = native_layer.payload
    runs = [run for run in native_payload.get("native_runs", ()) if run["provider"] == "spacy"]
    if len(runs) != 1:
        raise ValueError("named rules require one exact native spaCy run")
    run = runs[0]
    profile = retained_annotation_profile(run)
    products = retained_annotation_products({native_pin: native_layer}, view, profile)
    annotations = {a["local_id"]: a for a in native_payload["annotations"]}
    source_occurrences = {o["local_id"]: o for o in native_payload["occurrences"]}
    token_refs = {
        (a["native_token"]["container"], a["native_token"]["index"]): dict(
            layer=native_pin.values(), local_id=a["local_id"]
        )
        for a in annotations.values()
        if a.get("native_token", {}).get("native_run") == run["local_id"]
    }
    def blocks():
        for product in products:
            container = f"spacy/{view.ref.id}/{product.block_id}/block"
            native = annotation_view(
                product, view.text[product.block_start:product.block_end], prepared.vocab, required=()
            )
            refs = {index: ref for (owner, index), ref in token_refs.items() if owner == container}

            def occurrences(index, *, refs=refs):
                ids = annotations[refs[index]["local_id"]]["occurrences"]
                for oid in ids:
                    layer.occurrences.setdefault(oid, source_occurrences[oid])
                return ids

            yield product, native, dict(layer=native_pin.values(), local_id=container), refs, occurrences

    _populate_named_blocks(layer, view, native_pin, prepared, blocks(), check_active=check_active, admitted=admitted)
    return products


def populate_named_products(layer, view, source, native, prepared, *, annotation_products=None, check_active=lambda: None, admitted=lambda a, b: True):
    """Interpret actual detached native blocks, with governed product/member addresses."""
    import json

    from corpus_structure.semantic.data_product_reference import DataProductReference, member_reference
    from corpus_structure.semantic.sentence_products import source_annotation_member_values, retained_source_annotation_products

    value = json.loads(native.content)
    products = retained_source_annotation_products(source, native) if annotation_products is None else annotation_products
    pin = DataProductReference(native.semantic_id)
    tokens = {(row["block_id"], row["ordinal"]): row for row in source_annotation_member_values(value) if row["record_type"] == "token"}

    def blocks():
        for product in products:
            native_view = annotation_view(product, view.text[product.block_start:product.block_end], prepared.vocab, required=())
            refs = {index: member_reference(pin, row["local_id"]).values() for (owner, index), row in tokens.items() if owner == product.block_id}

            def occurrences(index, *, product=product):
                token = product.tokens[index]
                return [layer.occurrence(view, token.start, token.end)]

            yield product, native_view, dict(product_id=pin.product_id, block_id=product.block_id), refs, occurrences

    _populate_named_blocks(layer, view, pin, prepared, blocks(), check_active=check_active, admitted=admitted)


def _populate_named_blocks(layer, view, native_pin, prepared, blocks, *, check_active, admitted):
    rules = {(r.rule, r.variant): r for r in prepared.rules}
    for product, native, container, token_refs, token_occurrences in blocks:
        check_active()
        selector = dict(
            projection=layer.scope["selectors"][0]["projection"], start=product.block_start, end=product.block_end
        )
        if not admitted(product.block_start, product.block_end):
            continue
        result = prepared.match(native)
        for rule, variant, availability in result.availability:
            declaration = rules[rule, variant]
            body = dict(
                rule=rule,
                variant=variant,
                mechanism=declaration.mechanism,
                protocol=NAMED_VOCABULARY,
                dependency_digest=product.dependency_digest,
                native_container=container,
                nodes=[],
                piece_indices=[],
                sentences=[],
                bindings=[],
                negation_occurrences=[],
                status=availability,
            )
            key = identity(
                "named-rule-availability",
                [native_pin.values(), container, rule_identity(declaration)],
            )
            layer.annotations[key] = dict(
                local_id=key,
                kind="construction.named_availability",
                family=NAMED_FAMILY,
                vocabulary=NAMED_VOCABULARY,
                rule_id=rule_identity(declaration),
                native_scheme="spacy-named-rule-availability-1",
                native_label=availability,
                status="interpreted" if availability == "available" else "unknown",
                named_match=body,
                occurrences=[layer.occurrence(view, product.block_start, product.block_end)],
                external_premises=[] if layer.semantic else [body["native_container"]],
            )
        for match in result.matches:
            declaration = rules[match.rule, match.variant]

            def token(index, *, container=container):
                return token_refs[index]

            bindings: list[dict[str, Any]] = []
            for role in match.roles:
                bindings.append(
                    dict(
                        role=role.role,
                        node=role.node,
                        head=token(role.head),
                        expansion=role.expansion,
                        members=[token(index) for index in role.nodes],
                        status=role.status,
                        **({"reason": role.reason} if role.reason else {}),
                    )
                )
                nomination = naming_nomination(native, match, role)
                if nomination is not None:
                    bindings[-1].update(
                        antecedent_status=nomination.status,
                        antecedent_members=[token(index) for index in nomination.antecedent_nodes],
                        **(
                            {"demonstrative": nomination.demonstrative}
                            if nomination.demonstrative is not None
                            else {}
                        ),
                        **({"antecedent_reason": nomination.reason} if nomination.reason else {}),
                    )
            body = dict(
                rule=match.rule,
                variant=match.variant,
                mechanism=match.mechanism,
                protocol=match.protocol,
                dependency_digest=match.dependency_digest,
                native_container=container,
                nodes=[token(index) for index in match.nodes],
                piece_indices=list(match.piece_indices),
                sentences=[
                    dict(
                        token_index=index,
                        **({"sentence": sentence} if sentence is not None else {}),
                    )
                    for index, sentence in zip(match.nodes, match.sentences, strict=True)
                ],
                bindings=bindings,
                negation_occurrences=[
                    layer.occurrence(view, a, b) for a, b in match.negation_extents
                ],
                status="matched"
                if all(role.status == "complete" for role in match.roles)
                else "partial",
            )
            key = identity(
                "named-binding", [native_pin.values(), container, rule_identity(declaration), body]
            )
            occurrences = [layer.occurrence(view, a, b) for a, b in match.extents]
            layer.annotations[key] = dict(
                local_id=key,
                kind="construction.named_binding",
                family=NAMED_FAMILY,
                vocabulary=NAMED_VOCABULARY,
                rule_id=rule_identity(declaration),
                native_scheme="spacy-named-rule-match-2",
                native_label=match.variant,
                status="interpreted",
                occurrences=occurrences,
                named_match=body,
                external_premises=body["nodes"] if layer.semantic else [body["native_container"], *body["nodes"]],
            )
            for role in match.roles:
                for order, index in enumerate(role.nodes):
                    endpoint = token(index)
                    participant = identity("named-role-member", [endpoint, role.role])
                    occurrences = token_occurrences(index)
                    layer.terms.setdefault(
                        participant,
                        dict(
                            local_id=participant,
                            kind="participant",
                            family=NAMED_FAMILY,
                            vocabulary=NAMED_VOCABULARY,
                            value=role.role,
                            status="interpreted" if role.status == "complete" else "unknown",
                            occurrences=occurrences,
                            external_premises=[endpoint],
                        ),
                    )
                    membership = identity("named-role-binding", [key, role.role, order, endpoint])
                    layer.memberships[membership] = dict(
                        local_id=membership,
                        group=key,
                        member=participant,
                        role=role.role,
                        order=order,
                        scope=key,
                        structural=False,
                        family=NAMED_FAMILY,
                        occurrences=occurrences,
                        premises=[key],
                        external_premises=[endpoint],
                    )
            for binding in bindings:
                for order, endpoint in enumerate(binding.get("antecedent_members", ())):
                    occurrences = token_occurrences(next(index for index, ref in token_refs.items() if ref == endpoint))
                    for oid in occurrences:
                        if oid not in layer.annotations[key]["occurrences"]:
                            layer.annotations[key]["occurrences"].append(oid)
                    participant = identity("named-role-member", [endpoint, "antecedent"])
                    layer.terms.setdefault(
                        participant,
                        dict(
                            local_id=participant,
                            kind="participant",
                            family=NAMED_FAMILY,
                            vocabulary=NAMED_VOCABULARY,
                            value="antecedent",
                            status="private_proposal",
                            occurrences=occurrences,
                            external_premises=[endpoint],
                        ),
                    )
                    membership = identity(
                        "named-antecedent-binding", [key, binding["role"], order, endpoint]
                    )
                    layer.memberships[membership] = dict(
                        local_id=membership,
                        group=key,
                        member=participant,
                        role="antecedent",
                        order=order,
                        scope=key,
                        structural=False,
                        family=NAMED_FAMILY,
                        occurrences=occurrences,
                        premises=[key],
                        external_premises=[endpoint],
                    )
        available = all(state == "available" for _, _, state in result.availability) and all(
            role.status == "complete" for match in result.matches for role in match.roles
        )
        layer.record(
            NAMED_FAMILY,
            selector,
            "complete" if available else "partial",
            None
            if available
            else (
                "one or more named variants or role expansions require unavailable "
                "native columns or exceed their declared bounds"
            ),
        )


class RetainedNamedRules:
    """One operation-scoped index shared by every block projection in a selected view."""

    def __init__(self, layers):
        self.nodes = {}
        self.occurrences = {}
        self.annotations = []
        self._decoded = {}
        for pin, report in layers.items():
            if report.reference(pin.task_id) != pin:
                raise ValueError("named match projection requires exact retained layers")
            body = report.payload
            for annotation in body["annotations"]:
                self.nodes[AnnotationReference(pin, annotation["local_id"])] = annotation
                if "named_match" in annotation:
                    self.annotations.append(
                        (AnnotationReference(pin, annotation["local_id"]), annotation)
                    )
            self.occurrences.update((o["local_id"], o) for o in body["occurrences"])

    def match(self, product, *, rules):
        return self._decode(product, rules)[0]

    def _decode(self, product, rules):
        key = (product.dependency_digest, tuple(rule_identity(rule) for rule in rules))
        if key not in self._decoded:
            self._decoded[key] = _project_named_matches(self, product, rules=rules)
        return self._decoded[key]

    def references(self, product, *, rules):
        _result, refs, _nominations = self._decode(product, rules)
        if any(len(origins) != 1 for origins in refs.values()):
            raise ValueError(
                "named match has competing retained primary origins; select one exact revision"
            )
        return {match: origins[0] for match, origins in refs.items()}

    def nominations(self, product, *, rules):
        _result, _refs, nominations = self._decode(product, rules)
        return {match: dict(roles) for match, roles in nominations.items()}


def retained_named_matches(layers, product, *, rules):
    """Read exact released matches. This performs no native reconstruction or matching."""
    inventory = layers if isinstance(layers, RetainedNamedRules) else RetainedNamedRules(layers)
    return inventory.match(product, rules=rules)


def _project_named_matches(inventory, product, *, rules):
    nodes, occurrences = inventory.nodes, inventory.occurrences
    expected = {(rule.rule, rule.variant): rule_identity(rule) for rule in rules}
    current_container = None

    def native(ref):
        found = nodes.get(AnnotationReference(ProductReference(**ref["layer"]), ref["local_id"]))
        if found is None or "native_token" not in found:
            raise ValueError("retained named binding has no exact original native token")
        if current_container is not None and (
            ref["layer"] != current_container["layer"]
            or found["native_token"]["container"] != current_container["local_id"]
        ):
            raise ValueError("retained named binding refers to another native container")
        return found

    def spans(refs):
        result = []
        for ref in refs:
            row = native(ref)
            extents = [e for oid in row["occurrences"] for e in occurrences[oid]["extents"]]
            result.append((min(e["start"] for e in extents), max(e["end"] for e in extents)))
        return tuple(result)

    matches = []
    availability = {}
    references = {}
    nominations = {}
    for origin, annotation in inventory.annotations:
        body = annotation.get("named_match")
        if body is None or body["dependency_digest"] != product.dependency_digest:
            continue
        key = (body["rule"], body["variant"])
        if key not in expected or annotation.get("rule_id") != expected[key]:
            continue
        current_container = body["native_container"]
        expected_container = f"spacy/{product.source.source_view_id}/{product.block_id}/block"
        container = nodes.get(
            AnnotationReference(
                ProductReference(**current_container["layer"]), current_container["local_id"]
            )
        )
        if (
            current_container["local_id"] != expected_container
            or container is None
            or container.get("kind") != "native.block"
        ):
            raise ValueError("named match native container differs from selected annotation block")
        if annotation["kind"] == "construction.named_availability":
            state = body["status"]
            if key in availability and availability[key] != state:
                raise ValueError("retained named variant has competing availability")
            availability[key] = state
            continue
        if annotation["kind"] != "construction.named_binding":
            continue
        roles = []
        for role in body["bindings"]:
            roles.append(
                LocatedRole(
                    role["role"],
                    role["node"],
                    native(role["head"])["native_token"]["index"],
                    role["expansion"],
                    tuple(native(ref)["native_token"]["index"] for ref in role["members"]),
                    spans(role["members"]),
                    role["status"],
                    role.get("reason"),
                )
            )
        token_nodes = tuple(native(ref)["native_token"]["index"] for ref in body["nodes"])
        source_extents = tuple(sorted(set(spans(body["nodes"]))))
        sentences = {row["token_index"]: row.get("sentence") for row in body["sentences"]}
        negative = tuple(
            (
                min(e["start"] for e in occurrences[oid]["extents"]),
                max(e["end"] for e in occurrences[oid]["extents"]),
            )
            for oid in body["negation_occurrences"]
        )
        match = AnnotationRuleMatch(
            body["rule"],
            body["variant"],
            body["mechanism"],
            token_nodes,
            source_extents,
            tuple(body["piece_indices"]),
            tuple(sentences[index] for index in token_nodes),
            body["dependency_digest"],
            tuple(roles),
            body["protocol"],
            negative,
        )
        matches.append(match)
        references.setdefault(match, []).append(origin)
        for binding in body["bindings"]:
            if "antecedent_status" not in binding:
                continue
            refs = binding.get("antecedent_members", ())
            antecedent_nodes = tuple(native(ref)["native_token"]["index"] for ref in refs)
            context_start = None
            if antecedent_nodes:
                sentence = product.tokens[antecedent_nodes[0]].sentence
                if sentence is None:
                    raise ValueError(
                        "resolved naming antecedent lacks its original native sentence context"
                    )
                context_start = product.sentences[sentence].start
            nomination = NamedNomination(
                binding.get("demonstrative"),
                binding["antecedent_status"],
                antecedent_nodes,
                spans(refs),
                context_start,
                binding.get("antecedent_reason"),
            )
            recorded = nominations.setdefault(match, {})
            if binding["role"] in recorded and recorded[binding["role"]] != nomination:
                raise ValueError("named match has competing retained naming nominations")
            recorded[binding["role"]] = nomination
    if set(availability) != set(expected):
        raise ValueError(
            "requested named variants were not produced in the selected primary layers"
        )
    result = AnnotationRuleResult(
        tuple(dict.fromkeys(matches)),
        tuple((r.rule, r.variant, availability[r.rule, r.variant]) for r in rules),
    )
    return (
        result,
        {match: tuple(dict.fromkeys(refs)) for match, refs in references.items()},
        nominations,
    )
