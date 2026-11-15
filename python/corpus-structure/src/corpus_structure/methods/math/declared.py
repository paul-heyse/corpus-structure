"""Mathematical consumers of explicit original-relative sources and retained syntax."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.declared_math_products import (
    execute_normalization,
    execute_occurrences,
)
from corpus_structure.semantic.declared_math_scope import execute_scope
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.formal_forest import SourceNativeMathReadings
from corpus_structure.semantic.source_products import FrozenNativeSource

from . import grammar
from .native import prepare_native_readings
from .native_topology import prepare_native_topology_columns
from .pdf import formula_occurrence


def selected_formula_inputs(source: FrozenNativeSource):
    """Separate fully selected original formula atoms from clipped/unknown scope.

    Formula coordinates remain local to the recognized atom. A clipped projection
    never permits inspecting the rest of that atom as if it were selected text.
    """
    value = source.value
    index = source.selector_index()
    pieces = {}
    for piece in value["pieces"]:
        if piece.get("item_ref"):
            pieces.setdefault(piece["item_ref"], []).append(piece)
    selected, unexamined = set(), set()
    for item in value["items"]:
        if item["label"] != "formula":
            continue
        pointer = item["self_ref"]
        projected = [
            piece
            for piece in pieces.get(pointer, ())
            if value["text"][piece["start"] : piece["end"]] == item["text"]
        ]
        for selector in value["selectors"]:
            matches = index.matches(selector, pointer)
            if matches is False:
                continue
            if matches is None:
                unexamined.add(pointer)
                continue
            start, end = selector.get("start", 0), selector.get("end", len(value["text"]))
            if projected:
                if any(start <= piece["start"] < piece["end"] <= end for piece in projected):
                    selected.add(pointer)
                elif any(start < piece["end"] and piece["start"] < end for piece in projected):
                    unexamined.add(pointer)
            elif "start" not in selector and "end" not in selector:
                selected.add(pointer)
            else:
                unexamined.add(pointer)
    return frozenset(selected), frozenset(unexamined - selected)


def declared_math_readings(
    source: DeclaredNativeFrameSource,
    formal,
    configuration,
    *,
    prepared,
    prepare_context,
    inherited=(),
    context_issues=(),
    blocks=(),
    check_active=lambda: None,
):
    """Run the original occurrence kernel without a Reader or reparsing.

    The producer supplies its admitted context preparer, selected ancestor declarations and any
    unavailable-context diagnostics. Domain-rule blocks must come from the bound
    primary scope operation; this function does not discover linguistic rules.
    """
    if not isinstance(source, DeclaredNativeFrameSource):
        raise TypeError("declared mathematics requires its actual semantic source member")
    frozen = FrozenNativeSource.acquire(prepared, source.value)
    retained = SourceNativeMathReadings(frozen, tuple(formal))
    section = configuration.section()
    if section.native_domain_rules and not blocks:
        raise ValueError("native domain rules require explicitly bound primary scope blocks")
    selected, clipped = selected_formula_inputs(frozen)
    value = frozen.value
    health = {row["pointer"]: row["outcome"] for row in value["recognition"]}
    issues = tuple(
        dict.fromkeys(
            (
                *context_issues,
                *(
                    "clipped or unavailable formula scope: " + pointer
                    for pointer in sorted(clipped)
                ),
            )
        )
    )
    topology = prepare_native_topology_columns(
        root=source.section_pointer,
        text=source.text,
        items=source.items,
        ancestors=source.ancestors,
        pieces=source.pieces,
    )

    def retain(operand, pointer):
        kind = operand.kind or operand.context.kind
        if kind not in grammar.STARTS:
            raise ValueError("primary mathematical input has an unsupported start symbol")
        syntax = retained.syntax(pointer, operand.latex, macros=operand.context.macros, kind=kind)
        inventory = retained.inventory(pointer, operand.latex, macros=operand.context.macros)
        operand.retain_primary_syntax(syntax, primary_input=inventory["input"])

    readings = prepare_native_readings(
        items=source.items,
        text=source.text,
        pieces={piece["item_ref"]: piece for piece in source.pieces if piece.get("item_ref")},
        health=health,
        section=section,
        seconds=getattr(configuration, "parse_seconds", grammar.PARSE_SECONDS),
        prepared=prepared,
        source=source.source_key,
        topology=topology,
        inherited=inherited,
        context_issues=issues,
        blocks=blocks,
        occurrence=lambda item: formula_occurrence(source, item, health[item["self_ref"]]),
        retain_syntax=retain,
        selected=lambda item: item["self_ref"] in selected,
        check_active=check_active,
        prepare_context=prepare_context,
    )
    return readings


def declared_normalization_readings(
    source, records, configuration, *, prepared, prepare_context, check_active=lambda: None
):
    """Consume the exact occurrence codec without recognizing or parsing again."""
    from .native import NativeReading, _restore_reading
    from .prepared import PreparedMathInput

    if not isinstance(source, DeclaredNativeFrameSource):
        raise TypeError("normalization requires an admitted semantic source")
    positions = {item["self_ref"]: n for n, item in enumerate(source.items)}
    selected, _ = selected_formula_inputs(FrozenNativeSource.acquire(prepared, source.value))
    topology = prepare_native_topology_columns(
        root=source.section_pointer,
        text=source.text,
        items=source.items,
        ancestors=source.ancestors,
        pieces=source.pieces,
    )
    pieces = {piece["item_ref"]: piece for piece in source.pieces if piece.get("item_ref")}
    items = {item["self_ref"]: item for item in source.items}
    seen = set()
    result = []
    for record in records:
        check_active()
        pointer = record["pointer"]
        if (
            pointer in seen
            or pointer not in selected
            or record["recognized_latex"] != items[pointer]["text"]
        ):
            raise ValueError("occurrence inventory differs from selected original formula atoms")
        seen.add(pointer)
        basis = record["context"]
        context = prepare_context(
            prepared,
            macros=configuration.section().macro_table(),
            constants=configuration.section().constants,
            source_id=basis["source_id"],
            scope=basis["scope"],
            offset=positions[pointer],
            scope_chain=topology.scope_chain(pointer, basis["source_id"]),
            declarations=[d for d in basis["declarations"] if d["authority"] == "source"],
            demand="occurrences",
        )
        if context.stage_key("occurrences") != record["occurrence_basis"]:
            raise ValueError("normalization context differs from its exact occurrence input")
        operand = PreparedMathInput(
            context, record["recognized_latex"], seconds=configuration.parse_seconds
        )
        syntax = _restore_reading(record.get("raw_syntax", record), operand.latex, context)
        weak = _restore_reading(record, operand.latex, context)
        operand.retain_primary_syntax(syntax, primary_input=record.get("primary_input"))
        object.__setattr__(operand, "_reading", weak)
        operand._remember("syntax", syntax)
        operand._remember("interpretation", weak)
        operand._states["occurrences"] = operand.state("interpretation")
        piece = pieces.get(pointer)
        start = (
            None
            if piece is None or source.text[piece["start"] : piece["end"]] != operand.latex
            else piece["start"]
        )
        result.append(
            NativeReading(
                pointer, operand, operand.symbolic_reading(), start, tuple(basis.get("issues", ()))
            )
        )
    return tuple(result)


class DeclaredMathOccurrences:
    __data_operation__: ClassVar[dict] = {
        "id": "extract.math/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["project", "subject", "original-source", "analyzed-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "parameter": "source",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "parameter": "formal",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "inherited",
                "kind": "urn:corpus:math:DeclaredMathOccurrenceProduct",
                "direction": "input",
                "parameter": "inherited",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "frozen-source-set",
                    "source_set": "math-ancestors",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "ancestor_sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "parameter": "ancestor_sources",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "frozen-source-set",
                    "source_set": "math-ancestor-sources",
                    "coverage": "exact-selected-source-scope",
                },
            },
            {
                "name": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "input",
                "parameter": "constructions",
                "minimum": 0,
                "maximum": 1,
                "collection": "scalar",
                "presence": "optional",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-source-scope",
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:math:DeclaredMathOccurrenceProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'retained-formal-syntax-and-explicit-mathematical-context'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'exact-original-formula-coordinates'},
            {'kind': 'documentation', 'text': 'no-repeated-recognition'},
            {'kind': 'documentation', 'text': 'exact-retained-occurrence-context'},
        ],
        "coverage": "selected-formula-atoms-with-explicit-partial-context",
        "outcomes": ["success"],
        "precision": "exact-symbolic-with-retained-ambiguity",
        "dependencies": ["text.formal_evidence/source-native"],
        "potential_dependencies": ["text.constructions/source-native"],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "original-native-mathematical-occurrences-v1",
        "binding": {
            "operator": "scan",
            "roles": ["source", "formal", "inherited", "ancestor_sources", "constructions"],
        },
        "assets": [
            {
                "reference": "declared-mathematical-profile",
                "contract": "math/declared-profile",
                "role": "semantic-profile-and-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declared_math_products.execute_occurrences",
                "contract": "math/declared-profile",
                "role": "mathematical-kernel",
            }
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/formal_input",
                "input_role": "formal",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/inherited_inputs/*",
                "input_role": "inherited",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_math_products import resolve_math_port

        return resolve_math_port(
            prepared,
            model,
            operation,
            receiver=DeclaredMathOccurrences(None),
            phase="occurrences",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(
        self,
        source: dict,
        formal: dict,
        inherited: tuple[dict, ...] = (),
        ancestor_sources: tuple[dict, ...] = (),
        constructions: dict | None = None,
    ) -> dict:
        return execute_occurrences(self, source, formal, inherited, ancestor_sources, constructions)


class DeclaredMathNormalization:
    __data_operation__: ClassVar[dict] = {
        "id": "normalize.formula/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["project", "subject", "original-source", "analyzed-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "parameter": "source",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "occurrences",
                "kind": "urn:corpus:math:DeclaredMathOccurrenceProduct",
                "direction": "input",
                "parameter": "occurrences",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:math:DeclaredMathSymbolicProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'retained-formal-syntax-and-explicit-mathematical-context'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'exact-original-formula-coordinates'},
            {'kind': 'documentation', 'text': 'no-repeated-recognition'},
            {'kind': 'documentation', 'text': 'exact-retained-occurrence-context'},
        ],
        "coverage": "selected-formula-atoms-with-explicit-partial-context",
        "outcomes": ["success"],
        "precision": "exact-symbolic-with-retained-ambiguity",
        "dependencies": ["extract.math/declared"],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "original-native-mathematical-symbolic-v1",
        "binding": {"operator": "scan", "roles": ["source", "occurrences"]},
        "assets": [
            {
                "reference": "declared-mathematical-profile",
                "contract": "math/declared-profile",
                "role": "semantic-profile-and-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declared_math_products.execute_normalization",
                "contract": "math/declared-profile",
                "role": "mathematical-kernel",
            }
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/occurrence_input",
                "input_role": "occurrences",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_math_products import resolve_math_port

        return resolve_math_port(
            prepared,
            model,
            operation,
            receiver=DeclaredMathNormalization(None),
            phase="symbolic",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(self, source: dict, occurrences: dict) -> dict:
        return execute_normalization(self, source, occurrences)


class DeclaredMathScope:
    __data_operation__: ClassVar[dict] = {
        "id": "resolve.symbol_scope/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["project", "subject", "original-source", "analyzed-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "parameter": "source",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "occurrences",
                "kind": "urn:corpus:math:DeclaredMathOccurrenceProduct",
                "direction": "input",
                "parameter": "occurrences",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "symbolic",
                "kind": "urn:corpus:math:DeclaredMathSymbolicProduct",
                "direction": "input",
                "parameter": "symbolic",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "input",
                "parameter": "constructions",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "exact-selected-source-scope",
                },
            },
            {
                "name": "inherited",
                "kind": "urn:corpus:math:DeclaredMathScopeProduct",
                "direction": "input",
                "parameter": "inherited",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "frozen-source-set",
                    "source_set": "math-scope-ancestors",
                    "coverage": "exact-selected-scope",
                },
            },
            {
                "name": "ancestor_sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "parameter": "ancestor_sources",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "frozen-source-set",
                    "source_set": "math-scope-ancestor-sources",
                    "coverage": "exact-selected-source-scope",
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:math:DeclaredMathScopeProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'retained-formal-syntax-and-explicit-mathematical-context'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'exact-original-formula-coordinates'},
            {'kind': 'documentation', 'text': 'no-repeated-recognition'},
            {'kind': 'documentation', 'text': 'exact-retained-occurrence-context'},
        ],
        "coverage": "selected-formula-atoms-with-explicit-partial-context",
        "outcomes": ["success"],
        "precision": "exact-symbolic-with-retained-ambiguity",
        "dependencies": [
            "extract.math/declared",
            "normalize.formula/declared",
            "text.constructions/source-native",
        ],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "original-native-symbol-scope-v1",
        "binding": {
            "operator": "scan",
            "roles": [
                "source",
                "occurrences",
                "symbolic",
                "constructions",
                "inherited",
                "ancestor_sources",
            ],
        },
        "assets": [
            {
                "reference": "declared-mathematical-profile",
                "contract": "math/declared-profile",
                "role": "semantic-profile-and-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declared_math_scope.execute_scope",
                "contract": "math/declared-profile",
                "role": "mathematical-kernel",
            }
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/occurrence_input",
                "input_role": "occurrences",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "occurrences",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/symbolic_input",
                "input_role": "symbolic",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "symbolic",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/construction_input",
                "input_role": "constructions",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/inherited_inputs/*",
                "input_role": "inherited",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_math_products import resolve_math_port

        return resolve_math_port(
            prepared,
            model,
            operation,
            receiver=DeclaredMathScope(None),
            phase="scope",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(
        self,
        source: dict,
        occurrences: dict,
        symbolic: dict,
        constructions: dict,
        inherited: tuple[dict, ...] = (),
        ancestor_sources: tuple[dict, ...] = (),
    ) -> dict:
        return execute_scope(
            self, source, occurrences, symbolic, constructions, inherited, ancestor_sources
        )
