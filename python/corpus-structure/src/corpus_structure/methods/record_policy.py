"""Native-issued ordinary policy conclusions over exact protected fitted evidence."""

from typing import ClassVar

from corpus_structure.semantic.record_policy_authority import execute_authorization_profile


class RecordPolicyAuthorization:
    __data_operation__: ClassVar[dict] = {
        "id": "record_policy.authorize", "profile": "command", "subject": "knowledge-universe",
        "subject_definition": {"id": "knowledge-universe", "identifier_kind": "string", "scope": "project"},
        "discovery_relation": "role-associated", "context": ["exact-policy-instance", "protected-evaluator-basis"],
        "entrypoints": ["run"],
        "roles": [
            {"name": "basis", "parameter": "basis", "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoFittedRecordPolicy",
             "direction": "input", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required",
             "support": {"provenance": "exact", "source": "same-original", "coverage": {"role": "basis", "description": "exact-fitted-and-calibrated-instance"}, "identity_requirements": ["episode"]}},
            {"name": "authorization", "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization",
             "direction": "output", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required"},
        ],
        "applicability": [{"kind": "documentation", "text": "native-authenticated-protected-policy-instance-and-checked-application-sources"}],
        "invariants": [{"kind": "documentation", "text": "native-exact-issuer-and-public-disclosure-boundary"}],
        "coverage": {"binding": "self", "result_owners": [{"kind": "implementation", "reference": "self"}], "description": "one-exact-policy-authorization"},
        "outcomes": ["success"], "precision_description": "exact-finite-parameter-projection", "dependencies": [],
        "effects": [{"name": "native-evaluator-policy-authorization", "authorization": ["native-purpose:evaluator", "exact-protected-policy-basis"], "idempotency": "request-generation/exact-instance", "fulfillment": "native-publication-receipt"}],
        "capabilities": {"forms": ["scalar"], "preparation": "native-publication", "prepared_factory": "acquire_port", "cancellation": "cooperative", "ownership": "invocation-owned-cpu"},
        "behavior": "allowlisted-policy-conclusion-issued-only-by-native-publication",
        "parameters": {}, "binding": {"operator": "scan", "roles": ["basis"]},
        "opaque": [{"reference": "corpus_structure.semantic.record_policy_authority.execute_authorization_profile", "contract": "record-policy/authorization-assets", "role": "exact-public-policy-value"}],
        "assets": [{"reference": "record-policy-authority", "contract": "record-policy/authorization-assets", "role": "closed-policy-contract-and-allowlist"}],
    }

    def run(self, basis: dict) -> dict:
        return execute_authorization_profile(self, basis)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.record_policy_authority import acquire_authorization_port

        return acquire_authorization_port(
            prepared, model, operation, identity=identity, authorize=authorize, custody=custody, sources=sources,
        )
