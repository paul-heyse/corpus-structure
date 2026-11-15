"""Declared weak and contextual mathematical requests on retained native facts."""

from typing import ClassVar

from corpus_structure.semantic.declared_math_analysis import execute_math_analysis


class WeakMathAnalysis:
    __data_operation__: ClassVar[dict] = {
        "id": "analyze.math/lexical",
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
                    "coverage": {"role": "source", "description": "exact-selected-scope"},
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
                    "coverage": {"role": "formal", "description": "exact-selected-scope"},
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:math-analysis:DeclaredWeakMathAnalysis",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'retained-formal-syntax-and-explicit-mathematical-context'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'original-source-and-native-formula-coordinate-distinction'},
            {'kind': 'documentation', 'text': 'no-language-recognition-or-grammar-reparse'},
            {'kind': 'documentation', 'text': 'weak-demand-never-resolves-ancestor-context'},
            {'kind': 'documentation', 'text': 'timeout-never-publishes-success'},
        ],
        "coverage": {"binding": "self", "result_owners": [{"kind":'implementation',"reference":"self"}], "description": "selected-original-formula-atoms-with-explicit-unavailability"},
        "outcomes": ["success", "failed"],
        "precision": "exact-symbolic-with-retained-ambiguity",
        "dependencies": ["text.formal_evidence/source-native"],
        "potential_dependencies": [],
        "effects": [],
        "parameters": {
            "demand": {"default": "lexical"},
            "pointer": {"default": ""},
            "question": {"default": ""},
            "predicate": {"default": ""},
            "seconds": {"default": 2.0},
        },
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "finite-lexical-analysis-over-genuine-source-and-retained-mathematical-premises",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["formal"]},
            ],
        },
        "assets": [
            {
                "reference": "mathematical-analysis-profile",
                "contract": "math-analysis/profile",
                "role": "captured-analysis-options-and-original-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declared_math_analysis.execute_math_analysis",
                "contract": "math-analysis/profile",
                "role": "owned-finite-mathematical-analysis",
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_math_analysis import resolve_math_analysis_port

        return resolve_math_analysis_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(
        self,
        prepared,
        roles=(),
        context=None,
        options=None,
        context_profile=None,
        check_active=lambda: None,
    ):
        self.prepared, self.roles, self.context = prepared, roles, context
        self.options, self.context_profile, self.check_active = (
            options,
            context_profile,
            check_active,
        )

    def run(
        self,
        source: dict,
        formal: dict,
        demand: str = "lexical",
        pointer: str = "",
        question: str = "",
        predicate: str = "",
        seconds: float = 2.0,
    ) -> dict:
        return execute_math_analysis(
            self,
            source=source,
            formal=formal,
            demand=demand,
            pointer=pointer,
            question=question,
            predicate=predicate,
            seconds=seconds,
        )


class ContextualMathAnalysis:
    __data_operation__: ClassVar[dict] = {
        "id": "analyze.math/contextual",
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
                    "coverage": {"role": "source", "description": "exact-selected-scope"},
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
                    "coverage": {"role": "formal", "description": "exact-selected-scope"},
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
                    "coverage": {"role": "constructions", "description": "exact-selected-source-scope"},
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
                    "coverage": {"role": "inherited", "description": "exact-selected-scope"},
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
                    "coverage": {"role": "ancestor_sources", "description": "exact-selected-source-scope"},
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:math-analysis:DeclaredContextualMathAnalysis",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'retained-formal-syntax-and-explicit-mathematical-context'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'original-source-and-native-formula-coordinate-distinction'},
            {'kind': 'documentation', 'text': 'no-language-recognition-or-grammar-reparse'},
            {'kind': 'documentation', 'text': 'weak-demand-never-resolves-ancestor-context'},
            {'kind': 'documentation', 'text': 'timeout-never-publishes-success'},
        ],
        "coverage": {"binding": "self", "result_owners": [{"kind":'implementation',"reference":"self"}], "description": "selected-original-formula-atoms-with-explicit-unavailability"},
        "outcomes": ["success", "failed"],
        "precision": "exact-symbolic-with-retained-ambiguity",
        "dependencies": ["text.formal_evidence/source-native", "text.constructions/source-native"],
        "potential_dependencies": ["resolve.symbol_scope/declared"],
        "effects": [],
        "parameters": {
            "demand": {"default": "interpretation"},
            "pointer": {"default": ""},
            "question": {"default": ""},
            "predicate": {"default": ""},
            "seconds": {"default": 2.0},
        },
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "finite-contextual-analysis-over-genuine-source-and-retained-mathematical-premises",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["formal"]},
                {"operator": "scan", "roles": ["constructions"]},
                {"operator": "collection", "roles": ["inherited"], "collection": "set"},
                {"operator": "collection", "roles": ["ancestor_sources"], "collection": "set"},
            ],
        },
        "assets": [
            {
                "reference": "mathematical-analysis-profile",
                "contract": "math-analysis/profile",
                "role": "captured-analysis-options-and-original-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declared_math_analysis.execute_math_analysis",
                "contract": "math-analysis/profile",
                "role": "owned-finite-mathematical-analysis",
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "formal",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "inherited",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
        from corpus_structure.semantic.declared_math_analysis import resolve_math_analysis_port

        return resolve_math_analysis_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(
        self,
        prepared,
        roles=(),
        context=None,
        options=None,
        context_profile=None,
        check_active=lambda: None,
    ):
        self.prepared, self.roles, self.context = prepared, roles, context
        self.options, self.context_profile, self.check_active = (
            options,
            context_profile,
            check_active,
        )

    def run(
        self,
        source: dict,
        formal: dict,
        constructions: dict,
        inherited: tuple[dict, ...] = (),
        ancestor_sources: tuple[dict, ...] = (),
        demand: str = "interpretation",
        pointer: str = "",
        question: str = "",
        predicate: str = "",
        seconds: float = 2.0,
    ) -> dict:
        return execute_math_analysis(
            self,
            source=source,
            formal=formal,
            constructions=constructions,
            inherited=inherited,
            ancestor_sources=ancestor_sources,
            demand=demand,
            pointer=pointer,
            question=question,
            predicate=predicate,
            seconds=seconds,
        )
