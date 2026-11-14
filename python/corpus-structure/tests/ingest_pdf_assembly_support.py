"""Shared controlled inputs and builders for ingest pdf assembly support."""

from docling.datamodel.base_models import AssembledUnit, Cluster, ContainerElement, Table
from docling_core.types.doc import BoundingBox, DocItemLabel


def assembly():
    cluster = Cluster(
        id=1, label=DocItemLabel.FORM, bbox=BoundingBox(l=0, t=0, r=100, b=100), confidence=1
    )
    container = ContainerElement(label=DocItemLabel.FORM, id=1, page_no=1, cluster=cluster)
    child = Table(
        label=DocItemLabel.TABLE,
        id=2,
        page_no=1,
        cluster=cluster.model_copy(update={"id": 2, "label": DocItemLabel.TABLE}),
        otsl_seq=[],
        table_cells=[],
    )
    return AssembledUnit(elements=[container, child], body=[container, child], headers=[])
