"""Controlled inputs and builders shared by the m1 source preparation consumers."""

from typing import Any

from methods.record_assembly_support import source as declared_source


def source(text="Mean is average.\nX+Y\n12\n?", *, labels=("text", "formula", "table", "unknown")):
    chunks = text.split("\n")
    pieces, nodes = [], []
    offset = 0
    for index, (chunk, label) in enumerate(zip(chunks, labels, strict=True)):
        pointer = f"#/texts/{index}"
        nodes.append(dict(self_ref=pointer, label=label, text=chunk))
        if chunk:
            pieces.append(
                dict(item_ref=pointer, start=offset, end=offset + len(chunk), kind="native_text", source_field="text")
            )
            offset += len(chunk)
        if index < len(chunks) - 1:
            pieces.append(dict(start=offset, end=offset + 1, kind="synthetic_separator"))
            offset += 1
    return projection(text, pieces=pieces, items=nodes)


def projection(text, *, pieces, items, ancestors=(), identity=1):
    """Literal current source member; no publication or provider standing is implied."""
    return declared_source(text, identity=identity, pieces=pieces, items=items, ancestors=ancestors)


def _native_table_projection(cells, *, caption=None, note=None):
    """Explicit native geometry and repeated lexical text with independent cell addresses."""
    table: dict[str, Any] = dict(
        self_ref="#/tables/0",
        label="table",
        parent={"$ref": "#/groups/1"},
        data=dict(table_cells=cells),
    )
    nodes = [dict(self_ref="#/groups/1", label="section"), table]
    chunks: list[tuple[str, int | None, str]] = []
    for index, cell in enumerate(cells):
        if cell.get("text"):
            chunks.append(("#/tables/0", index, cell["text"]))
    for role, text in (("captions", caption), ("footnotes", note)):
        if text:
            pointer = f"#/texts/{role}"
            table[role] = [{"$ref": pointer}]
            nodes.append(
                dict(self_ref=pointer, label="caption" if role == "captions" else "text", text=text)
            )
            chunks.append((pointer, None, text))
    pieces, texts, offset = [], [], 0
    for pointer, index, text in chunks:
        if texts:
            texts.append("\n")
            pieces.append(dict(kind="synthetic_separator", start=offset, end=offset + 1))
            offset += 1
        pieces.append(
            dict(
                kind="native_text",
                item_ref=pointer,
                start=offset,
                end=offset + len(text),
                **(
                    dict(cell_index=index, source_field="cell_text")
                    if index is not None
                    else dict(source_field="text")
                ),
            )
        )
        texts.append(text)
        offset += len(text)
    text = "".join(texts)
    return text, pieces, nodes


def native_table_source(cells, *, caption=None, note=None):
    text, pieces, nodes = _native_table_projection(cells, caption=caption, note=note)
    return projection(text, pieces=pieces, items=nodes)


def table_cell(text, row, col, **flags):
    return dict(
        text=text,
        start_row_offset_idx=row,
        end_row_offset_idx=row + 1,
        start_col_offset_idx=col,
        end_col_offset_idx=col + 1,
        **flags,
    )


def _dense_table_cells():
    cells = [table_cell("value", 0, col, column_header=True) for col in range(1, 10)]
    for row in range(1, 31):
        cells.append(table_cell(f"row{row}", row, 0, row_header=True))
        cells.extend(table_cell("0", row, col) for col in range(1, 10))
    return tuple(cells)


def dense_table_source():
    return native_table_source(_dense_table_cells(), caption="Caption", note="Note")


def declared_dense_table_source():
    """Current original/member coordinates over the independent finite cell inventory."""
    return dense_table_source()
