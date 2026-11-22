"""Declared independent HanLP native characterization over canonical sentences."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.canonical_sentences import CanonicalProduct
from corpus_structure.semantic.hanlp_products import HanlpProduct, execute_hanlp_profile
from corpus_structure.semantic.source_products import FrozenNativeSource


class HanlpEvidenceOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "text.hanlp_native/source-native",
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
                "id": "text.hanlp_native/dense-unit-ordinals",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "collection": "rows",
                "scope": "partition",
                "form": "dense_ordinal",
                "checker": "admission",
                "parameters": {"path": "ordinal", "group_by": ["sentence_ordinal", "record_type"]},
            },
            {
                "id": "text.hanlp_native/canonical-token-and-span-alignment",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.hanlp_native/source-native",
                "checker_callable": "corpus_structure.semantic.hanlp_products.verify_hanlp_sentence_alignment",
                "parameters": {
                    "paths": ["canonical_input", "rows"],
                    "input_reads": {
                        "canonical": ["source", "selectors", "rows"],
                        "source": ["source", "selectors", "text"],
                    },
                },
            },
            {
                "id": "text.hanlp_native/coverage",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.hanlp_native/source-native",
                "checker_callable": "corpus_structure.semantic.hanlp_products.hanlp_coverage_outcome",
                "parameters": {
                    "paths": ["source", "selectors", "coverage", "outcome", "members"],
                    "input_reads": {
                        "canonical": ["block_coverage", "rows"],
                        "source": ["source", "selectors", "text"],
                    },
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
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": {"role": "source", "description": "selected-scope"},
                },
            },
            {
                "name": "canonical",
                "required_rules": ["segment.sentences/canonical-dense-ordinal"],
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoCanonicalSentences",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "canonical",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "source": "original-source",
                    "coverage": {"role": "canonical", "description": "selected-scope"},
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "canonical-pretokenized-sentences"}],
        "invariants": [
            {"kind": "documentation", "text": "original-source-coordinates"},
            {"kind": "documentation", "text": "no-retokenization"},
            {"kind": "documentation", "text": "independent-native-head-standings"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-canonical-sentences",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "native-one-based-heads-and-half-open-word-spans",
        "dependencies": ["segment.sentences/canonical-projection"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "original HanLP five native heads over retained canonical words",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source", "canonical"]},
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/canonical_input",
                "input_role": "canonical",
                "variant": "product",
            },
            {
                "output_role": "result",
                "path": "/sentence",
                "input_role": "canonical",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            },
            {
                "output_role": "result",
                "path": "/token",
                "input_role": "canonical",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            },
            {
                "output_role": "result",
                "path": "/tokens/*",
                "input_role": "canonical",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            },
            {
                "output_role": "result",
                "path": "/children/*/token",
                "input_role": "canonical",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            },
            {
                "output_role": "result",
                "path": "/roles/*/tokens/*",
                "input_role": "canonical",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            },
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.hanlp_products.execute_hanlp_profile",
                "contract": "hanlp/profile-assets",
                "role": "prepared-hanlp-native",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "hanlp/profile-assets",
                "role": "original-source-boundary",
            },
            {
                "reference": "corpus_structure.semantic.canonical_sentences.CanonicalProduct",
                "contract": "hanlp/profile-assets",
                "role": "canonical-member-boundary",
            },
            {
                "reference": "corpus_structure.semantic.hanlp_products.HanlpProduct",
                "contract": "hanlp/profile-assets",
                "role": "typed-native-heads",
            },
        ],
        "assets": [
            {
                "reference": "hanlp-provider-inference-profile",
                "contract": "hanlp/provider-inference-profile",
                "role": "provider-inference-profile",
            },
            {
                "reference": "hanlp-native-model-profile",
                "contract": "hanlp/profile-assets",
                "role": "native-checkpoint-heads-and-decoder",
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.hanlp_products import resolve_hanlp_port

        return resolve_hanlp_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, check_active, host=None):
        self.profile, self.check_active, self.host = profile, check_active, host

    def run(self, source: FrozenNativeSource, canonical: CanonicalProduct) -> HanlpProduct:
        return execute_hanlp_profile(self, source, canonical)
