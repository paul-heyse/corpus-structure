"""Independent math position, source-rule and native-tree scope criteria.

These call current declared kernels over actual formal products. Curated binder
cues are explicit pure input values; they assert no NLP or native CPU custody.
"""

from dataclasses import replace
from typing import Any

import pytest
from semantic.declared_math_support import _inputs, _role, selected_symbolic_fixture
from semantic.declared_math_support import math_profile as math_profile
from semantic.formal_products_support import selected

from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.declared import (
    DeclaredMathNormalization,
    DeclaredMathOccurrences,
    DeclaredMathScope,
)
from corpus_structure.semantic.construction_products import (
    ConstructionOptions,
    PreparedConstructionProfile,
)
from corpus_structure.semantic.constructions.math_scope import (
    FAMILY,
    Binders,
    NativeDomainRule,
    policy_identity,
)
from corpus_structure.semantic.constructions.nodes import identity
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_math_products import DeclaredMathOptions, PreparedMathInputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.math_context import acquire_analysis_context_profile


def occurrence(profile, source, options=None, *, inherited=(), parents=(), constructions=None):
    source, formal, source_pin, formal_pin = _inputs(profile, source)
    roles = (
        _role("source", (source_pin,)),
        _role("formal", (formal_pin,)),
        _role("inherited", tuple(pin for pin, body in inherited)),
        _role("ancestor_sources", tuple(pin for pin, body in parents)),
    )
    if constructions is not None:
        roles += (
            _role(
                "constructions",
                (
                    replace(
                        formal_pin,
                        product="product:curated-domain-cues"
                        if isinstance(constructions, dict)
                        else constructions.semantic_id,
                    ),
                ),
            ),
        )
    inputs = PreparedMathInputs(
        profile.prepared,
        roles,
        "outside-statistics",
        options or DeclaredMathOptions(),
        acquire_analysis_context_profile(),
        lambda: None,
    )
    result = DeclaredMathOccurrences(inputs).run(
        source.value,
        formal.value.model_dump(mode="json", exclude_unset=True),
        inherited=tuple(body for pin, body in inherited),
        ancestor_sources=tuple(body for pin, body in parents),
        constructions=None
        if constructions is None
        else constructions
        if isinstance(constructions, dict)
        else constructions.value.model_dump(mode="json", exclude_unset=True),
    )
    return inputs, source, source_pin, formal_pin, result


def source_values(profile, parts, *, section="#/groups/0", ancestors=(), items=None, health=None):
    text, pieces, nodes, recognition = "", [], [], []
    for index, (label, value) in enumerate(parts):
        pointer = "#/texts/" + str(index)
        nodes.append(
            {"self_ref": pointer, "label": label, "text": value, "orig": value, "parent": section}
        )
        pieces.append(
            {
                "kind": "native_text",
                "item_ref": pointer,
                "source_field": "text",
                "start": len(text),
                "end": len(text) + len(value),
            }
        )
        text += value
        if label == "formula":
            recognition.append(
                {"pointer": pointer, "outcome": (health or {}).get(pointer, "succeeded")}
            )
    return selected(
        profile,
        text,
        source={
            "document": "document:original-content",
            "section_pointer": section,
            "membership": "descendants",
            "projection": "pending",
        },
        pieces=pieces,
        items=[
            {
                "self_ref": section,
                "label": "section",
                "children": [node["self_ref"] for node in nodes],
            },
            *nodes,
        ]
        if items is None
        else items,
        ancestors=list(ancestors),
        recognition=recognition,
        selectors=[
            {"projection": "pending", "native_pointer": section, "start": 0, "end": len(text)}
        ],
    )


