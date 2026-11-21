"""Primary execution and pure retained projection of configured named native rules."""

from __future__ import annotations

from typing import Any

from corpus_structure.ingest.annotation_views import annotation_view

from .named_nominations import naming_nomination
from .nodes import identity

NAMED_FAMILY = "construction.named_rules"
NAMED_VOCABULARY = "named-annotation-match-2"


def rule_identity(rule):
    return identity(
        "named-rule", rule.model_dump(mode="json") if hasattr(rule, "model_dump") else rule
    )


def populate_named_products(
    layer,
    view,
    source,
    native,
    prepared,
    *,
    annotation_products=None,
    check_active=lambda: None,
    admitted=lambda a, b: True,
):
    """Interpret actual detached native blocks, with governed product/member addresses."""
    from corpus_structure.semantic.data_product_reference import (
        DataProductReference,
        member_reference,
    )
    from corpus_structure.semantic.sentence_products import (
        retained_source_annotation_products,
        source_annotation_member_values,
    )

    products = (
        retained_source_annotation_products(source, native)
        if annotation_products is None
        else annotation_products
    )
    pin = DataProductReference(native.semantic_id)
    tokens = {
        (row["block_id"], row["ordinal"]): row
        for row in source_annotation_member_values(native)
        if row["record_type"] == "token"
    }

    def blocks():
        for product in products:
            native_view = annotation_view(
                product,
                view.text[product.block_start : product.block_end],
                prepared.vocab,
                required=(),
            )
            refs = {
                index: member_reference(pin, row["local_id"]).values()
                for (owner, index), row in tokens.items()
                if owner == product.block_id
            }

            def occurrences(index, *, product=product):
                token = product.tokens[index]
                return [layer.occurrence(view, token.start, token.end)]

            yield (
                product,
                native_view,
                dict(product_id=pin.product_id, block_id=product.block_id),
                refs,
                occurrences,
            )

    _populate_named_blocks(
        layer, view, pin, prepared, blocks(), check_active=check_active, admitted=admitted
    )


def _populate_named_blocks(layer, view, native_pin, prepared, blocks, *, check_active, admitted):
    rules = {(r.rule, r.variant): r for r in prepared.rules}
    for product, native, container, token_refs, token_occurrences in blocks:
        check_active()
        selector = dict(
            projection=layer.scope["selectors"][0]["projection"],
            start=product.block_start,
            end=product.block_end,
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
                external_premises=[],
            )
        for match in result.matches:
            declaration = rules[match.rule, match.variant]

            def token(index, *, container=container, token_refs=token_refs):
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
                external_premises=body["nodes"],
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
                    occurrences = token_occurrences(
                        next(index for index, ref in token_refs.items() if ref == endpoint)
                    )
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
