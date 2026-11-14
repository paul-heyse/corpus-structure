"""Exact PostgreSQL retrieval from explicitly bound inventory and vector products."""

from typing import Any, ClassVar

from corpus_structure.semantic.contextual_operations import execute_retrieval_profile


class ContextualRetrievalOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual/declared", "profile": "derivation", "subject": "selected-native-source",
        "context": ["original-source", "located-occurrence", "frozen-inventory", "exact-encoder-space"],
        "entrypoints": ["run"],
        "roles": [
            {"name": "query", "parameter": "query", "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery", "direction": "input", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required", "support": {"provenance": "exact", "source": "same-original", "coverage": "located-occurrence", "identity_requirements": ["episode"]}},
            {"name": "inventory", "parameter": "inventory", "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualInventory", "direction": "input", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required", "support": {"provenance": "value_substitution", "source": "explicit-inventory", "coverage": "complete-eligible-inventory", "identity_requirements": []}},
            {"name": "vectors", "parameter": "vectors", "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualVectors", "direction": "input", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required", "support": {"provenance": "exact", "source": "selected-inventory-and-query", "coverage": "complete-selected-inputs", "identity_requirements": ["episode"]}},
            {"name": "policy", "parameter": "policy", "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalPolicy", "direction": "input", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required", "support": {"provenance": "value_substitution", "source": "explicit-policy", "coverage": "complete-relationship-constraints", "identity_requirements": []}},
            {"name": "result", "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalProduct", "direction": "output", "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required"},
        ],
        "applicability": ["complete-admitted-inventory-profile-and-vector-population"],
        "invariants": ["exact-postgresql-ranking", "equal-labels-remain-distinct", "explicit-relationship-witnesses", "private-proposal-standing"],
        "coverage": "complete-frozen-eligible-inventory", "outcomes": ["success"], "precision": "exact-pgvector-cosine-and-lexical-ranking",
        "dependencies": [], "effects": [],
        "capabilities": {"forms": ["scalar"], "preparation": "resource", "prepared_factory": "acquire_port", "cancellation": "call-boundary", "ownership": "invocation-owned-db-borrow"},
        "behavior": "one-exact-native-retrieval-and-source-supported-relationship-result",
        "parameters": {}, "binding": {"operator": "scan", "roles": ["query", "inventory", "vectors", "policy"]},
        "output_witnesses": [{"output_role": "result", "records": "", "input_role": "query", "comparisons": [{"output_field": "/source_pin", "input": {"role": "query", "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery", "field": "/source_pin"}, "encoding": "value"}]}],
        "opaque": [{"reference": "corpus_structure.semantic.contextual_operations.execute_retrieval_profile", "contract": "contextual/retrieval-assets", "role": "exact-postgresql-and-relationship-algorithms"}],
        "assets": [{"reference": "retrieval-algorithms", "contract": "contextual/retrieval-assets", "role": "actual-retrieval-and-vector-shape-kernels"}],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, query: dict[str, Any], inventory: dict[str, Any], vectors: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
        return execute_retrieval_profile(self, query, inventory, vectors, policy)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_operations import resolve_retrieval_port

        return resolve_retrieval_port(prepared, model, operation, identity=identity, authorize=authorize, custody=custody, sources=sources)
