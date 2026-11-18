"""Finite PM2 decoder transport with real selected-source and CPU custody.

The authored replies are controlled input, not external provider observations.
Production D1/source decoders and the ordinary candidate carrier own the result.
"""

import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from corpus_structure.semantic.identity import canonical_bytes

MODULE = "semantic.current_pm2_projection_fixture"
OPERATION = "fixture.pm2_projection"
ASSET = "pm2-projection-fixture/source-assets"


def projection_inputs(prepared, source, pin, mode):
    from corpus_structure.methods.pm2_source import D1SourceField
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.interpretation_questions import Question, QuestionFamily
    from corpus_structure.semantic.model_characterization import prepare_model_scope

    if mode not in {"empty", "mixed", "literal"}:
        raise ValueError("controlled PM2 projection has no such finite case")
    frame = DeclaredNativeFrameSource(
        canonical_bytes(source).decode(), canonical_bytes(pin).decode()
    )
    piece = next(row for row in source["pieces"] if row["kind"] == "native_text")
    start, end = piece["start"], piece["end"]
    literal = source["text"][start:end]
    if literal not in {"12", "x + y"}:
        raise ValueError("controlled PM2 transport requires its independent literal panel")
    scope = prepare_model_scope(frame, (start, end), (start, end), max_chars=65536)
    family = QuestionFamily(
        family="literal_completion_v1",
        questions=(
            Question(key="missing", kind="text", instructions="Copy the document's color."),
            Question(
                key="value",
                kind="number" if literal == "12" else "text",
                instructions="Copy the literal exactly.",
            ),
        ),
    )
    keys = (
        ("missing",)
        if mode == "empty"
        else ("value",)
        if mode == "literal"
        else ("missing", "value")
    )
    request = dict(
        state=dict(source=literal),
        questions={q.key: q.native([]) for q in family.questions if q.key in keys},
        interpretation=dict(
            version="3",
            declaration_digest=family.digest,
            assessed_scope=dict(
                pin=pin, scope_digest=scope.mapping.scope_digest, projection_extent=[start, end]
            ),
            candidates=[],
        ),
    )
    rendered = json.dumps(request["state"], ensure_ascii=False, separators=(",", ":"))
    field = D1SourceField(rendered, "/source", 11, len(rendered) - 2)
    answers: dict[str, dict[str, Any]] = {}
    if "missing" in keys:
        answers["missing"] = dict(type="text", found=0.2, span=None, text=None)
    if "value" in keys:
        answers["value"] = dict(
            type="number" if literal == "12" else "text",
            found=0.98,
            span=[11, len(rendered) - 2],
            text=literal,
            path="/source",
        )
        if literal == "12":
            answers["value"]["number"] = 12
    reply = dict(
        outcome="empty" if mode == "empty" else "succeeded",
        rendered_state=rendered,
        state_fields=[[11, len(rendered) - 2, "/source"]],
        native=dict(answers=answers),
    )
    return frame, scope, family, request, reply, field


def project(prepared, model, source, pin, context, mode, *, native_reply=None, profile=None):
    from corpus_structure.methods.pm2_interpretation_products import interpretation_products
    from corpus_structure.methods.pm2_result import (
        d1_evidence,
        pm2_contribution_values,
        pm2_input_digest,
    )
    from corpus_structure.methods.pm2_source import D1SourceField
    from corpus_structure.semantic.contributions import operation_identity
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_candidate_products import candidate_inspection_report

    frame, scope, family, request, reply, field = projection_inputs(prepared, source, pin, mode)
    if native_reply is not None:
        reply = native_reply
        if reply.get("outcome") not in {"succeeded", "empty"}:
            raise ValueError("actual literal provider did not complete its declared question")
        if canonical_bytes(json.loads(reply["rendered_state"])) != canonical_bytes(
            request["state"]
        ):
            raise ValueError("actual literal provider changed its frozen source state")
        fields = [value for value in reply["state_fields"] if value[2] == "/source"]
        if len(fields) != 1:
            raise ValueError("actual literal provider lacks one authorized source field")
        a, b, _ = fields[0]
        field = D1SourceField(reply["rendered_state"], "/source", a, b)
    located = d1_evidence(scope.mapping, reply, field=field, source_path="/source", native=True)
    parsed = interpretation_products(family, request, reply, located)
    digest = pm2_input_digest(
        scope.mapping,
        {"provider": "controlled-d1-reply-transport"} if profile is None else profile,
        request,
        question=family.family,
        operation_version="3",
        source_path="/source",
    )
    operation = operation_identity(family.family, "3", pin["source"], digest)
    rows, coordinates, locations = pm2_contribution_values(
        scope.mapping,
        located,
        parsed,
        prepared=prepared,
        provider="d1",
        input_digest=digest,
        operation_key=operation,
        question=family.family,
        source_path="/source",
    )
    return candidate_inspection_report(
        prepared,
        model,
        frame,
        SubjectContext(
            context["project_id"],
            context["subject"],
            context["original_source"],
            canonical_bytes(context["analyzed_scope"]),
            subject_definition=context["subject_definition"],
        ),
        inspection_outcome="produced" if rows else "empty",
        contributions=rows,
        operations=[
            dict(
                operation_key=operation,
                question=family.family,
                operation_version="3",
                outcome="succeeded",
                inspected_count=1,
                emitted_count=len(rows),
                computation_dependencies=[digest],
            )
        ],
        coordinate_texts=coordinates,
        coverage=[
            dict(
                family=family.family,
                scope=canonical_bytes(scope.examined).decode(),
                outcome="complete",
            )
        ],
        diagnostics=dict(
            controlled_transport=native_reply is None,
            request=request,
            native_reply=reply,
            locations=locations,
            input_digest=digest,
            source_map_digest=scope.mapping.input_digest,
        ),
    )