def binder_cues(source, binders, ranges):
    """Independent literal sentence/initial positions, using the existing cue format."""
    text, pieces = source.value["text"], source.value["pieces"]
    projection = source.value["source"]["projection"]
    policy = policy_identity(binders, ())
    members: list[dict[str, Any]] = []
    extents = {"all": (0, len(text))}
    for index, (start, end) in enumerate(ranges):
        extents["sentence:" + str(index)] = (start, end)
        extents["initial:" + str(index)] = (start, start + 3)
    for name, (start, end) in extents.items():
        members.append(
            {
                "body": {
                    "record_type": "occurrence",
                    "local_id": "o:" + name,
                    "extents": [
                        {
                            "projection": projection,
                            "native_pointer": piece["item_ref"],
                            "start": max(start, piece["start"]),
                            "end": min(end, piece["end"]),
                            "text": text[max(start, piece["start"]) : min(end, piece["end"])],
                        }
                        for piece in pieces
                        if piece["start"] < end and start < piece["end"]
                    ],
                }
            }
        )
    members.append(
        {
            "body": {
                "record_type": "annotation",
                "local_id": "a:policy",
                "kind": "math.scope_policy",
                "family": FAMILY,
                "rule_id": policy,
                "occurrences": ["o:all"],
            }
        }
    )
    for index, _ in enumerate(ranges):
        sentence, initial = "sentence:" + str(index), "initial:" + str(index)
        for name, kind in ((sentence, "scope_sentence"), (initial, "scope_initial")):
            members.append(
                {
                    "body": {
                        "record_type": "annotation",
                        "local_id": "a:" + name,
                        "kind": "math." + kind,
                        "family": FAMILY,
                        "rule_id": identity("math-source-sentences", [])
                        if kind == "scope_sentence"
                        else policy,
                        "occurrences": ["o:" + name],
                    }
                }
            )
        members.append(
            {
                "body": {
                    "record_type": "membership",
                    "local_id": "m:" + initial,
                    "group": "a:" + initial,
                    "role": "sentence",
                    "member": "a:" + sentence,
                }
            }
        )
    return {
        "source": source.value["source"],
        "selectors": source.value["selectors"],
        "members": members,
        "coverage": [
            {
                "family": FAMILY,
                "availability": "available",
                "outcome": "complete",
                "examined": [{"projection": projection, "start": 0, "end": len(text)}],
                "unexamined": [],
            }
        ],
    }


def normalize_and_scope(inputs, source, source_pin, formal_pin, original, cues):
    occurrence_pin = replace(formal_pin, product="product:actual-occurrences")
    normalizer = replace(
        inputs, roles=(_role("source", (source_pin,)), _role("occurrences", (occurrence_pin,)))
    )
    normalized = DeclaredMathNormalization(normalizer).run(source.value, original)
    scoped = DeclaredMathScope(
        replace(
            inputs,
            roles=(
                _role("source", (source_pin,)),
                _role("occurrences", (occurrence_pin,)),
                _role("symbolic", (selected_symbolic_fixture(occurrence_pin),)),
                _role("constructions", (replace(formal_pin, product="product:curated-cues"),)),
                _role("inherited", ()),
                _role("ancestor_sources", ()),
            ),
        )
    ).run(source.value, original, normalized, cues)
    return normalized, scoped


