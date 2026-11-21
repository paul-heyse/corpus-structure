"""Retained named bindings resolved against the actual selected annotation rows."""

from __future__ import annotations

import json

from corpus_structure.methods.annotation_rules import (
    AnnotationRuleMatch,
    AnnotationRuleResult,
    LocatedRole,
)
from corpus_structure.semantic.structural_products import DeclaredPrimaryReference

from .named_nominations import NamedNomination


class DeclaredNamedRules:
    """Index the supplied immutable products once; never rerun a matcher."""

    def __init__(self, constructions, annotations):
        from ..construction_products import annotation_support_index
        from ..sentence_products import source_annotation_blocks

        self.blocks = {
            row["annotation"]["block_id"]: row["annotation"]["tokens"]
            for row in source_annotation_blocks(annotations)
        }
        self.matches = []
        self.occurrences = {}
        self._decoded = {}
        source = json.loads(annotations.content)
        for product in constructions:
            body = json.loads(product.content)
            if body["source"] != source["source"] or body["selectors"] != source["selectors"]:
                raise ValueError("named products differ from their exact native source and scope")
            support = annotation_support_index(body)
            inventory = product.inventory()
            for occurrence in inventory["occurrences"]:
                identifier = occurrence["local_id"]
                if identifier in self.occurrences and self.occurrences[identifier] != occurrence:
                    raise ValueError("named products contain competing original occurrences")
                self.occurrences[identifier] = occurrence
            for row in inventory["annotations"]:
                if "named_match" not in row:
                    continue
                if row["named_match"]["block_id"] not in self.blocks:
                    raise ValueError("named binding lacks its actual selected native block")
                self.matches.append(
                    (
                        DeclaredPrimaryReference(
                            product_id=product.semantic_id, member_id=row["local_id"]
                        ),
                        row,
                        support,
                    )
                )

    def decode(self, product):
        key = (product.block_id, product.dependency_digest)
        if key not in self._decoded:
            self._decoded[key] = self._decode(product)
        return self._decoded[key]

    def _decode(self, product):
        matches, availability, references, nominations, rule_ids = [], {}, {}, {}, {}

        def token(ref):
            retained = self.blocks[product.block_id]
            if (
                ref.role != "sentences"
                or ref.collection != "rows"
                or ref.partition_key != product.block_id
                or ref.item_key is None
                or len(ref.item_key) != 2
                or ref.item_key[0] != "token"
                or type(ref.item_key[1]) is not int
                or not 0 <= ref.item_key[1] < min(len(product.tokens), len(retained))
            ):
                raise ValueError("named binding lacks its exact native token row")
            index = ref.item_key[1]
            expected = retained[index]
            if (product.tokens[index].start, product.tokens[index].end) != (
                expected["start"],
                expected["end"],
            ):
                raise ValueError("named binding changes original native token coordinates")
            return index

        def spans(refs):
            return tuple((product.tokens[index].start, product.tokens[index].end) for index in refs)

        for origin, annotation, support in self.matches:
            body = annotation["named_match"]
            if body["block_id"] != product.block_id:
                continue
            if body["dependency_digest"] != product.dependency_digest:
                raise ValueError("named binding changes its native dependency columns")
            key = body["rule"], body["variant"]
            identifier = annotation["rule_id"]
            if key in rule_ids and rule_ids[key] != identifier:
                raise ValueError("named variant has competing authored rule identities")
            rule_ids[key] = identifier
            if annotation["kind"] == "construction.named_availability":
                if key in availability and availability[key] != body["status"]:
                    raise ValueError("named variant has competing availability")
                availability[key] = body["status"]
                continue
            if annotation["kind"] != "construction.named_binding":
                continue
            owner = annotation["local_id"]

            def indices_for(use, binding_position=None, *, owner=owner, support=support):
                return tuple(
                    token(ref) for _, ref in support.get((owner, use, binding_position), ())
                )

            def located(role, position):
                (head,) = indices_for("named_binding_head", position)
                members = indices_for("named_binding_member", position)
                return LocatedRole(
                    role["role"],
                    role["node"],
                    head,
                    role["expansion"],
                    members,
                    spans(members),
                    role["status"],
                    role.get("reason"),
                )

            roles = tuple(located(role, position) for position, role in enumerate(body["bindings"]))
            indices = indices_for("named_node")
            sentences = {row["token_index"]: row.get("sentence") for row in body["sentences"]}
            negative = tuple(
                (
                    min(extent["start"] for extent in self.occurrences[identifier]["extents"]),
                    max(extent["end"] for extent in self.occurrences[identifier]["extents"]),
                )
                for identifier in body["negation_occurrences"]
            )
            match = AnnotationRuleMatch(
                body["rule"],
                body["variant"],
                body["mechanism"],
                indices,
                tuple(sorted(set(spans(indices)))),
                tuple(body["piece_indices"]),
                tuple(sentences[index] for index in indices),
                body["dependency_digest"],
                roles,
                body["protocol"],
                negative,
            )
            if match in references and references[match] != origin:
                raise ValueError("named binding has competing actual semantic member origins")
            matches.append(match)
            references[match] = origin
            for position, binding in enumerate(body["bindings"]):
                if "antecedent_status" not in binding:
                    continue
                nodes = indices_for("named_binding_antecedent", position)
                context_start = None
                if nodes:
                    sentence = product.tokens[nodes[0]].sentence
                    if sentence is None:
                        raise ValueError("named antecedent lacks its native sentence context")
                    context_start = product.sentences[sentence].start
                nomination = NamedNomination(
                    binding.get("demonstrative"),
                    binding["antecedent_status"],
                    nodes,
                    spans(nodes),
                    context_start,
                    binding.get("antecedent_reason"),
                )
                existing = nominations.setdefault(match, {})
                if binding["role"] in existing and existing[binding["role"]] != nomination:
                    raise ValueError("named binding has competing antecedent nominations")
                existing[binding["role"]] = nomination
        if any((match.rule, match.variant) not in availability for match in matches):
            raise ValueError("named match lacks its retained variant availability")
        return (
            AnnotationRuleResult(
                tuple(dict.fromkeys(matches)),
                tuple(
                    (rule, variant, state)
                    for (rule, variant), state in sorted(availability.items())
                ),
            ),
            references,
            nominations,
            rule_ids,
        )
