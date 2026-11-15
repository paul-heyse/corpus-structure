"""Finite current structural facets, without publication inference.

The selected product supplies custody. Captured nominal schemas and the existing
family owners supply meaning; this reader neither reruns a producer nor converts
private readings into accepted scientific assertions.
"""

from dataclasses import dataclass

from .data_operation_json import json_bytes, json_loads
from .data_operation_wire import validate_wire_schema
from .identity import canonical_bytes
from .rich_queries import RichQueryRefused, RichQueryRow
from .structural_products import (
    DeclaredArtifactReport,
    DeclaredClauseReport,
    DeclaredComparisonReport,
    DeclaredConditionReport,
    DeclaredDefinitionApplicabilityReport,
    DeclaredDefinitionComponentsReport,
    DeclaredDossierReport,
    DeclaredStructuralProductReport,
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
        DeclaredDossierReport,
    )
}


@dataclass(frozen=True)
class CurrentNonRichRoot:
    nominal: str
    name: str
    family: str
    body: dict
    structural: DeclaredStructuralProductReport | None = None


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
    return CurrentNonRichRoot(
        kind.semantic_id,
        kind.name,
        family,
        structural.model_dump(mode="python", exclude_none=True),
        structural,
    )


def _row(selected, population, local, **meaning):
    return RichQueryRow(
        dict(population=population, row=meaning),
        canonical_bytes(
            [
                selected.use_id,
                selected.output["role"],
                selected.output["position"],
                selected.reference.product_id,
                population,
                local,
            ]
        ).decode(),
    )


def _base(selected, root):
    reference = selected.reference
    context = selected.context.identity_record
    return dict(
        reference=reference.model_dump(mode="python"),
        context=context,
        nominal=root.nominal,
        standing=root.body.get("standing"),
        scientific_truth="not-established",
    )


def nonrich_facets(
    selected,
    model,
    *,
    interpretation,
    assessment,
    member_id=None,
    max_members=100000,
    max_nested_members=1000,
):
    root = read_nonrich_root(model, selected)
    if member_id is not None:
        return
    # A report-local display facet is not a nominal product member. Its reference
    # stays the actual whole output, and broad dossier membership is not paged by
    # inventing member addresses. Larger complete facets refuse explicitly.
    pending = [root.body]
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
    base = _base(selected, root)
    yield _row(selected, "contribution", "whole", **base)
    if interpretation:
        yield _row(
            selected,
            "interpretation",
            "whole",
            **base,
            availability="observed",
            meaning=root.body,
            scope="typed-private-structural-reading",
        )
    if assessment:
        yield _row(
            selected,
            "assessment",
            "whole",
            **base,
            availability="observed",
            scope="captured-private-producer-judgments",
            judgments=root.body,
            public_admission="not-established",
        )