def test_current_reading_owners_keep_literal_offsets_and_reuse_retained_tree(
    math_profile, monkeypatch
):
    source = source_values(
        math_profile,
        (
            ("text", "Let "),
            ("formula", "x"),
            ("text", ". Then "),
            ("formula", "x+x"),
            ("text", "."),
        ),
    )
    binders = Binders(sentence_initial=("let",))
    from corpus_structure.methods.math.prepared import PreparedMathInput

    with monkeypatch.context() as weak:
        weak.setattr(
            PreparedMathInput, "symbolic_value", lambda *_: pytest.fail("unasked symbolic work")
        )
        values = occurrence(math_profile, source, DeclaredMathOptions(math_scope_binders=binders))
    inputs, source, source_pin, formal_pin, original = values
    offsets = {piece["item_ref"]: piece["start"] for piece in source.value["pieces"]}
    spans = [
        (item["pointer"], symbol["start"], symbol["end"])
        for item in original["items"]
        for symbol in item["occurrences"]
    ]
    assert spans == [("#/texts/1", 0, 1), ("#/texts/3", 0, 1), ("#/texts/3", 2, 3)]
    assert [
        (offsets[pointer] + start, offsets[pointer] + end) for pointer, start, end in spans
    ] == [(4, 5), (12, 13), (14, 15)]
    with monkeypatch.context() as retained:
        retained.setattr(
            grammar, "syntax", lambda *_a, **_kw: pytest.fail("consumer reparsed primary syntax")
        )
        normalized, scoped = normalize_and_scope(
            inputs,
            source,
            source_pin,
            formal_pin,
            original,
            binder_cues(source, binders, ((0, 6),)),
        )
    assert [row["symbolic"]["expression"] for row in normalized["items"]] == [
        "Symbol('x')",
        "Mul(Integer(2), Symbol('x'))",
    ]
    assert [row["outcome"] for row in scoped["items"]] == ["resolved"] * 3
    assert all(row["binding_pointer"] == "#/texts/1" for row in scoped["items"])
    assert all(
        row["binding_input"]["product_id"] == "product:actual-occurrences"
        for row in scoped["items"]
    )


def domain_cues(source, rules, markers=()):
    """Explicit unadmitted source-marker values; never a computed native receipt."""
    projection = source.value["source"]["projection"]
    policy = policy_identity(None, rules)
    members: list[dict[str, Any]] = []
    for index, piece in enumerate(source.value["pieces"]):
        if piece["kind"] != "native_text":
            continue
        occurrence = "o:" + str(index)
        members.append(
            {
                "body": {
                    "record_type": "occurrence",
                    "local_id": occurrence,
                    "extents": [
                        {
                            "projection": projection,
                            "native_pointer": piece["item_ref"],
                            "start": piece["start"],
                            "end": piece["end"],
                            "text": source.value["text"][piece["start"] : piece["end"]],
                        }
                    ],
                }
            }
        )
        members.append(
            {
                "body": {
                    "record_type": "annotation",
                    "local_id": "a:" + str(index),
                    "kind": "math.domain_examined",
                    "family": FAMILY,
                    "rule_id": policy,
                    "occurrences": [occurrence],
                }
            }
        )
        for pointer, rule in markers:
            if pointer != piece["item_ref"]:
                continue
            marker = "marker:" + str(index)
            members.append(
                {
                    "body": {
                        "record_type": "annotation",
                        "local_id": marker,
                        "kind": "math.domain_marker",
                        "family": FAMILY,
                        "rule_id": policy,
                        "native_label": pointer,
                        "occurrences": [occurrence],
                    }
                }
            )
            for role, value in rule.model_dump(mode="json").items():
                term = marker + ":" + role
                members.append({"body": {"record_type": "term", "local_id": term, "value": value}})
                members.append(
                    {
                        "body": {
                            "record_type": "membership",
                            "local_id": "m:" + term,
                            "group": marker,
                            "role": role,
                            "member": term,
                        }
                    }
                )
    return {
        "source": source.value["source"],
        "selectors": source.value["selectors"],
        "members": members,
        "coverage": [
            {
                "family": FAMILY,
                "availability": "available",
                "outcome": "complete",
                "examined": [
                    {"projection": projection, "start": 0, "end": len(source.value["text"])}
                ],
                "unexamined": [],
            }
        ],
    }


