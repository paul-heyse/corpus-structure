"""A fixed literal-question panel through genuine shared D1 execution.

This fixture does not change production characterization question families.
The current provider/profile, physical owner, decoders and native publication
remain real; correctness expectations stay independent in the consuming test.
"""

import inspect
import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.identity import canonical_bytes
from semantic.current_pm2_projection_fixture import execute_kernel, projection_inputs

MODULE = "semantic.current_pm2_provider_fixture"
OPERATION = "fixture.pm2_literal_provider"
ASSET = "pm2-literal-provider/source-assets"
CUSTODY = "pm2-literal-provider/execution-custody"
PROFILE = "pm2-literal-provider/inference-profile"


def inference_policy():
    from corpus_structure.methods.model_observation import installed_policy

    return installed_policy()[0]["batch_execution"]


def execute_profile(receiver, source, mode):
    raise ValueError("actual literal provider requires its acquired physical plan")


class LiteralProviderProjection:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.pm2_literal_provider",
        "profile": "derivation",
        "replicate_policy": "retained-observation-single-result",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["fixed-native-literal-panel"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "parameter": "source",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "pm2-test-source",
                    "identity_requirements": ["episode"],
                    "coverage": {"role": "source", "description": "actual-selected-source"},
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "fixed-literal-panel-only"}],
        "invariants": [
            {"kind": "documentation", "text": "actual-provider-observation-is-private-uncalibrated"}
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-first-native-piece",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "unchanged-native-d1-and-original-field-inversion",
        "dependencies": [],
        "effects": [],
        "parameters": {"mode": {"default": "literal"}},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "fixed-literal-question-provider-inspection",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.current_pm2_provider_fixture.execute_profile",
                "contract": "pm2-literal-provider/source-assets",
                "role": "genuine-provider-plan",
            }
        ],
        "assets": [
            {
                "reference": "fixed-literal-provider",
                "contract": "pm2-literal-provider/source-assets",
                "role": "captured-fixed-question-computation",
            },
            {
                "reference": "literal-provider-profile",
                "contract": "pm2-literal-provider/inference-profile",
                "role": "provider-inference-profile",
            },
        ],
    }

    def run(self, source: dict, mode: str = "literal") -> dict:
        return execute_profile(self, source, mode)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        captured = json.loads(next(item.content for item in custody if item.name == CUSTODY))
        declared = captured["selection"]
        selection = NativeSelection(
            NativeProfile.from_content(canonical_bytes(declared["profile"])),
            Path(declared["assets"]),
        )
        if selection.native.fingerprint != declared["fingerprint"]:
            raise ValueError("literal provider differs from its captured actual profile")
        plan = ProviderPlan(prepared, selection)
        port = PreparedOriginalCallPort(
            identity,
            model,
            model.operation(operation),
            sources,
            custody,
            LiteralProviderProjection().run,
            plan.plan,
            MODULE + ".ProviderPlan.plan",
            authorize,
            (assets(), profile_asset(selection)),
            operation_sources(selection),
            functions=(("semantic.current_pm2_projection_fixture.execute_kernel", execute_kernel),),
            native_selections=(selection,),
            requires_prepared_schema=True,
        )
        plan.port = port
        return port


@dataclass
class ProviderPlan:
    prepared: Any
    selection: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.methods.characterization_resources import (
            LogicalProviderMember,
            PM2Work,
        )
        from corpus_structure.methods.model_observation import (
            ordered_native_bytes,
            validate_pm2_batch_receipt,
        )
        from corpus_structure.methods.native_host import payload_digest
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

        if (
            binding is None
            or not binding.sufficient
            or binding.subject_context is None
            or arguments.arguments["mode"] != "literal"
        ):
            raise ValueError("literal provider requires its exact sufficient frozen panel")
        (member,) = next(role.members for role in binding.roles if role.role == "source")
        context = binding.subject_context
        source = arguments.arguments["source"]
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, source, member, project=context.project_id
        )
        _, _, _, request, _, _ = projection_inputs(
            self.prepared, source, frame.pin.values(), "literal"
        )
        claim = execution_owner.claim
        logical = LogicalProviderMember(
            str(claim.request_id),
            claim.generation,
            claim.task_id,
            claim.attempt,
            "literal:first-native-piece",
            0,
            1,
            payload_digest([request]),
        )
        correlation = sha256(canonical_bytes([claim.fence, request])).hexdigest()
        providers = execution_owner.providers
        providers.declare_native((self.selection,))
        (reply,) = yield (
            providers.work(
                PM2Work(
                    self.selection,
                    ordered_native_bytes({"batch": [request]}),
                    correlation,
                    (check_active,),
                    (logical,),
                ),
                reservation=execution_owner.reservation,
            ),
        )
        native = reply.payload.get("batch")
        if not isinstance(native, list) or len(native) != 1 or reply.execution_receipt is None:
            raise ValueError("literal provider changed its exact frozen native population")
        validate_pm2_batch_receipt(native[0].get("batch_receipt"), request, "d1")
        bound = inspect.signature(execute_kernel, eval_str=True).bind(
            source=source,
            pin=frame.pin.values(),
            context=dict(
                project_id=context.project_id,
                subject=context.subject,
                subject_definition=context.subject_definition,
                original_source=context.original_source,
                analyzed_scope=json_loads(context.analyzed_scope),
            ),
            mode="literal",
            native_reply=native[0],
            profile=self.selection.native.wire,
            prepared=self.prepared,
            check_active=check_active,
        )
        completed = yield from self.port.plan_cpu(
            execute_kernel,
            bound,
            operation_sources(self.selection),
            prepared_release_id=self.prepared.release_id,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return replace(
            completed,
            provider_execution_evidence=canonical_bytes([asdict(reply.execution_receipt)]),
        )


def profile_asset(selection):
    from corpus_structure.semantic.data_operation_provider_profiles import (
        profile_asset as capture_profile,
    )

    return capture_profile(PROFILE, selection, inference_policy())


def assets():
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            dict(
                version="literal-provider-panel-v1",
                source=admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
            )
        ),
    )


def execution_custody(selection):
    from corpus_structure.semantic.data_operation_provider_profiles import profile_attestation
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        CUSTODY,
        canonical_bytes(
            dict(
                selection=selection.declaration(),
                provider_profile=profile_attestation(selection, inference_policy()),
            )
        ),
    )


def operation_sources(selection):
    from corpus_structure.semantic import identity
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )
    from semantic.current_pm2_projection_fixture import operation_sources as decoder_sources

    path = Path(__file__).resolve()
    return combine_primary_sources(
        decoder_sources(),
        PythonSourceCollection(
            (
                PythonSource(MODULE, path.read_bytes(), str(path)),
                PythonSource(
                    identity.__name__, Path(identity.__file__).read_bytes(), identity.__file__
                ),
            ),
            boundary_contracts=(assets(), profile_asset(selection), execution_custody(selection)),
        ),
    )
