"""Exact retained definition component/role location, with authentic native source anchors."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import PreparedRelease, SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-definition-location.yaml"
_FILES = (
    "methods/definition_location.py",
    "semantic/definition_location_products.py",
    "methods/definition_terms.py",
    "semantic/source_contexts.py",
    "semantic/structural_products.py",
    "semantic/declared_structural_references.py",
    "semantic/contributions.py",
    "semantic/declared_record_sources.py",
    "semantic/declared_candidate_products.py",
    "semantic/data_operation_prepared_call.py",
)


def definition_location_inputs(bundle: SourceBundle) -> SourceBundle:
    import yaml

    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(bundle)
    name, root = "data_operation_definition_location", "data_operation_definition_location_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("definition location schema differs from its captured owner")
        return bundle
    if root in existing:
        raise ValueError("definition location uses its reserved schema root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:definition-location-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def definition_location_assets():
    return SourceArtifact(
        "definition-location/profile-assets",
        canonical_bytes(
            {
                "version": "declared-definition-location-1",
                "schema": _MODEL.read_bytes().hex(),
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/definition_location.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def definition_location_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (_FILES[0], _FILES[1], _FILES[2], _FILES[-1])
        ),
        boundary_contracts=(definition_location_assets(),),
    )


def definition_location_values(frame, report, reference, selection, *, check_active=lambda: None):
    """Project selected original spans; independent role proposals never become attachments."""
    from hashlib import sha256

    from corpus_structure.methods.definition_terms import locate_definition_span

    from .contributions import contribution_identity, occurrence_identity, operation_identity
    from .observations import source_value
    from .source_contexts import NativeSourceContext, PreparedNativeSources, source_slice
    from .structural_products import read_definition_components_report

    report = read_definition_components_report(report)
    component_ids = tuple(selection["component_ids"])
    roles = tuple((row["role"], row["envelope"], row["index"]) for row in selection["roles"])
    if (
        (not component_ids and not roles)
        or (component_ids and roles)
        or max(len(component_ids), len(roles)) > 256
    ):
        raise ValueError(
            "location requires one bounded explicit component or independent role population"
        )
    if len(set(component_ids)) != len(component_ids) or len(set(roles)) != len(roles):
        raise ValueError("location selection repeats a retained definition identity")
    pin = frame.pin.values()
    passages = {row.passage_id: row for row in report.inputs.passages}
    sources = {row.identity: row for row in report.inputs.sources}
    components = {row.component_id: row for row in report.definition_components.components}
    candidates = {
        (row.role, row.envelope, row.index): row
        for row in report.definition_components.role_candidates or ()
    }
    selected = []
    for identity in component_ids:
        if identity not in components:
            raise ValueError("selected definition component is absent from the retained report")
        component = components[identity]
        # Preserve the directed attachment and actual producer address; locating the
        # term supplies no independent support for this component's interpretation.
        meaning = {
            "role": "defined_term",
            "component_reference": {
                **reference,
                "structural_id": report.product_id,
                "component_id": component.component_id,
            },
            "attachment": {
                "term": component.term.model_dump(mode="json"),
                "content": component.content.model_dump(mode="json"),
                "interpretation": component.interpretation,
            },
        }
        selected.append(
            (component.term, "definition.term", "occurrence", meaning, component.component_id)
        )
    for identity in roles:
        if identity not in candidates:
            raise ValueError("selected definition role is absent from the retained report")
        candidate = candidates[identity]
        meaning = {
            "role": candidate.role,
            "role_reference": {
                "report": {**reference, "structural_id": report.product_id},
                "role": candidate.role,
                "envelope": candidate.envelope,
                "index": candidate.index,
            },
        }
        key = "definition-role:" + sha256(canonical_bytes(meaning["role_reference"])).hexdigest()
        selected.append(
            (
                candidate.span,
                "definition.term" if candidate.role == "term" else "definition.defining_text",
                "proposal",
                meaning,
                key,
            )
        )
    operation_key = operation_identity(
        "locate.definition_terms/declared",
        "declared-definition-location-1",
        reference,
        selection,
        pin,
    )
    preparation = PreparedNativeSources((frame,), max_sources=1)
    products, coordinates, dependencies = [], {}, []
    for span, semantic_type, kind, meaning, identity in selected:
        check_active()
        passage = passages[span.passage_id]
        source = sources[passage.source_ref]
        if not source.matches_pin(pin):
            raise ValueError("retained definition belongs to another selected native source")
        if (
            not passage.start <= span.start < span.end <= passage.end
            or frame.text[span.start : span.end] != span.text
            or frame.text[passage.start : passage.end] != passage.text
        ):
            raise ValueError("retained definition span differs from its exact native source")
        context = NativeSourceContext(
            frame,
            (),
            (source_slice(frame, span.start, span.end),),
            "retained definition role projection",
            "retained-definition-role-declared-1",
            "exact selected retained span",
            max_chars=span.end - span.start,
            max_pieces=1,
            max_sources=1,
            version=2,
            preparation=preparation,
        )
        anchors, located = locate_definition_span(
            context, span.model_dump(mode="json"), offset=span.start
        )
        for coordinate in located:
            coordinates[
                canonical_bytes({key: value for key, value in coordinate.items() if key != "text"})
            ] = coordinate
        deps = (reference["product_id"], report.product_id, identity)
        dependencies.extend(deps)
        row = dict(
            contract="RetainedContributionSemantics",
            kind=kind,
            semantic_type=semantic_type,
            operation_key=operation_key,
            item_key="retained-definition:" + identity,
            pin=pin,
            anchors=anchors,
            occurrence_id=occurrence_identity(anchors),
            disposition="located_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=deps,
            value=source_value(meaning),
        )
        row["contribution_id"] = contribution_identity(row)
        products.append(row)
    operation = dict(
        operation_key=operation_key,
        question="locate_role_from_retained_definition_evidence",
        operation_version="declared-definition-location-1",
        outcome="succeeded",
        inspected_count=len(selected),
        emitted_count=len(products),
        computation_dependencies=tuple(dict.fromkeys(dependencies)),
    )
    return tuple(products), (operation,), tuple(coordinates.values())


@dataclass(frozen=True)
class PreparedDefinitionLocation:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Any

    def member(self, name, *, whole=True):
        (member,) = next(role.members for role in self.roles if role.role == name)
        if member.multiplicity != 1 or (whole and member.member is not None):
            raise ValueError("definition location requires exact scalar whole retained inputs")
        return member

    def run(self, source, components, selection):
        from .data_operation_admission import bound_data_operation_model
        from .data_operation_json import json_bytes
        from .declared_candidate_products import candidate_inspection_report
        from .declared_record_sources import DeclaredNativeFrameSource
        from .structural_products import DeclaredStructuralInputPin

        frame = DeclaredNativeFrameSource.acquire(
            self.prepared,
            source,
            self.member("source", whole=False),
            project=self.context.project_id,
        )
        selection = self.prepared.validate_json(
            "DdoDefinitionLocationSelection", json_bytes(selection)
        ).model_dump(mode="python", exclude_unset=True)
        reference = DeclaredStructuralInputPin.from_bound(
            self.member("components"), project=self.context.project_id
        ).model_dump(mode="json", exclude_none=True)
        products, operations, coordinates = definition_location_values(
            frame, components, reference, selection, check_active=self.check_active
        )
        model = bound_data_operation_model(self.prepared)
        result = candidate_inspection_report(
            self.prepared,
            model,
            frame,
            self.context,
            inspection_outcome="produced",
            contributions=products,
            operations=operations,
            coordinate_texts=coordinates,
            diagnostics={"version": "declared-definition-location-1"},
        )
        for name in ("components", "selection"):
            value = DeclaredStructuralInputPin.from_bound(
                self.member(name), project=self.context.project_id
            ).model_dump(mode="json", exclude_none=True)
            # The native witness addresses product/member through its canonical
            # reference; no historical task or source-view row is introduced.
            value.pop("member_id", None)
            result[name + "_input"] = value
        return self.prepared.validate_json(
            "DdoDefinitionLocationReport", json_bytes(result)
        ).model_dump(mode="python", exclude_unset=True)


def execute_definition_location(receiver, source, components, selection):
    return receiver.inputs.run(source, components, selection)


def definition_location_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active,
) -> dict:
    return PreparedDefinitionLocation(prepared, roles, context, check_active).run(**arguments)


@dataclass
class DefinitionLocationPlan:
    prepared: PreparedRelease
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("definition location requires its actual qualified binding")
        signature = inspect.signature(definition_location_kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = definition_location_operation_sources()
        return (
            yield from self.port.plan_cpu(
                definition_location_kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_definition_location_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    from corpus_structure.methods.definition_location import DefinitionLocationOperation

    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != DefinitionLocationOperation.__data_operation__["id"]:
        raise ValueError("definition location factory differs from its declared producer")
    receiver = DefinitionLocationOperation(None)
    plan = DefinitionLocationPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.definition_location_products.DefinitionLocationPlan.plan",
        authorize,
        (definition_location_assets(),),
        definition_location_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.definition_location_products.execute_definition_location",
                execute_definition_location,
            ),
            (
                "corpus_structure.semantic.definition_location_products.definition_location_kernel",
                definition_location_kernel,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