def test_current_domain_markers_are_explicit_source_rules_without_proof_truth(math_profile):
    from types import SimpleNamespace

    from corpus_structure.methods.math.native import domain_blocks_columns
    from corpus_structure.semantic.constructions.math_scope import retained_math_scope_products
    from corpus_structure.semantic.declared_record_sources import native_language_items

    source = source_values(math_profile, (("section_header", "Proof."), ("text", " Details.")))
    source, formal, source_pin, _ = _inputs(math_profile, source)
    context = SubjectContext(
        "outside-statistics",
        source_pin.subject,
        source_pin.original_source,
        source_pin.analyzed_scope,
        subject_definition=source_pin.subject_definition,
    )
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    construction = PreparedConstructionProfile(
        math_profile.prepared, bound_data_operation_model(math_profile.prepared)
    ).run(
        source, (formal,), ConstructionOptions(math_domain_rules=(rule,)), subject_context=context
    )
    unavailable = retained_math_scope_products((construction,), source, binders=None, rules=(rule,))
    assert not unavailable.complete  # Missing native sentence annotations stay unknown.
    values = domain_cues(source, (rule,), (("#/texts/0", rule),))
    primary = retained_math_scope_products(
        (
            SimpleNamespace(
                semantic_id="product:curated-domain-cues", content=canonical_bytes(values)
            ),
        ),
        source,
        binders=None,
        rules=(rule,),
    )
    args = dict(
        root="#/groups/0",
        text=source.value["text"],
        items=native_language_items(source.value["items"]),
        ancestors=(),
        pieces=source.value["pieces"],
    )
    assert domain_blocks_columns(**args, rules=()) == ()
    with pytest.raises(ValueError, match="complete primary source-marker coverage"):
        domain_blocks_columns(**args, rules=(rule,), primary_scope=unavailable)
    (block,) = domain_blocks_columns(**args, rules=(rule,), primary_scope=primary)
    assert block[2] == "#/texts/0" and block[3].rule_id == "proof-heading-1"
    assert "proven" not in construction.content.decode()
    from corpus_structure.methods.math.declared import declared_math_readings
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.math_context import prepare_interpretation_context

    frame = DeclaredNativeFrameSource.acquire(
        math_profile.prepared, source.value, source_pin, project="outside-statistics"
    )
    kernel = dict(
        prepared=math_profile.prepared,
        prepare_context=lambda **kw: prepare_interpretation_context(
            context_profile=acquire_analysis_context_profile(), **kw
        ),
    )
    with pytest.raises(ValueError, match="explicitly bound primary scope blocks"):
        declared_math_readings(
            frame, (formal,), DeclaredMathOptions(math_domain_rules=(rule,)), **kernel
        )
    assert (
        declared_math_readings(
            frame, (formal,), DeclaredMathOptions(math_domain_rules=(rule,)), blocks=(), **kernel
        )
        == ()
    )


def descendant_source(profile):
    root = {"self_ref": "#/groups/0", "label": "section", "children": []}
    rows: list[dict[str, Any]] = [root]
    pieces = []
    parts = []
    offset = 0
    formulas = {}

    def group(ref, parent):
        value = {
            "self_ref": ref,
            "label": "section",
            "parent": parent["self_ref"],
            "children": [],
        }
        parent["children"].append(ref)
        rows.append(value)
        return value

    def add(text, parent, formula=None):
        nonlocal offset
        pointer = f"#/texts/{len(pieces)}"
        value = {
            "self_ref": pointer,
            "label": "text" if formula is None else "formula",
            "text": text,
            "orig": text,
            "parent": parent["self_ref"],
        }
        parent["children"].append(pointer)
        rows.append(value)
        pieces.append(
            dict(
                kind="native_text",
                item_ref=pointer,
                source_field="text",
                start=offset,
                end=offset + len(text),
            )
        )
        parts.append(text)
        offset += len(text)
        if formula is not None:
            formulas[formula] = pointer

    add("Let ", root)
    add("x", root, "root_x")
    add(". ", root)
    add("f(t)=t", root, "root_f")
    add(". ", root)
    child = group("#/groups/1", root)
    add("Let ", child)
    add("y", child, "child_y")
    add(". ", child)
    add("g(t)=t", child, "child_g")
    add(". ", child)
    add("f(2)", child, "child_f_call")
    add(". ", child)
    add("g(2)", child, "child_g_call")
    add(". ", child)
    grandchild = group("#/groups/2", child)
    add("y", grandchild, "grandchild_y")
    add(". ", grandchild)
    add("g(2)", grandchild, "grandchild_g_call")
    add(". ", grandchild)
    sibling = group("#/groups/3", root)
    add("x", sibling, "sibling_x")
    add(". ", sibling)
    add("y", sibling, "sibling_y")
    add(". ", sibling)
    add("f(2)", sibling, "sibling_f_call")
    add(". ", sibling)
    add("g(2)", sibling, "sibling_g_call")
    add(".", sibling)
    text = "".join(parts)
    source = selected(
        profile,
        text,
        items=rows,
        pieces=pieces,
        recognition=[{"pointer": pointer, "outcome": "succeeded"} for pointer in formulas.values()],
        selectors=[
            {"projection": "pending", "native_pointer": "#/groups/0", "start": 0, "end": len(text)}
        ],
    )
    return source, formulas


