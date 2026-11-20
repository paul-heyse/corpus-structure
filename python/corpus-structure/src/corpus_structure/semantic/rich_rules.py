"""Current release-derived typed rule language and policy compilation.

Scientific execution and publication are separate owners. This module acquires no
execution catalog, historical run, task or cut.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType

from .refusal_types import SemanticRefusal
from .refusals import SemanticOperationRefusal, SemanticReason
from .rich_knowledge_sources import RULE_INPUT, VERSION, parse_policy_yaml
from .types import PreparedRelease


class RichRulePolicyRefused(SemanticRefusal):
    """The actual captured domain policy cannot provide the requested typed rules."""


def prepared_rich_rule_policy(prepared: PreparedRelease) -> RichRulePolicy:
    """Release-owned preparation; no document, selected-input or invocation state."""
    artifact = next((item for item in prepared.artifacts if item.kind == RULE_INPUT), None)
    if artifact is None:
        raise RichRulePolicyRefused("release has no declared domain rules operation")
    key = "rich-rule-policy:" + artifact.digest
    with prepared._adapter_lock:
        if key not in prepared._relational_preparations:
            prepared._relational_preparations[key] = RichRulePolicy(prepared)
        return prepared._relational_preparations[key]


class RichRulePolicy:
    """The existing rule language and finalize decision table over release-derived views."""

    version = VERSION

    def __init__(self, prepared: PreparedRelease):
        from corpus_structure.schema.rulelang import BUILTIN, Builtin, Vocabulary

        from .rule_views import build_rule_language

        self.prepared = prepared
        self.release_id = prepared.release_id
        artifact = next((a for a in prepared.artifacts if a.kind == RULE_INPUT), None)
        if artifact is None:
            raise RichRulePolicyRefused("release has no declared domain rules operation")
        self.source = parse_policy_yaml(artifact.content) or {}
        if not isinstance(self.source, dict):
            raise RichRulePolicyRefused("domain rule artifact is not an object")
        self.definitions = {d.name: d for d in prepared.definitions}
        self.metadata = {}
        for row in prepared.registry_rows:
            if row.kind == "operation_property":
                body = json.loads(row.body)
                self.metadata[body["class"], body["property"]] = body
        from .comparison_projection import comparison_projection

        self.comparison_projection = comparison_projection(prepared)
        self.prefixes = {
            row.name: json.loads(row.body)["uri"]
            for row in prepared.registry_rows
            if row.kind == "prefix"
        }
        self._is_a = MappingProxyType(
            {
                definition.iri: frozenset(
                    {
                        definition.iri,
                        *(
                            self.definitions[name].iri
                            for name in definition.ancestors
                            if name in self.definitions
                        ),
                    }
                )
                for definition in prepared.definitions
            }
        )
        self.validate_source()
        self.version = self.source["operation"]["version"]
        self.enums = {}
        for row in prepared.registry_rows:
            if row.kind == "enum_definition":
                body = json.loads(row.body)
                enum_uri = body.get("enum_uri")
                if enum_uri:
                    self.enums[self.compact(prepared.expand_name(enum_uri))] = tuple(
                        prepared.enum_members(row.name)
                    )
        # Classes, qualifier schemas and memberships come from the same immutable binding.
        from .statement_types import effective_bindings

        qualification = effective_bindings(prepared)["qualification"]
        qprops = (
            {p.name: p for p in self.definitions[qualification].properties} if qualification else {}
        )
        self.qprops = qprops
        builtins = {
            "enums": Builtin(self.enums, "map[list[string]]"),
            "is_a": Builtin(self.is_a, "function(list[string], string)->boolean"),
        }
        for name, values in self.source.get("tables", {}).items():
            if all(isinstance(v, list) for v in values.values()):
                typ = "map[list[string]]"
            elif all(isinstance(v, str) for v in values.values()):
                typ = "map[string]"
            else:
                raise RichRulePolicyRefused("unsupported released rule lookup table")
            builtins[name] = Builtin(values, typ)
        classes = frozenset(self.compact(d.iri) for d in prepared.definitions)
        predicates = frozenset(
            self.compact(p.iri) for d in prepared.definitions for p in d.properties
        )
        groups = frozenset(g for row in self.metadata.values() for g in row.get("groups", ()))
        values = {
            ("Claim", "predicate"): Vocabulary("predicates", predicates),
            ("Claim", "groups"): Vocabulary("predicate subsets", groups),
            ("Entity", "types"): Vocabulary("entity classes", classes),
            ("Claim", "establishment"): Vocabulary(
                "Establishment", frozenset(prepared.enum_members("Establishment"))
            ),
        }
        from .statement_types import statement_kinds as bound_statement_kinds

        statement_kinds = Vocabulary("StatementKind", bound_statement_kinds(prepared))
        statement_roles = Vocabulary(
            "StatementRole", frozenset(prepared.enum_members("StatementRole"))
        )
        values[("Claim", "statement_kind")] = statement_kinds
        values[("Statement", "kind")] = statement_kinds
        values[("Claim", "statement_role")] = statement_roles
        values[("Value", "t")] = Vocabulary(
            "Value discriminators",
            frozenset(
                p.equals_string
                for d in prepared.definitions
                if d.name == "Value" or "Value" in d.ancestors
                for p in d.properties
                if p.name == "kind" and p.equals_string
            ),
        )
        values[("Binding", "bind")] = Vocabulary(
            "ExpressionBinding kinds",
            frozenset(
                p.equals_string
                for d in prepared.definitions
                if d.name == "ExpressionBinding" or "ExpressionBinding" in d.ancestors
                for p in d.properties
                if p.name == "kind" and p.equals_string
            ),
        )
        keys = {
            (BUILTIN, name): Vocabulary("keys of $" + name, frozenset(builtin.value))
            for name, builtin in builtins.items()
            if isinstance(builtin.value, Mapping)
        }
        keys[("Entity", "identity")] = Vocabulary(
            "identity slots",
            frozenset(
                self.compact(prop.iri)
                for definition in prepared.definitions
                if definition.name == "Entity" or "Entity" in definition.ancestors
                for group in definition.identity_groups
                for prop in definition.properties
                if prop.name in group
            ),
        )
        for prop in qprops.values():
            if prop.range in {
                row.name for row in prepared.registry_rows if row.kind == "enum_definition"
            }:
                values["Qualifiers", prop.name] = Vocabulary(
                    prop.range, frozenset(prepared.enum_members(prop.range))
                )
        self.language = build_rule_language(
            prepared,
            qprops=qprops,
            builtins=builtins,
            values=values,
            keys=keys,
            arguments={"is_a": (Vocabulary("classes", classes), Vocabulary("classes", classes))},
            views=self.source.get("views", {}),
        )
        rules = []
        seen = set()
        for section in ("rules", "guideline"):
            for raw in self.source.get(section, ()):
                rid = raw["id"]
                if rid in seen:
                    raise RichRulePolicyRefused("duplicate released rule id")
                seen.add(rid)
                if "finalize" not in raw.get("at", ("batch", "finalize")):
                    continue
                rules.append(
                    (
                        raw,
                        self.language.compile(rid, raw.get("when", "true")),
                        self.language.compile(rid, raw["check"]),
                    )
                )

        from .native_source_view import freeze_native

        self.source = freeze_native(self.source)
        self.metadata = freeze_native(self.metadata)
        self.definitions = MappingProxyType(self.definitions)
        self.prefixes = MappingProxyType(self.prefixes)
        self.enums = MappingProxyType(self.enums)
        self.qprops = MappingProxyType(self.qprops)
        self.rules = tuple((freeze_native(raw), when, check) for raw, when, check in rules)

    def validate_source(self):
        from .alias_policy import label_normalizer
        from .analytical_kernels import ALTERNATIVE_OF, SAME_SLOT, ViewSpec

        source = self.source
        if set(source) - {
            "rules",
            "guideline",
            "views",
            "tables",
            "derive",
            "identity",
            "operation",
            "rule_view_abi",
        }:
            raise RichRulePolicyRefused("unknown domain operation policy section")
        from .rule_views import RULE_VIEW_ABI

        if source.get("rule_view_abi") != RULE_VIEW_ABI:
            raise SemanticOperationRefusal(
                SemanticReason(
                    "incompatible_bindings",
                    "evaluate",
                    self.prepared.release_id,
                    expected=RULE_VIEW_ABI,
                    actual=source.get("rule_view_abi"),
                )
            )
        if source.get("operation") != {"name": "semantic-domain", "version": VERSION}:
            raise RichRulePolicyRefused("unsupported domain operation name/version")
        if source.get("derive"):
            raise RichRulePolicyRefused(
                "operation derive rules require an admitted inference profile"
            )
        identity = source.get("identity", {})
        if not isinstance(identity, dict) or set(identity) - {
            "aliases",
            "alias_profile",
            "alias_contexts",
        }:
            raise RichRulePolicyRefused("invalid operation identity policy")
        label_normalizer(self.prepared)
        props = {p.iri for d in self.prepared.definitions for p in d.properties}
        groups = {g for body in self.metadata.values() for g in body.get("groups", ())}

        def applies(value):
            values = [value] if isinstance(value, str) else value
            if (
                not isinstance(values, (tuple, list))
                or not values
                or any(not isinstance(v, str) for v in values)
            ):
                raise RichRulePolicyRefused("invalid rule applies_to")
            selected = set()
            for token in values:
                if token == "any":
                    selected.update(props)
                elif token.startswith("subset:"):
                    group = token[7:]
                    if group not in groups:
                        raise RichRulePolicyRefused("unknown operation predicate subset " + group)
                    selected.update(
                        body["property"]
                        for body in self.metadata.values()
                        if group in body.get("groups", ())
                    )
                else:
                    iri = self.prepared.expand_name(token)
                    if iri not in props:
                        raise RichRulePolicyRefused("unknown operation predicate " + token)
                    selected.add(iri)
            return selected

        for section in ("rules", "guideline"):
            if not isinstance(source.get(section, []), list):
                raise RichRulePolicyRefused("operation rules must be a list")
            for rule in source.get(section, ()):
                if not isinstance(rule, dict) or set(rule) - {
                    "id",
                    "applies_to",
                    "at",
                    "severity",
                    "when",
                    "check",
                    "description",
                }:
                    raise RichRulePolicyRefused("invalid operation rule shape")
                if (
                    not isinstance(rule.get("id"), str)
                    or not rule["id"]
                    or not isinstance(rule.get("check"), str)
                ):
                    raise RichRulePolicyRefused("operation rule requires id and check")
                sites = rule.get("at", ("batch", "finalize"))
                if (
                    not isinstance(sites, (list, tuple))
                    or not sites
                    or any(s not in {"batch", "finalize"} for s in sites)
                ):
                    raise RichRulePolicyRefused("unknown operation rule call site")
                if rule.get("severity", "error") not in {"error", "warning"}:
                    raise RichRulePolicyRefused("unknown operation rule severity")
                applies(rule.get("applies_to", "any"))
        tables = source.get("tables", {})
        if not isinstance(tables, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, dict)
            or any(not isinstance(k, str) for k in value)
            or not (
                all(isinstance(v, str) for v in value.values())
                or all(
                    isinstance(v, list) and all(isinstance(x, str) for x in v)
                    for v in value.values()
                )
            )
            for key, value in tables.items()
        ):
            raise RichRulePolicyRefused("invalid released rule lookup table")
        views = source.get("views", {})
        if not isinstance(views, dict):
            raise RichRulePolicyRefused("operation views must be a mapping")
        for name, decl in views.items():
            if (
                not isinstance(name, str)
                or not name.isidentifier()
                or name in {SAME_SLOT, ALTERNATIVE_OF}
                or not isinstance(decl, dict)
                or set(decl) - {"description", "applies_to", "source", "match", "project"}
            ):
                raise RichRulePolicyRefused("invalid operation view declaration")
            if not {"applies_to", "source", "match", "project"} <= decl.keys():
                raise RichRulePolicyRefused("incomplete operation view declaration")
            match = decl["match"]
            if (
                not isinstance(match, dict)
                or set(match) != {"source", "claim"}
                or any(v not in {"subject", "object"} for v in match.values())
            ):
                raise RichRulePolicyRefused("unknown operation view match side")
            if (
                not isinstance(decl["source"], str)
                or self.prepared.expand_name(decl["source"]) not in props
            ):
                raise RichRulePolicyRefused("unknown operation view source property")
            spec = ViewSpec.from_declaration(name, decl, applies(decl["applies_to"]))
            if spec.attr == "identity" and (
                spec.slot is None or self.prepared.expand_name(spec.slot) not in props
            ):
                raise RichRulePolicyRefused("unknown operation view identity projection")

    def compact(self, iri):
        choices = [
            (len(uri), prefix + ":" + iri[len(uri) :])
            for prefix, uri in self.prefixes.items()
            if iri.startswith(uri)
        ]
        return max(choices)[1] if choices else iri

    def is_a(self, children, parent):
        if isinstance(children, str):
            raise RichRulePolicyRefused("class membership requires its actual class collection")
        target = self.prepared.expand_name(parent)
        return any(
            target in self._is_a.get(self.prepared.expand_name(child), ()) for child in children
        )

    def applies(self, raw, *, class_name: str, predicate: str):
        source = raw.get("applies_to", "any")
        if isinstance(source, str):
            source = [source]
        groups = self.metadata.get((class_name, predicate), {}).get("groups", ())
        for token in source:
            if token == "any":
                return True
            if token.startswith("subset:"):
                if token[7:] in groups:
                    return True
            elif self.prepared.expand_name(token) == predicate:
                return True
        return False
