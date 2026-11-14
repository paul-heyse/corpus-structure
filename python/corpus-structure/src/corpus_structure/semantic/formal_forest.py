"""Direct native mathematical SPPF reduction into the common retained symbolic DAG.

This is a semantic consumer of the existing mathematical frontend, not a new grammar.
Unsupported formal productions retain positioned syntax and unknown symbolic nodes.
No callback constructs SymPy values, expands complete trees or chooses an interpretation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from lark import Token
from lark.exceptions import VisitError

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.semantic.constructions.nodes import Reference, identity
from corpus_structure.semantic.constructions.reuse import ReusingForestTransformer

VOCABULARY = "formal-math-symbolic-1"
FAMILY = "formal.math"
_RELATIONS = dict(
    eq="equals",
    ne="not_equals",
    lt="less_than",
    lte="less_or_equal",
    gt="greater_than",
    gte="greater_or_equal",
)
_BINARY = dict(
    mul=("multiply", ("left", "cue", "right")),
    div=("divide", ("numerator", "cue", "denominator")),
    adjacent_expressions=("multiply", ("left", "right")),
    superscript=("power", ("base", "cue", "exponent")),
    _basic_fraction=("divide", ("cue", "numerator", "denominator")),
    _simple_fraction=("divide", ("cue", "numerator", "denominator")),
    _general_fraction=("divide", ("cue", "numerator", "denominator")),
)
_IDENTITIES = frozenset(
    {"any_value", "formula", "relation", "set_expr", "set_atom", "fraction", "set_named"}
)
_GROUPS = frozenset(
    {
        "group_round_parentheses",
        "group_curly_parentheses",
        "group_square_brackets",
        "script_group",
        "set_group",
    }
)
_SET_OPERATORS = frozenset(
    {"set_union", "set_intersection", "set_minus", "set_product", "set_written_product"}
)


class FormalPackedReducer(ReusingForestTransformer):
    def __init__(
        self,
        text: str,
        *,
        region: str,
        check_active=lambda: None,
        max_nodes: int = 20000,
        macros: Mapping[str, MacroDef] | None = None,
    ):
        super().__init__(check_active=check_active, max_nodes=max_nodes)
        self.text, self.region = text, region
        self.macros = dict(macros or {})
        self.terms: dict[str, dict[str, Any]] = {}
        self.choices: dict[str, dict[str, Any]] = {}
        self.syntax: dict[str, dict[str, Any]] = {}
        self.positions: dict[str, tuple[int, int]] = {}
        self.sequences: dict[str, tuple[Reference, ...]] = {}
        self.uninterpreted: set[str] = set()
        self.symbols: dict[str, dict[str, Any]] = {}
        self.symbol_outcome = "not_requested"

    def term(
        self,
        value: str,
        kind: str,
        children: list[dict[str, Any]],
        start: int,
        end: int,
        *,
        status: str,
        production: str,
    ) -> Reference:
        row = dict(
            kind=kind,
            family=FAMILY,
            vocabulary=VOCABULARY,
            value=value,
            status=status,
            children=children,
            premises=[production],
        )
        key = identity("formal-term", [self.region, start, end, row])
        self.terms.setdefault(key, dict(local_id=key, **row))
        self.positions[key] = start, end
        return Reference(target=key)

    def transform_token_node(self, node: Token):
        token = node
        start, end = token.start_pos, token.end_pos
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(self.text):
            raise ValueError("native mathematical terminal has no exact represented position")
        key = identity("formal-terminal", [self.region, token.type, start, end, str(token)])
        formal = dict(node_kind="token", rule=token.type, start=start, end=end)
        for field in ("line", "column", "end_line", "end_column"):
            value = getattr(token, field, None)
            if type(value) is int:
                formal[field] = value
        self.syntax[key] = dict(local_id=key, native_label=token.type, formal=formal, children=[])
        return self.term(
            str(token), "participant", [], start, end, status="unknown", production=key
        )

    def transform_packed_node(self, node, data):
        name = str(node.rule.alias or node.rule.origin.name)
        partial = node.parent.is_intermediate
        expanded = list(data)
        if expanded and expanded[0].target in self.sequences:
            expanded = [*self.sequences[expanded[0].target], *expanded[1:]]
        child_spans = []
        for child in expanded:
            key = child.target or child.choice_group
            assert key is not None
            child_spans.append(self.positions[key])
        start = min((a for a, _b in child_spans), default=node.parent.start)
        end = max((b for _a, b in child_spans), default=node.parent.end)
        container_start, container_end = node.parent.start, node.parent.end
        if not 0 <= container_start <= start <= end <= container_end <= len(self.text):
            raise ValueError(
                "native mathematical production container does not enclose its members"
            )
        pointer = node.parent.s[1] if partial else len(node.rule.expansion)
        production = identity(
            "formal-production",
            [
                self.region,
                str(node.rule),
                pointer,
                start,
                end,
                [(child.target, child.choice_group) for child in expanded],
            ],
        )
        formal = dict(
            node_kind="rule",
            rule=str(node.rule),
            start=start,
            end=end,
            container_start=container_start,
            container_end=container_end,
        )
        if start == end:
            formal["synthetic"] = True
        self.syntax[production] = dict(
            local_id=production,
            native_label=name,
            formal=formal,
            children=expanded,
            rule_id=identity("formal-rule", [str(node.rule), pointer]),
        )
        roles = [f"part_{index}" for index in range(len(expanded))]
        kind, value, status = "unknown", "uninterpreted:" + name, "unknown"
        structural_sequence = partial or name.startswith("__")
        if structural_sequence:
            kind, value, status = "operator", "@sequence", "interpreted"
        elif len(expanded) == 1 and (name in _IDENTITIES or name.startswith("_")):
            kind, value, status, roles = "operator", "identity", "interpreted", ["content"]
        elif name in _GROUPS and len(expanded) == 3:
            kind, value, status, roles = (
                "operator",
                "group",
                "interpreted",
                ["open", "content", "close"],
            )
        elif name == "number":
            value, kind, roles = self.text[start:end], "participant", ["lexeme"] * len(expanded)
            try:
                status = "interpreted" if Decimal(value).is_finite() else "unknown"
            except ValueError, ArithmeticError:
                status = "unknown"
        elif name in {
            "_one_letter_symbol",
            "_sym_base",
            "multi_letter_symbol",
            "sub_symbol",
            "styled",
            "symbol_prime",
        }:
            kind, value, status = "participant", "symbol:" + self.text[start:end], "unknown"
        elif name in {"add", "sub"} and len(expanded) in {2, 3}:
            kind, status = "operator", "interpreted"
            value = (
                ("positive" if name == "add" else "negate")
                if len(expanded) == 2
                else ("add" if name == "add" else "subtract")
            )
            roles = ["cue", "operand"] if len(expanded) == 2 else ["left", "cue", "right"]
        elif name in _BINARY and len(expanded) == len(_BINARY[name][1]):
            kind, value, status = "operator", _BINARY[name][0], "interpreted"
            roles = list(_BINARY[name][1])
        elif name in _RELATIONS and len(expanded) == 3:
            kind, value, status, roles = (
                "predicate",
                _RELATIONS[name],
                "interpreted",
                ["left", "cue", "right"],
            )
        elif name == "member" and len(expanded) == 3:
            kind, value, status, roles = (
                "predicate",
                "membership",
                "interpreted",
                ["member", "cue", "set"],
            )
        elif name in {"function_applied", "op_applied"} and len(expanded) == 4:
            kind, value, status, roles = (
                "operator",
                "application",
                "interpreted",
                ["function", "open", "arguments", "close"],
            )
        elif name == "interval" and len(expanded) == 5:
            kind, value, status, roles = (
                "operator",
                "interval",
                "interpreted",
                ["open", "lower", "separator", "upper", "close"],
            )
        elif name in _SET_OPERATORS and len(expanded) == 3:
            kind, value, status, roles = "operator", name, "interpreted", ["left", "cue", "right"]
        elif name in {"tuple", "list_of_expressions", "set_list", "empty_set"}:
            kind, value, status = "operator", name, "interpreted"
        if status == "unknown" and not (kind == "participant" and value.startswith("symbol:")):
            self.uninterpreted.add(name)
        edges = [
            child.edge(role, index)
            for index, (child, role) in enumerate(zip(expanded, roles, strict=True))
        ]
        result = self.term(value, kind, edges, start, end, status=status, production=production)
        if partial and result.target:
            self.sequences[result.target] = tuple(expanded)
        return result

    def _symbol(self, node, data):
        roots = tuple(dict.fromkeys(data))
        if not roots:
            raise ValueError("native mathematical symbol has no completed derivation")
        if len(roots) == 1:
            return roots[0]
        if any(root.target is None for root in roots):
            raise ValueError("formal packed alternative must have its own term root")
        key = identity(
            "formal-choice",
            [self.region, str(node.s), node.start, node.end, [root.target for root in roots]],
        )
        members = []
        for root in roots:
            member = identity("formal-alternative", [key, root.target])
            members.append(dict(local_id=member, root=root.target))
        self.choices[key] = dict(
            local_id=key, compatibility="exclusive", family=FAMILY, members=members
        )
        spans = [self.positions[root.target] for root in roots]
        self.positions[key] = min(a for a, _b in spans), max(b for _a, b in spans)
        return Reference(choice_group=key)

    transform_symbol_node = _symbol
    transform_intermediate_node = _symbol

    def symbol_occurrences(self, root: Reference) -> None:
        """Project qualified symbol uses from actual packed derivations, without trees.

        A shared base terminal is suppressed only while visiting that composite's
        base role. A rival path can therefore retain a distinct supported base use.
        Each result cites its actual term/derivation and local choice witness.
        """
        branches = {}
        for group in self.choices.values():
            for member in group["members"]:
                branches.setdefault(member["root"], []).append(member["local_id"])
        self.symbol_outcome = "partial"
        incomplete = False
        pending: list[tuple[Reference, str | None, str | None]] = [(root, None, root.target)]
        seen = set()
        while pending:
            ref, parent, witness = pending.pop()
            state = (ref, parent, witness)
            if state in seen:
                continue
            seen.add(state)
            if len(seen) % 64 == 0:
                self.check_active()
            if ref.choice_group is not None:
                pending.extend(
                    (Reference(target=member["root"]), parent, member["root"])
                    for member in self.choices[ref.choice_group]["members"]
                )
                continue
            assert ref.target is not None
            term = self.terms[ref.target]
            production = term["premises"][0]
            syntax = self.syntax[production]
            name, formal = syntax["native_label"], syntax["formal"]
            children = syntax["children"]
            token_symbol = formal["node_kind"] == "token" and name in {
                "SYMBOL",
                "GREEK_SYMBOL_WITH_PRIMES",
            }
            composite = formal["node_kind"] == "rule" and name in {
                "sub_symbol",
                "sup_sub",
                "styled",
                "multi_letter_symbol",
                "pi_constant",
            }
            symbol = None
            if token_symbol or composite:
                spelling = tex.token_form(self.text[formal["start"] : formal["end"]], self.macros)
                symbol = identity(
                    "formal-symbol", [self.region, formal["start"], formal["end"], spelling, parent]
                )
                required = list(
                    dict.fromkeys(
                        [
                            *branches.get(ref.target, ()),
                            *branches.get(witness, ()),
                            *(
                                self.symbols[parent].get("required_choices", ())
                                if parent is not None
                                else ()
                            ),
                        ]
                    )
                )
                premises = list(
                    dict.fromkeys(
                        [production, ref.target, *([witness] if witness is not None else [])]
                    )
                )
                support = dict(
                    member=witness or ref.target, premises=premises, required_choices=required
                )
                existing = self.symbols.get(symbol)
                if existing is None:
                    self.symbols[symbol] = dict(
                        local_id=symbol,
                        formal=dict(
                            node_kind="rule",
                            rule="symbol-occurrence-v1",
                            start=formal["start"],
                            end=formal["end"],
                            normalized=dict(
                                kind="identifier", value=spelling, domain_status="not_requested"
                            ),
                            **({"symbol_parent": parent} if parent is not None else {}),
                        ),
                        premises=premises,
                        required_choices=required,
                        supports=[support],
                    )
                elif support not in existing["supports"]:
                    existing["supports"].append(support)
                    existing["premises"] = list(dict.fromkeys([*existing["premises"], *premises]))
                    existing["required_choices"] = [
                        choice for choice in existing["required_choices"] if choice in required
                    ]
            if composite and name in {"styled", "multi_letter_symbol", "pi_constant"}:
                continue
            if composite and name in {"sub_symbol", "sup_sub"}:
                expected = 3 if name == "sub_symbol" else 5
                if len(children) == expected:
                    pending.append((children[-1], symbol, witness))
                    if name == "sup_sub":
                        pending.append((children[2], parent, witness))
                    # The base is part of this qualified symbol use; a distinct rival
                    # derivation remains independently reachable through its own path.
                    continue
                self.uninterpreted.add("symbol-membership:" + name)
                incomplete = True
            if name == "op_name":
                continue
            pending.extend((child, parent, witness) for child in children)
        self.symbol_outcome = "partial" if incomplete else "complete"


@dataclass(frozen=True, slots=True)
class FormalRecognition:
    reading: grammar.MathForestResult
    root: Reference | None
    reducer: FormalPackedReducer | None
    interpretation: str
    diagnostic: dict[str, Any] | None = None


def recognize_formal(
    latex: str,
    kind: grammar.Kind,
    *,
    region: str,
    seconds: float,
    max_nodes: int = 20000,
    check_active=lambda: None,
    macros: Mapping[str, MacroDef] | None = None,
) -> FormalRecognition:
    """One existing main-thread deadline covers recognition, retry and direct reduction."""
    grammar.require_main_thread()
    reading = grammar.MathForestResult(latex, kind, ParseOutcome.FAILED)
    reducer = None
    try:
        with grammar.deadline(seconds):
            check_active()
            reading = grammar.syntax_forest(latex, kind, macros=macros, seconds=seconds)
            if reading.forest is None:
                return FormalRecognition(reading, None, None, "not_requested")
            reducer = FormalPackedReducer(
                latex, region=region, check_active=check_active, max_nodes=max_nodes, macros=macros
            )
            root = reducer.transform(reading.forest)
            if not isinstance(root, Reference):
                raise ValueError("native formal reduction has no completed symbolic reference")
            reducer.symbol_occurrences(root)
            check_active()
            if reducer.uninterpreted:
                return FormalRecognition(
                    reading,
                    root,
                    reducer,
                    "unresolved",
                    dict(
                        category="unsupported_formal_semantics",
                        message="Uninterpreted formal productions retained: "
                        + ", ".join(sorted(reducer.uninterpreted)),
                    ),
                )
            return FormalRecognition(
                reading, root, reducer, "unresolved" if reducer.choices else "resolved"
            )
    except grammar.Expired:
        return FormalRecognition(
            reading,
            None,
            reducer,
            "failed",
            dict(category="timeout", message="Formal recognition/reduction deadline expired."),
        )
    except Exception as error:
        cause = error.orig_exc if isinstance(error, VisitError) else error
        return FormalRecognition(
            reading,
            None,
            reducer,
            "failed",
            dict(category="semantic_callback", message=f"{type(cause).__name__}: {cause}"),
        )


def _factored_native_alternatives(values, *, inline):
    """Keep one local choice; private-rule sequences factor only at one differing slot."""
    from copy import copy

    from lark import Tree

    if not values:
        return None
    first = values[0]
    if all(value == first for value in values[1:]):
        return first
    if inline:
        if not all(
            isinstance(value, Tree)
            and isinstance(first, Tree)
            and value.data == first.data
            and len(value.children) == len(first.children)
            for value in values
        ):
            return None
        different = [
            index
            for index in range(len(first.children))
            if any(value.children[index] != first.children[index] for value in values[1:])
        ]
        if len(different) != 1:
            return None
        index = different[0]
        child = _factored_native_alternatives(
            [value.children[index] for value in values], inline=False
        )
        children = list(first.children)
        children[index] = child
        return Tree(first.data, children, copy(first.meta))
    return Tree("_ambig", list(values), copy(first.meta) if isinstance(first, Tree) else None)


def retained_math_syntax(
    layers,
    view,
    pointer: str,
    latex: str,
    *,
    macros=None,
    kind: grammar.Kind = "any_value",
    max_nodes=20000,
):
    """Restore a factored native working DAG with the original Lark callbacks.

    Callback inlining/filtering is the installed library's responsibility. No parse
    call or Cartesian ambiguity expander runs. Local choices remain available to
    the existing contextual resolver. Correlated private sequences that cannot be
    factored remain explicitly unavailable, never independently recombined.
    """
    candidates = []
    for pin, report in layers.items():
        if report.reference(pin.task_id) != pin:
            raise ValueError("native mathematical syntax requires exact retained layer pins")
        body = report.payload
        selected = [
            row
            for row in body["source_scope"]["source_views"]
            if row["source_view_id"] == view.ref.id
        ]
        if not selected:
            continue
        if (
            len(selected) != 1
            or body["base_document"] != view.ref.native_product.values()
            or selected[0]["projection_digest"] != view.ref.projection_digest
            or selected[0]["recipe_digest"] != view.ref.recipe_digest
        ):
            raise ValueError("retained mathematical syntax differs from exact source")
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for root in body["annotations"]:
            inp = root.get("formal_input")
            if inp is None or inp["representation"] != "recognized_latex" or inp["text"] != latex:
                continue
            parent = occurrences[inp["parent_occurrence"]]
            if not any(
                e["native_pointer"] == pointer
                and e["source_view_id"] == view.ref.id
                and e["projection"] == view.ref.projection_digest
                for e in parent["extents"]
            ):
                continue
            candidates.append((body, root))
    return _restore_math_syntax(candidates, latex, macros=macros, kind=kind, max_nodes=max_nodes)


def _restore_math_syntax(
    candidates, latex, *, macros=None, kind="any_value", max_nodes=20000, semantic=False
):
    """Shared retained DAG/callback restoration after the owning source lookup."""
    from lark import Tree
    from lark.parse_tree_builder import ParseTreeBuilder

    from .formal_evidence import macro_identity, math_grammar_identity

    table = dict(macros or {})
    classes = grammar.classify(table)
    base = grammar.MathResult(latex, kind, ParseOutcome.FAILED, macros=table, classes=classes)
    if len(candidates) != 1:
        category = "ambiguous_primary_input" if candidates else "missing_primary_input"
        return replace(base, failure=grammar.Failure(category, "PrimarySyntaxUnavailable"))
    body, root = candidates[0]
    inp = root["formal_input"]
    expected_grammar = "formal-math" if semantic else math_grammar_identity(table)
    if inp["macro_identity"] != macro_identity(table) or inp["grammar"] != expected_grammar:
        return replace(
            base, failure=grammar.Failure("primary_grammar_drift", "PrimarySyntaxUnavailable")
        )
    if inp["start_symbol"] != kind:
        return replace(
            base, failure=grammar.Failure("primary_start_mismatch", "PrimarySyntaxUnavailable")
        )
    if inp["syntax_outcome"] not in {"complete", "partial", "ambiguous"}:
        diagnostic = inp.get("diagnostic", {})
        return replace(
            base,
            failure=grammar.Failure(
                diagnostic.get("category", "primary_syntax_unavailable"),
                "PrimarySyntaxUnavailable",
                diagnostic.get("position"),
            ),
        )
    terms = {row["local_id"]: row for row in body["terms"]}
    annotations = {row["local_id"]: row for row in body["annotations"]}
    choices = {row["local_id"]: row for row in body["choices"]}
    readings = [
        row
        for row in terms.values()
        if row.get("value") == "formal-reading" and row.get("premises") == [root["local_id"]]
    ]
    if len(readings) != 1 or len(readings[0].get("children", ())) != 1:
        return replace(
            base, failure=grammar.Failure("missing_primary_derivation", "PrimarySyntaxUnavailable")
        )
    parser = grammar.forest_parser_for(classes).lark
    # Lark's ambiguous=True callback builder performs Cartesian expansion; keep it
    # disabled and factor only correlation-preserving private sequences ourselves.
    callbacks = ParseTreeBuilder(
        parser.rules, Tree, propagate_positions=True, ambiguous=False, maybe_placeholders=False
    ).create_callback()
    rules = {}
    for rule in parser.rules:
        rules.setdefault((str(rule), rule.alias or rule.origin.name), []).append(rule)
    memo = {}
    active = set()
    origins = {}

    class PackedRival(Exception):
        pass

    def restore(edge):
        if "choice_group" in edge:
            group = choices[edge["choice_group"]]
            cache_key = ("choice", group["local_id"])
            if cache_key in memo:
                return memo[cache_key]
            if cache_key in active or len(memo) + len(active) >= max_nodes:
                raise ValueError("retained native syntax is cyclic or exceeds its node bound")
            active.add(cache_key)
            roots = [member["root"] for member in group["members"]]
            values = [restore(dict(target=root)) for root in roots]
            private = [origins.get(root, "").startswith("_") for root in roots]
            if any(private) and not all(private):
                raise PackedRival
            result = _factored_native_alternatives(values, inline=all(private))
            if result is None:
                raise PackedRival
            active.remove(cache_key)
            memo[cache_key] = result
            return result
        key = edge["target"]
        if key in memo:
            return memo[key]
        if key in active or len(memo) + len(active) >= max_nodes:
            raise ValueError("retained native syntax is cyclic or exceeds its node bound")
        active.add(key)
        term = terms[key]
        productions = [
            annotations[p]
            for p in term.get("premises", ())
            if p in annotations and "formal" in annotations[p]
        ]
        if len(productions) != 1:
            raise ValueError("retained mathematical term lacks one native syntax premise")
        syntax = productions[0]
        formal = syntax["formal"]
        if formal["input_id"] != root["local_id"]:
            raise ValueError("retained derivation crosses formal inputs")
        if formal["node_kind"] == "token":
            a, b = formal["start"], formal["end"]
            result = Token(
                formal["rule"],
                latex[a:b],
                start_pos=a,
                end_pos=b,
                line=formal.get("line"),
                column=formal.get("column"),
                end_line=formal.get("end_line"),
                end_column=formal.get("end_column"),
            )
        else:
            matches = rules.get((formal["rule"], syntax["native_label"]), ())
            if len(matches) != 1:
                raise ValueError("retained production differs from frozen native grammar")
            rule = matches[0]
            origins[key] = rule.origin.name
            if syntax.get("rule_id") != identity("formal-rule", [str(rule), len(rule.expansion)]):
                raise ValueError("retained native derivation contains an incomplete production")
            children = [restore(child) for child in term.get("children", ())]
            if len(children) != len(rule.expansion):
                raise ValueError("retained native production lost its exact grammar children")
            from copy import copy

            # Installed Lark ChildFilterLALR may reuse and append to child.children;
            # PropagatePositions also writes root metadata. Copy these wrappers only,
            # retaining the shared immutable descendants rather than cloning trees.
            local = [
                Tree(child.data, list(child.children), copy(child.meta))
                if isinstance(child, Tree)
                else child
                for child in children
            ]
            result = callbacks[rule](local)
        active.remove(key)
        memo[key] = result
        return result

    try:
        tree = restore(readings[0]["children"][0])
    except PackedRival:
        return replace(
            base,
            status=ParseOutcome.AMBIGUOUS,
            kind="ambiguous",
            failure=grammar.Failure("packed_primary_ambiguity", "PrimarySyntaxRequiresChoice"),
        )
    except (KeyError, ValueError, IndexError) as error:
        return replace(
            base,
            failure=grammar.Failure(
                "primary_derivation_unavailable", "PrimarySyntaxUnavailable", detail=str(error)
            ),
        )
    if not isinstance(tree, Tree):
        return replace(
            base, failure=grammar.Failure("primary_root_not_tree", "PrimarySyntaxUnavailable")
        )
    position = inp.get("diagnostic", {}).get("position")
    tail = latex[position:] if inp["syntax_outcome"] == "partial" and type(position) is int else ""
    diagnostic = inp.get("diagnostic", {})
    failure = (
        grammar.Failure(
            diagnostic.get("category", "primary_partial_syntax"),
            "PrimaryPartialSyntax",
            diagnostic.get("position"),
            detail=diagnostic.get("message"),
        )
        if inp["syntax_outcome"] == "partial"
        else None
    )
    return replace(
        base,
        status=ParseOutcome.AMBIGUOUS
        if any(node.data == "_ambig" for node in tree.iter_subtrees())
        else ParseOutcome.PARTIAL
        if inp["syntax_outcome"] == "partial"
        else ParseOutcome.OK,
        kind=grammar._detect(tree) if kind == "any_value" else kind,
        tree=tree,
        tail=tail,
        failure=failure,
    )


class SourceNativeMathReadings:
    """One source's retained formal inputs, without task/view identities or recognition.

    The parent authenticates the nominal products and their selected native support.
    This index preserves their actual coordinate and member references for consumers.
    """

    def __init__(self, source, products):
        from .data_product_reference import DataProductReference

        selected = source.value
        coordinate = selected["source"]
        self._inputs = {}
        self._coordinate = coordinate
        for product in products:
            value = product.value.model_dump(mode="json", exclude_unset=True)
            if value["source"] != coordinate:
                raise ValueError("retained mathematical product belongs to another source")
            body = product.inventory()
            occurrences = {row["local_id"]: row for row in body["occurrences"]}
            pin = DataProductReference(product.semantic_id)
            for root in body["annotations"]:
                inp = root.get("formal_input")
                if inp is None or inp["representation"] != "recognized_latex":
                    continue
                parent = occurrences[inp["parent_occurrence"]]
                for extent in parent["extents"]:
                    if (
                        "source_view_id" in extent
                        or extent["projection"] != coordinate["projection"]
                    ):
                        raise ValueError("retained mathematical extent differs from its source")
                    pointer = extent.get("native_pointer")
                    if pointer is not None:
                        self._inputs.setdefault((pointer, inp["text"]), []).append(
                            (pin, body, root)
                        )

    def syntax(self, pointer, latex, *, macros=None, kind="any_value", max_nodes=20000):
        return _restore_math_syntax(
            [(body, root) for _, body, root in self._inputs.get((pointer, latex), ())],
            latex,
            macros=macros,
            kind=kind,
            max_nodes=max_nodes,
            semantic=True,
        )

    def inventory(self, pointer, latex, *, macros=None):
        return _math_inventory(
            self._inputs.get((pointer, latex), ()), latex, macros=macros, semantic=True
        )


def retained_math_inventory(layers, view, pointer, latex, *, macros=None):
    """Read raw positioned constituents and packing without a private lexical walk."""
    from .formal_evidence import macro_identity, math_grammar_identity

    candidates = []
    for pin, report in layers.items():
        if report.reference(pin.task_id) != pin:
            raise ValueError("primary mathematical inventory differs from exact pin")
        body = report.payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for row in body["annotations"]:
            inp = row.get("formal_input")
            if inp is None or inp["representation"] != "recognized_latex" or inp["text"] != latex:
                continue
            extents = occurrences[inp["parent_occurrence"]]["extents"]
            if not any(
                e["native_pointer"] == pointer
                and e["source_view_id"] == view.ref.id
                and e["projection"] == view.ref.projection_digest
                for e in extents
            ):
                continue
            if (
                body["base_document"] != view.ref.native_product.values()
                or inp["macro_identity"] != macro_identity(macros)
                or inp["grammar"] != math_grammar_identity(macros)
            ):
                raise ValueError(
                    "primary mathematical inventory differs from frozen source or macros"
                )
            candidates.append((pin, body, row))
    return _math_inventory(candidates, latex, macros=macros)


def _math_inventory(candidates, latex, *, macros=None, semantic=False):
    from .data_product_reference import member_reference
    from .formal_evidence import macro_identity, math_grammar_identity

    if len(candidates) != 1:
        return dict(
            outcome="unavailable",
            input=None,
            nodes=[],
            lexical=[],
            choices=[],
            issues=["exact primary mathematical input is missing or competing"],
        )
    pin, body, root = candidates[0]
    inp = root["formal_input"]
    expected_grammar = "formal-math" if semantic else math_grammar_identity(macros)
    if inp["macro_identity"] != macro_identity(macros) or inp["grammar"] != expected_grammar:
        raise ValueError("primary mathematical inventory differs from frozen macros")
    rows = [
        row
        for row in body["annotations"]
        if row.get("formal", {}).get("input_id") == root["local_id"]
    ]
    ids = {row["local_id"] for row in rows}
    nodes = [
        dict(
            primary_node=member_reference(pin, row["local_id"]).values(),
            kind=row["kind"],
            formal=row["formal"],
            parts=[
                dict(role=m["role"], member=m["member"], order=m["order"])
                for m in body["memberships"]
                if m["group"] == row["local_id"] and m["role"] == "part"
            ],
        )
        for row in rows
    ]
    tokens = [
        dict(
            kind=row["formal"]["rule"],
            text=latex[row["formal"]["start"] : row["formal"]["end"]],
            start=row["formal"]["start"],
            end=row["formal"]["end"],
            primary_node=member_reference(pin, row["local_id"]).values(),
        )
        for row in rows
        if row["formal"]["node_kind"] == "token"
    ]
    terms = {
        row["local_id"]
        for row in body["terms"]
        if any(key in ids for key in row.get("premises", ()))
    }
    choices = [
        group
        for group in body["choices"]
        if any(member["root"] in terms for member in group["members"])
    ]
    return dict(
        outcome=root["formal_input"]["syntax_outcome"],
        input=member_reference(pin, root["local_id"]).values(),
        nodes=nodes,
        lexical=sorted(tokens, key=lambda t: (t["start"], t["end"], t["kind"])),
        choices=choices,
        issues=[root["formal_input"]["diagnostic"]]
        if root["formal_input"].get("diagnostic")
        else [],
    )