def test_current_descendant_tree_preserves_roles_without_sibling_leakage(math_profile, monkeypatch):
    source, formulas = descendant_source(math_profile)
    binders = Binders(sentence_initial=("let",))
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    values = occurrence(
        math_profile,
        source,
        DeclaredMathOptions(math_scope_binders=binders, math_domain_rules=(rule,)),
        constructions=domain_cues(source, (rule,)),
    )
    inputs, source, source_pin, formal_pin, original = values
    outcomes = {row["pointer"]: row["outcome"] for row in original["items"]}
    assert {
        name: outcomes[formulas[name]]
        for name in (
            "child_f_call",
            "child_g_call",
            "grandchild_g_call",
            "sibling_f_call",
            "sibling_g_call",
        )
    } == {
        "child_f_call": "ok",
        "child_g_call": "ok",
        "grandchild_g_call": "ok",
        "sibling_f_call": "ok",
        "sibling_g_call": "ambiguous",
    }
    text = source.value["text"]
    ranges = []
    offset = 0
    while (start := text.find("Let ", offset)) >= 0:
        end = text.index(".", start) + 1
        ranges.append((start, end))
        offset = end
    monkeypatch.setattr(
        grammar, "syntax", lambda *_a, **_kw: pytest.fail("scope reparsed retained syntax")
    )
    cues = binder_cues(source, binders, ranges)
    domain = domain_cues(source, (rule,))
    # Binder policy binds the same exact finite domain-rule set.
    binder_policy = policy_identity(binders, (rule,))
    for packet in cues["members"]:
        if packet["body"].get("rule_id") == policy_identity(binders, ()):
            packet["body"]["rule_id"] = binder_policy
    cues["members"].extend(domain["members"])
    _, scoped = normalize_and_scope(inputs, source, source_pin, formal_pin, original, cues)
    results = {row["pointer"]: row for row in scoped["items"] if row["symbol"] in {"x", "y"}}
    assert results[formulas["sibling_x"]]["outcome"] == "resolved"
    assert results[formulas["sibling_x"]]["scope_pointer"] == "#/groups/0"
    assert results[formulas["grandchild_y"]]["outcome"] == "resolved"
    assert results[formulas["grandchild_y"]]["scope_pointer"] == "#/groups/1"
    assert results[formulas["sibling_y"]]["outcome"] == "unresolved"


@pytest.mark.parametrize("health", ["failed", "unknown"])
def test_current_partial_recognition_preserves_known_items_without_complete_context(
    math_profile, health
):
    source = source_values(
        math_profile,
        (("formula", "x"), ("text", " "), ("formula", "y")),
        health={"#/texts/2": health},
    )
    inputs, source, pin, formal_pin, original = occurrence(math_profile, source)
    assert original["outcome"] == "partial"
    assert len(original["items"]) == 1 and original["items"][0]["pointer"] == "#/texts/0"
    from corpus_structure.methods.math.declared import selected_formula_inputs

    assert selected_formula_inputs(source)[0] == {"#/texts/0", "#/texts/2"}
    assert source.value["recognition"][1]["outcome"] == health
    normalized = DeclaredMathNormalization(
        replace(
            inputs,
            roles=(
                _role("source", (pin,)),
                _role("occurrences", (replace(formal_pin, product="actual-occurrences"),)),
            ),
        )
    ).run(source.value, original)
    assert normalized["outcome"] == "partial" and len(normalized["items"]) == 1
    assert normalized["items"][0]["symbolic"]["expression"] == "Symbol('x')"


