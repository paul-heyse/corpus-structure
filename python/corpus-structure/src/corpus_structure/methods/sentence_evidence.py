"""Original declared canonical sentence/token entrypoint over selected native source."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.sentence_products import SourceAnnotations, execute_sentence_profile
from corpus_structure.semantic.source_products import FrozenNativeSource


def verify_annotation_source(annotation_source, annotation_selectors, source, selectors):
    """Check the annotation's declared source coordinate and examined selectors."""
    if annotation_source != source or tuple(annotation_selectors) != tuple(selectors):
        raise ValueError("source annotations differ from exact original source/scope")


class SentenceEvidenceOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "segment.sentences/source-native",
        "profile": "derivation",
        "replicate_policy": "retained-observation-single-result",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "rules": [
            {
                "id": "segment.sentences/source-layout",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "segment.sentences/source-native",
                "checker_callable": "corpus_structure.semantic.sentence_products.verify_annotation_block_source",
                "parameters": {
                    "paths": ["block_layouts", "rows", "configuration", "execution_profile"],
                    "input_reads": {"source": ["source", "pieces", "text"]},
                },
            },
            {
                "id": "segment.sentences/token-sentence-membership",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "collection": "rows",
                "scope": "partition",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "segment.sentences/source-native",
                "checker_callable": "corpus_structure.semantic.sentence_products.verify_annotation_sentence_membership",
                "parameters": {"paths": ["record_type", "ordinal", "start", "end", "sentence"]},
            },
            {
                "id": "segment.sentences/coverage-manifest",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "segment.sentences/source-native",
                "checker_callable": "corpus_structure.semantic.sentence_products.verify_annotation_coverage",
                "parameters": {
                    "paths": [
                        "source",
                        "selectors",
                        "coverage",
                        "outcome",
                        "members",
                    ],
                    "input_reads": {"source": ["selectors"]},
                },
            },
            {
                "id": "segment.sentences/native-dense-ordinal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "collection": "rows",
                "scope": "partition",
                "form": "dense_ordinal",
                "checker": "admission",
                "parameters": {"path": "ordinal", "group_by": ["record_type"]},
            },
            {
                "id": "segment.sentences/native-source-order",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "collection": "rows",
                "scope": "partition",
                "form": "ordered_by",
                "checker": "admission",
                "parameters": {"paths": ["record_type", "start"]},
            },
            {
                "id": "segment.sentences/native-row-span",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "collection": "rows",
                "scope": "partition",
                "form": "span_within",
                "checker": "admission",
                "parameters": {
                    "start": "start",
                    "end": "end",
                    "limit": "extent",
                    "coordinates": "relative",
                },
            },
            {
                "id": "segment.sentences/exact-source-scope",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "segment.sentences/source-native",
                "checker_callable": "corpus_structure.methods.sentence_evidence.verify_annotation_source",
                "parameters": {
                    "paths": ["source", "selectors"],
                    "input_reads": {"source": ["source", "selectors"]},
                },
            },
        ],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": {"role": "source", "description": "selected-scope"},
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "captured-original-blocks"}],
        "invariants": [
            {"kind": "documentation", "text": "original-source-coordinates"},
            {"kind": "documentation", "text": "atom-preserving-layout"},
            {"kind": "documentation", "text": "closed-token-sentence-membership"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-original-blocks",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "exact-original-projection-offsets",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "existing learned spaCy parser over original atom-preserving canonical layout",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.sentence_products.execute_sentence_profile",
                "contract": "sentences/profile-assets",
                "role": "prepared-spacy-parser",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "sentences/profile-assets",
                "role": "original-source-boundary",
            },
            {
                "reference": "corpus_structure.semantic.sentence_products.SourceAnnotations",
                "contract": "sentences/profile-assets",
                "role": "typed-sentence-product",
            },
        ],
        "assets": [
            {
                "reference": "spacy-provider-inference-profile",
                "contract": "sentences/provider-inference-profile",
                "role": "provider-inference-profile",
            },
            {
                "reference": "spacy-original-model-profile",
                "contract": "sentences/profile-assets",
                "role": "learned-parser-model-and-layout",
            },
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/block_layouts/*/annotation/source",
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
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.sentence_products import resolve_sentence_port

        return resolve_sentence_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, check_active, host=None, *, source_pin=None):
        self.profile = profile
        self.check_active = check_active
        self.host = host
        self.source_pin = source_pin

    def run(self, source: FrozenNativeSource) -> SourceAnnotations:
        return execute_sentence_profile(self, source)
