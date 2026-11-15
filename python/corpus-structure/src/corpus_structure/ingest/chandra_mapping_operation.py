"""Declared mechanical placement of an actually retained Chandra observation."""

from typing import ClassVar

from corpus_structure.semantic.visual_requests import map_chandra_observation


class ChandraMappingFamily:
    __data_operation__: ClassVar[dict] = {
        "abstract": True,
        "id": "source.visual/map",
        "profile": "derivation",
        "subject": "original-document",
        "subject_definition": {'id': 'original-document', 'identifier_kind': 'string', 'scope': 'original-document'},
        "discovery_relation": 'role-associated',
        "context": ["original-source", "exact-submitted-png"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "observation",
                "parameter": "observation",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-visual/DdoChandraObservation",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "observation", "description": "exact-submitted-png"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualMapping",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": ["source.visual/recognize"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "owned-visual-mapping",
        },
        "applicability": [{'kind': 'documentation', 'text': 'actual-raw-observation-with-qualified-image'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'raw-byte-digest'},
            {'kind': 'documentation', 'text': 'original-coordinate-transform'},
            {'kind': 'documentation', 'text': 'unassessed-source-fidelity'},
        ],
        "coverage": {"binding": "self", "result_owners": [{"kind":'implementation',"reference":"self"}], "description": "exact-submitted-png"},
        "outcomes": ["success", "failed"],
        "precision": "incumbent-chandra-html-parser-and-qualified-pdf-map",
        "behavior": "retain parser outcomes and independently mapped original coordinates without selecting source knowledge",
        "binding": {"operator": "scan", "roles": ["observation"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.visual_requests.map_chandra_observation",
                "contract": "visual-mapping/profile",
                "role": "existing-html-and-coordinate-kernels",
            }
        ],
        "assets": [
            {
                "reference": "chandra-parser-and-mapper",
                "contract": "visual-mapping/profile",
                "role": "parse-and-geometry-contract",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.visual_requests import PreparedVisualMappingPort

        port = PreparedVisualMappingPort(
            identity, model, model.operation(operation), prepared, authorize, custody, sources
        )
        port.verify()
        return port

    def run(self, observation: dict) -> dict:
        return map_chandra_observation(observation)


class ChandraMappingOperation(ChandraMappingFamily):
    __data_operation__: ClassVar[dict] = {"abstract": False}