def native_nodes_source(profile, section, nodes, *, ancestors=()):
    text, pieces, recognition = "", [], []
    for node in nodes:
        if "text" not in node:
            continue
        value = node["text"]
        pieces.append(
            {
                "kind": "native_text",
                "item_ref": node["self_ref"],
                "source_field": "text",
                "start": len(text),
                "end": len(text) + len(value),
            }
        )
        text += value
        if node["label"] == "formula":
            recognition.append({"pointer": node["self_ref"], "outcome": "succeeded"})
    return selected(
        profile,
        text,
        source={
            "document": "document:original-content",
            "section_pointer": section,
            "membership": "direct",
            "projection": "pending",
        },
        items=nodes,
        ancestors=list(ancestors),
        pieces=pieces,
        recognition=recognition,
        selectors=[
            {"projection": "pending", "native_pointer": section, "start": 0, "end": len(text)}
        ],
    )


@pytest.mark.parametrize("proof", [False, True])
def test_current_ancestor_function_roles_flow_only_forward_outside_proofs(math_profile, proof):
    root = {
        "self_ref": "#/groups/0",
        "label": "section_header",
        "children": ["#/texts/0", "#/texts/1", "#/groups/1", "#/texts/2"],
    }
    child_group = {
        "self_ref": "#/groups/1",
        "label": "section_header",
        "parent": "#/groups/0",
        "children": ["#/texts/3", "#/texts/4"],
    }
    before = {
        "self_ref": "#/texts/1",
        "label": "formula",
        "text": "f(x)=x",
        "orig": "f(x)=x",
        "parent": "#/groups/0",
    }
    after = {
        "self_ref": "#/texts/2",
        "label": "formula",
        "text": "g(x)=x",
        "orig": "g(x)=x",
        "parent": "#/groups/0",
    }
    heading = {
        "self_ref": "#/texts/0",
        "label": "section_header",
        "text": "Proof." if proof else "Functions.",
        "parent": "#/groups/0",
    }
    parent = native_nodes_source(math_profile, "#/groups/0", [root, heading, before, after])
    _source, _formal, parent_pin, _ = _inputs(math_profile, parent)
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    options = DeclaredMathOptions(math_domain_rules=(rule,))
    _, _, parent_pin, parent_formal, parent_result = occurrence(
        math_profile,
        parent,
        options,
        constructions=domain_cues(parent, (rule,), (("#/texts/0", rule),) if proof else ()),
    )
    child = native_nodes_source(
        math_profile,
        "#/groups/1",
        [
            child_group,
            {
                "self_ref": "#/texts/3",
                "label": "formula",
                "text": "f(2)",
                "orig": "f(2)",
                "parent": "#/groups/1",
            },
            {
                "self_ref": "#/texts/4",
                "label": "formula",
                "text": "g(2)",
                "orig": "g(2)",
                "parent": "#/groups/1",
            },
        ],
        ancestors=(root,),
    )
    inherited_pin = replace(parent_formal, product="product:parent-occurrences", member=None)
    _, _, _, _, child_result = occurrence(
        math_profile,
        child,
        inherited=((inherited_pin, parent_result),),
        parents=((parent_pin, parent.value),),
    )
    outcomes = {item["pointer"]: item["outcome"] for item in child_result["items"]}
    assert outcomes == {"#/texts/3": "ambiguous" if proof else "ok", "#/texts/4": "ambiguous"}
    declarations = [
        row
        for item in child_result["items"]
        for row in item["context"]["declarations"]
        if row["authority"] == "source"
    ]
    assert {row["symbol"] for row in declarations} == (set() if proof else {"f"})