def execute_profile(receiver, source, mode):
    raise ValueError("controlled PM2 projection requires its acquired CPU plan")


def execute_kernel(
    source: dict,
    pin: dict,
    context: dict,
    mode: str,
    *,
    prepared,
    check_active,
    native_reply: dict | None = None,
    profile: dict | None = None,
) -> dict:
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    check_active()
    return project(
        prepared,
        bound_data_operation_model(prepared),
        source,
        pin,
        context,
        mode,
        native_reply=native_reply,
        profile=profile,
    )


class ControlledPM2Projection:
    __data_operation__: ClassVar[dict] = {
        "id": "fixture.pm2_projection",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["controlled-pm2-decoder-transport"],
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
        "applicability": [{"kind": "documentation", "text": "independent-finite-literal-panel"}],
        "invariants": [
            {"kind": "documentation", "text": "controlled-replies-are-not-provider-evidence"}
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-first-native-piece",
        },
        "outcomes": ["success"],
        "precision_description": "production-original-field-inversion",
        "dependencies": [],
        "effects": [],
        "parameters": {"mode": {"default": "mixed"}},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "controlled-pm2-decoder-transport",
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "semantic.current_pm2_projection_fixture.execute_profile",
                "contract": "pm2-projection-fixture/source-assets",
                "role": "controlled-reply-decoding",
            }
        ],
        "assets": [
            {
                "reference": "controlled-pm2-replies",
                "contract": "pm2-projection-fixture/source-assets",
                "role": "captured-controlled-computation",
            }
        ],
    }

    def run(self, source: dict, mode: str = "mixed") -> dict:
        return execute_profile(self, source, mode)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

        plan = ProjectionPlan(prepared)
        port = PreparedOriginalCallPort(
            identity,
            model,
            model.operation(operation),
            sources,
            custody,
            ControlledPM2Projection().run,
            plan.plan,
            MODULE + ".ProjectionPlan.plan",
            authorize,
            (assets(),),
            operation_sources(),
            functions=((MODULE + ".execute_kernel", execute_kernel),),
            requires_prepared_schema=True,
        )
        plan.port = port
        return port


@dataclass
class ProjectionPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise ValueError("controlled projection requires actual sufficient source support")
        (member,) = next(role.members for role in binding.roles if role.role == "source")
        context = binding.subject_context
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, arguments.arguments["source"], member, project=context.project_id
        )
        bound = inspect.signature(execute_kernel, eval_str=True).bind(
            source=arguments.arguments["source"],
            pin=frame.pin.values(),
            context=dict(
                project_id=context.project_id,
                subject=context.subject,
                original_source=context.original_source,
                subject_definition=context.subject_definition,
                analyzed_scope=json_loads(context.analyzed_scope),
            ),
            mode=arguments.arguments["mode"],
            prepared=self.prepared,
            check_active=check_active,
        )
        bound.apply_defaults()
        return (
            yield from self.port.plan_cpu(
                execute_kernel,
                bound,
                operation_sources(),
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def assets():
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            dict(
                version="controlled-pm2-projection-v1",
                source=admitted_operation_module_meaning(Path(__file__).read_bytes()).hex(),
            )
        ),
    )


def operation_sources():
    from corpus_structure.semantic import data_operation_prepared_call
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    path = Path(__file__).resolve()
    adapter = Path(data_operation_prepared_call.__file__).resolve()
    return PythonSourceCollection(
        (
            PythonSource(MODULE, path.read_bytes(), str(path)),
            PythonSource(data_operation_prepared_call.__name__, adapter.read_bytes(), str(adapter)),
        ),
        boundary_contracts=(assets(),),
    )
