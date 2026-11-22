"""Finite current structural facets, without publication inference.

The selected product supplies custody. Captured nominal schemas and the existing
family owners supply meaning; this reader neither reruns a producer nor converts
private readings into accepted scientific assertions.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from .data_operation_json import json_bytes, json_loads
from .data_operation_wire import validate_wire_schema
from .refusal_types import RichQueryRefused
from .rich_queries import RichQueryRow
from .structural_products import (
    DeclaredArtifactReport,
    DeclaredClauseReport,
    DeclaredComparisonReport,
    DeclaredConditionReport,
    DeclaredDefinitionApplicabilityReport,
    DeclaredDefinitionComponentsReport,
    DeclaredDossierReport,
    DeclaredLearnedDefinitionComponentsReport,
    DeclaredNamedDefinitionComponentsReport,
    DeclaredStructuralProductReport,
    DeclaredSyntaxDefinitionComponentsReport,
)

_STRUCTURAL = {
    "urn:corpus:structural:" + cls.__name__: cls
    for cls in (
        DeclaredArtifactReport,
        DeclaredClauseReport,
        DeclaredComparisonReport,
        DeclaredConditionReport,
        DeclaredDefinitionApplicabilityReport,
        DeclaredDefinitionComponentsReport,
        DeclaredNamedDefinitionComponentsReport,
        DeclaredLearnedDefinitionComponentsReport,
        DeclaredSyntaxDefinitionComponentsReport,
        DeclaredDossierReport,
    )
}


@dataclass(frozen=True)
class CurrentNonRichRoot:
    nominal: str
    structural: DeclaredStructuralProductReport


def nonrich_family(model, nominal):
    """Select only actual captured nominal owners, never operation-name guesses."""
    kind = next((item for item in model.kinds if item.semantic_id == nominal), None)
    if kind is None:
        return None
    return "structural" if nominal in _STRUCTURAL else None


def read_nonrich_root(model, selected) -> CurrentNonRichRoot:
    family = nonrich_family(model, selected.nominal)
    if family is None or selected.reference.member_id is not None:
        raise RichQueryRefused("current family interpretation requires its actual selected whole")
    kind = next(item for item in model.kinds if item.semantic_id == selected.nominal)
    expected = next(
        item.key
        for item in model.identities
        if item.owner == kind.semantic_id and item.domain == "kind"
    )
    if not kind.complete or expected != selected.reference.kind_contract:
        raise RichQueryRefused("source interpretation lacks its complete captured nominal contract")
    schema = json_loads(kind.facts).get("json_schema")
    if schema is None:
        raise RichQueryRefused("structural interpretation lacks its captured nominal schema")
    validate_wire_schema(schema, json_loads(json_bytes(selected.body)))
    structural = _STRUCTURAL[selected.nominal].model_validate_json(json_bytes(selected.body))
    return CurrentNonRichRoot(kind.semantic_id, structural)


def _row(population, **meaning):
    return RichQueryRow(dict(population=population, row=meaning))


def _base(selected, body):
    reference = selected.reference
    context = selected.context.identity_record
    return dict(
        reference=reference.model_dump(mode="python"),
        context=context,
        nominal=selected.nominal,
        standing=body.get("standing"),
        scientific_truth="not-established",
    )


def nonrich_facets(
    scope,
    selected,
    *,
    interpretation,
    assessment,
    member_id=None,
    max_members=100000,
    max_nested_members=1000,
) -> Iterator[RichQueryRow]:
    if member_id is not None:
        return
    from .selected_structural_projection import structural_report

    try:
        report = structural_report(scope, selected)
    except RichQueryRefused:
        raise
    except (PermissionError, ValueError) as error:
        raise RichQueryRefused(str(error)) from error
    body = report.model_dump(mode="python", exclude_none=True)
    # A report-local display facet is not a nominal product member. Its reference
    # stays the actual whole output, and broad dossier membership is not paged by
    # inventing member addresses. Larger complete facets refuse explicitly.
    pending = [body]
    collections = 0
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, (list, tuple)):
            collections += len(item)
            if collections > min(max_members, max_nested_members):
                raise RichQueryRefused("structural facet exceeds its complete nested-member bound")
            pending.extend(item)
    base = _base(selected, body)
    yield _row("contribution", **base)
    if interpretation:
        yield _row(
            "interpretation",
            **base,
            availability="observed",
            meaning=body,
            scope="typed-private-structural-reading",
        )
    if assessment:
        yield _row(
            "assessment",
            **base,
            availability="observed",
            scope="captured-private-producer-judgments",
            judgments=body,
            public_admission="not-established",
        )
