"""Native-issued ordinary structural statements from protected authored adjudication."""

from typing import ClassVar


class StructuralComparisonAdmission:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.admit_comparison",
        "profile": "command",
        "subject": "actual-focus-source",
        "subject_definition": {"id": "actual-focus-source", "identifier_kind": "string", "scope": "selected-source-set"},
        "discovery_relation": "role-associated",
        "context": ["exact-structural-report", "protected-independent-attributed-adjudication"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "report", "parameter": "report", "direction": "input",
                "kind": "urn:corpus:structural:DeclaredComparisonReport",
                "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required",
                "support": {"provenance": "exact", "source": "same-original", "identity_requirements": ["episode"],
                            "coverage": {"role": "report", "description": "exact-native-structural-report"}},
            },
            {
                "name": "passes", "parameter": "passes", "direction": "input",
                "kind": "urn:corpus:structural-admission:protected:DdoStructuralReferencePass",
                "minimum": 3, "maximum": 3, "collection": "set", "presence": "required",
                "support": {"provenance": "exact", "source": "same-original", "origins": ["authored"],
                            "identity_requirements": ["original-source"],
                            "coverage": {"role": "passes", "description": "exact-original-authored-A-B-C"}},
            },
            {
                "name": "admission", "direction": "output", "kind": "urn:corpus:structural-admission:DdoStructuralAdmission",
                "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "exact-independent-structural-comparison-1"}],
        "invariants": [{"kind": "documentation", "text": "native-authenticated-original-authorship-and-exact-whole-statement"}],
        "coverage": {"binding": "self", "result_owners": [{"kind": "implementation", "reference": "self"}], "description": "one-exact-structural-admission"},
        "outcomes": ["success"],
        "precision_description": "exact-source-qualified-structural-public-statement",
        "dependencies": [],
        "effects": [{"name": "native-evaluator-structural-admission",
                     "authorization": ["native-purpose:evaluator", "exact-protected-structural-adjudication"],
                     "idempotency": "request-generation/exact-structural-statement", "fulfillment": "native-publication-receipt"}],
        "capabilities": {"forms": ["scalar"], "preparation": "native-publication", "prepared_factory": "acquire_port",
                         "cancellation": "cooperative", "ownership": "invocation-owned-cpu"},
        "behavior": "allowlisted-structural-statement-issued-only-by-native-publication",
        "parameters": {},
        "binding": {"operator": "all", "children": [
            {"operator": "scan", "roles": ["report"]},
            {"operator": "collection", "roles": ["passes"], "collection": "set"},
        ]},
        "opaque": [{"reference": "corpus_structure.evaluate.declared_structural_admission.structural_admission_value",
                    "contract": "structural-admission/assets", "role": "exact-public-structural-value"}],
        "assets": [{"reference": "structural-admission", "contract": "structural-admission/assets", "role": "closed-structural-admission-contract"}],
    }

    def run(self, report: dict, passes: list) -> dict:
        from corpus_structure.evaluate.declared_structural_admission import structural_admission_value

        return structural_admission_value(report, passes).model_dump(mode="json")

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_structural_admission import acquire_structural_admission_port

        return acquire_structural_admission_port(prepared, model, operation, identity=identity,
                                                 authorize=authorize, custody=custody, sources=sources)
