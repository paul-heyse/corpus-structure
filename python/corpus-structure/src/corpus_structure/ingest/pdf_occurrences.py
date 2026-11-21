"""Shared native occurrence and cell addresses for Standard and Integrated records."""

from typing import Any


def iter_selected_occurrences(document, origins):
    from .pdf_hierarchy import native_nodes

    nodes = native_nodes(document)
    for pointer, node in nodes.items():
        label = str(node.label)
        origin = origins[id(node)]
        original_witness = getattr(origin, "evidence", {})
        row: dict[str, Any] = {
            "occurrence_id": pointer,
            "kind": "formula"
            if label == "formula"
            else "chart"
            if label == "picture"
            and getattr(node, "meta", None)
            and getattr(node.meta, "tabular_chart", None)
            else "item",
            "address_space": "selected_item",
            "precision": "item",
            "pointer": pointer,
        }
        if hasattr(node, "text"):
            row["text"] = node.text
        anchor = node
        while not getattr(anchor, "prov", ()) and anchor.parent is not None:
            anchor = anchor.parent.resolve(document)
        if getattr(anchor, "prov", ()):
            p = anchor.prov[0]
            box = p.bbox
            generated = origin.input_index != 0 and not original_witness.get("positioned_original")
            precision = "coarse" if generated else "item"
            if anchor is not node:
                row["grounding_pointer"] = anchor.self_ref
                precision = "inherited"
            row.update(
                precision=precision,
                page_no=p.page_no,
                region={
                    "address_space": "pdf_points",
                    "precision": precision,
                    "normalization": "inherited" if anchor is not node else "none",
                    "left": box.l,
                    "top": box.t,
                    "right": box.r,
                    "bottom": box.b,
                    "origin": "top_left" if box.coord_origin.value == "TOPLEFT" else "bottom_left",
                },
            )
        yield row
        cell_path, cells = native_cell_values(node)
        if cells:
            for i, cell in enumerate(cells):
                entry: dict[str, Any] = {
                    "occurrence_id": f"{pointer}{cell_path}/{i}",
                    "pointer": pointer,
                    "cell_index": i,
                    "kind": "cell",
                    "address_space": "native_cell",
                    "precision": "coarse" if origins[id(node)].input_index else "cell",
                    "text": cell.text,
                }
                if cell.bbox is not None and original_witness.get("positioned_grid"):
                    entry.update(
                        page_no=row["page_no"],
                        precision="cell",
                        region={
                            "address_space": "pdf_points",
                            "precision": "cell",
                            "normalization": "none",
                            "left": cell.bbox.l,
                            "top": cell.bbox.t,
                            "right": cell.bbox.r,
                            "bottom": cell.bbox.b,
                            "origin": "top_left",
                        },
                    )
                elif row.get("region"):
                    entry.update(
                        page_no=row["page_no"],
                        grounding_pointer=pointer,
                        region={
                            **row["region"],
                            "precision": "inherited",
                            "normalization": "inherited",
                        },
                        precision="inherited",
                    )
                yield entry


def native_cell_values(node):
    if str(node.label) == "table":
        return "/data/table_cells", node.data.table_cells
    if str(node.label) == "picture":
        chart = getattr(getattr(node, "meta", None), "tabular_chart", None)
        return (
            "/meta/tabular_chart/chart_data/table_cells",
            chart.chart_data.table_cells if chart else (),
        )
    return "", ()
