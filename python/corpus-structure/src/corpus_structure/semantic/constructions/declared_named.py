"""Retained named bindings addressed by genuine semantic product/member references."""

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
        self.annotations = annotations
        self.native = {
            packet["member_id"]: packet["body"]
            for packet in json.loads(annotations.content)["members"]
        }
        self.blocks = {row["block_id"] for row in self.native.values() if "block_id" in row}
        self.matches = []
        self.occurrences = {}
        self._decoded = {}
        source = json.loads(annotations.content)
        for product in constructions:
            body = json.loads(product.content)
            if body["source"] != source["source"] or body["selectors"] != source["selectors"]:
                raise ValueError("named products differ from their exact native source and scope")
            inventory = product.inventory()
            for occurrence in inventory["occurrences"]:
                identifier = occurrence["local_id"]
                if identifier in self.occurrences and self.occurrences[identifier] != occurrence:
                    raise ValueError("named products contain competing original occurrences")
                self.occurrences[identifier] = occurrence
            for row in inventory["annotations"]:
                if "named_match" not in row:
                    continue
                container = row["named_match"]["native_container"]
                if (
                    container["product_id"] != annotations.semantic_id
                    or container["block_id"] not in self.blocks
                ):
                    raise ValueError("named binding lacks its actual selected native block")
                self.matches.append(
                    (
                        DeclaredPrimaryReference(
                            product_id=product.semantic_id, member_id=row["local_id"]
                        ),
                        row,
                    )
                )

    def decode(self, product):
        key = (product.block_id, product.dependency_digest)
        if key not in self._decoded:
            self._decoded[key] = self._decode(product)
        return self._decoded[key]

    def _decode(self, product):
        matches, availability, references, nominations, rule_ids = [], {}, {}, {}, {}
        container = {"product_id": self.annotations.semantic_id, "block_id": product.block_id}

        def token(ref):
            body = self.native.get(ref["member_id"])
            if (
                ref["product_id"] != self.annotations.semantic_id
                or body is None
                or body.get("record_type") != "native_token"
                or body["block_id"] != product.block_id
            ):
                raise ValueError("named binding lacks its exact native token member")
            index = body["ordinal"]
            if index >= len(product.tokens) or (
                product.tokens[index].start,
                product.tokens[index].end,
            ) != (body["start"], body["end"]):
                raise ValueError("named binding changes original native token coordinates")
            return body

        def spans(refs):
            return tuple((token(ref)["start"], token(ref)["end"]) for ref in refs)

        for origin, annotation in self.matches:
            body = annotation["named_match"]
            if body["native_container"] != container:
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
            roles = tuple(
                LocatedRole(
                    role["role"],
                    role["node"],
                    token(role["head"])["ordinal"],
                    role["expansion"],
                    tuple(token(ref)["ordinal"] for ref in role["members"]),
                    spans(role["members"]),
                    role["status"],
                    role.get("reason"),
                )
                for role in body["bindings"]
            )
            indices = tuple(token(ref)["ordinal"] for ref in body["nodes"])
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
                tuple(sorted(set(spans(body["nodes"])))),
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
            for binding in body["bindings"]:
                if "antecedent_status" not in binding:
                    continue
                refs = binding.get("antecedent_members", ())
                nodes = tuple(token(ref)["ordinal"] for ref in refs)
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
                    spans(refs),
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
