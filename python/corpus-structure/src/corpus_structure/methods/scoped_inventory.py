"""Invocation-owned inventories for the scoped-relations set trial.

Python retains lexical interpretation and publication identities. These relations answer
the finite geometry questions once per population, preserving original encounter order.
"""

import sys
from collections import defaultdict
from contextlib import AbstractContextManager

import pyarrow as pa
import pyarrow.compute as pc
from duckdb import col, count_all, fn, lit, star

from corpus_structure.analytics import connection
from corpus_structure.methods.source_preparation import NativeTableTarget

_EXTENT_SCHEMA = pa.schema(
    [("extent_ordinal", pa.int64()), ("start", pa.int64()), ("end", pa.int64())]
)
_CELL_SCHEMA = pa.schema(
    [
        ("pointer", pa.string()),
        ("cell_index", pa.int64()),
        ("row_start", pa.int64()),
        ("row_end", pa.int64()),
        ("col_start", pa.int64()),
        ("col_end", pa.int64()),
        ("column_header", pa.bool_()),
        ("row_header", pa.bool_()),
    ]
)


def source_piece_schema(prepared):
    """Project the admitted native-piece declaration; analytical ordinals stay local."""
    fields = {
        prop.name: prop for prop in prepared.index.definitions["DdoNativeSourcePiece"].properties
    }
    types = {"kind": pa.string(), "item_ref": pa.string(), "start": pa.int64(), "end": pa.int64()}
    result = []
    for name, physical in types.items():
        prop = fields[name]
        expected = "integer" if pa.types.is_integer(physical) else "string"
        if prop.multivalued or prop.range != expected:
            raise ValueError("native piece declaration differs from its analytical field " + name)
        result.append(pa.field(name, physical, nullable=not prop.required))
    return pa.schema(result)


class ScopedInventory(AbstractContextManager):
    """One analytical connection and one acquired population per source invocation."""

    def __init__(self, pieces, selected_ranges, *, piece_schema=None):
        self._context = connection()
        self._original_pieces = tuple(pieces)
        self._selected_ranges = selected_ranges
        self._piece_schema = piece_schema

    def __enter__(self):
        self.engine = self._context.__enter__()
        try:
            schema = self._piece_schema or pa.schema(
                [
                    ("kind", pa.string()),
                    ("item_ref", pa.string()),
                    ("start", pa.int64()),
                    ("end", pa.int64()),
                ]
            )
            columns = {
                field.name: pa.array(
                    [piece.get(field.name) for piece in self._original_pieces], type=field.type
                )
                for field in schema
            }
            source = self.engine.from_arrow(
                pa.table(
                    {
                        "piece_ordinal": pa.array(
                            range(len(self._original_pieces)), type=pa.int64()
                        ),
                        "pointer": columns["item_ref"],
                        "start": columns["start"],
                        "end": columns["end"],
                        "native_text": pc.equal(columns["kind"], "native_text"),
                    }
                )
            ).set_alias("piece")
            ranges = self.engine.from_arrow(
                pa.table(
                    {
                        "range_start": pa.array(
                            [start for start, _ in self._selected_ranges], type=pa.int64()
                        ),
                        "range_end": pa.array(
                            [end for _, end in self._selected_ranges], type=pa.int64()
                        ),
                    }
                )
            ).set_alias("scope")
            self._pieces = source.join(
                ranges,
                (col("scope", "range_start") <= col("piece", "start"))
                & (col("piece", "start") < col("piece", "end"))
                & (col("piece", "end") <= col("scope", "range_end")),
                how="semi",
            )
            indices = (
                self._pieces.select(col("piece_ordinal")).sort(col("piece_ordinal")).fetchall()
            )
            self.pieces = tuple(self._original_pieces[index] for (index,) in indices)
            self._selected_ordinals = {index: selected for selected, (index,) in enumerate(indices)}
            return self
        except BaseException:
            self._context.__exit__(*sys.exc_info())
            raise

    def __exit__(self, *exc):
        return self._context.__exit__(*exc)

    def containing_pieces(self, extents):
        """Locate all requested spans together, preserving first-piece tie behavior."""
        selected = tuple(dict.fromkeys(extents))
        questions = self.engine.from_arrow(
            pa.Table.from_pylist(
                [
                    dict(extent_ordinal=index, start=start, end=end)
                    for index, (start, end) in enumerate(selected)
                ],
                schema=_EXTENT_SCHEMA,
            )
        ).set_alias("extent")
        pieces = self._pieces.filter(col("native_text")).set_alias("piece")
        matches = questions.join(
            pieces,
            (col("piece", "start") <= col("extent", "start"))
            & (col("extent", "start") < col("extent", "end"))
            & (col("extent", "end") <= col("piece", "end")),
        ).aggregate([col("extent", "extent_ordinal"), fn("min", col("piece", "piece_ordinal"))])
        return {
            selected[extent]: self._original_pieces[piece]
            for extent, piece in matches.sort(col("extent_ordinal")).fetchall()
        }

    def table_targets(self, tables):
        """Range joins and ordered windows reproduce native nested-header paths."""
        cells = []
        originals = {}
        for pointer, table in tables.items():
            originals[pointer] = table.get("data", {}).get("table_cells", ())
            for index, cell in enumerate(originals[pointer]):
                coordinates = {
                    name: cell.get(f"{boundary}_{axis}_offset_idx")
                    for name, boundary, axis in (
                        ("row_start", "start", "row"),
                        ("row_end", "end", "row"),
                        ("col_start", "start", "col"),
                        ("col_end", "end", "col"),
                    )
                }
                cells.append(
                    dict(
                        pointer=pointer,
                        cell_index=index,
                        **{
                            name: value if type(value) is int else None
                            for name, value in coordinates.items()
                        },
                        column_header=bool(cell.get("column_header")),
                        row_header=bool(cell.get("row_header")),
                    )
                )
        relation = self.engine.from_arrow(pa.Table.from_pylist(cells, schema=_CELL_SCHEMA))
        target = relation.filter(~(col("column_header") | col("row_header"))).set_alias("target")
        valid = (
            (col("row_start") >= 0)
            & (col("row_start") < col("row_end"))
            & (col("col_start") >= 0)
            & (col("col_start") < col("col_end"))
        )
        targets = target.filter(valid).set_alias("target")
        headers = relation.filter(valid).set_alias("header")
        shared = col("target", "pointer") == col("header", "pointer")
        row = targets.join(
            headers.filter(col("row_header")).set_alias("header"),
            shared
            & (col("header", "row_start") <= col("target", "row_start"))
            & (col("target", "row_end") <= col("header", "row_end"))
            & (col("header", "col_end") <= col("target", "col_start")),
        )
        column = targets.join(
            headers.filter(col("column_header")).set_alias("header"),
            shared
            & (col("header", "col_start") <= col("target", "col_start"))
            & (col("target", "col_end") <= col("header", "col_end"))
            & (col("header", "row_end") <= col("target", "row_start")),
        )

        def path_columns(matches, axis, along, across):
            return matches.select(
                col("target", "pointer").alias("pointer"),
                col("target", "cell_index").alias("cell_index"),
                lit(axis).alias("axis"),
                col("header", along + "_start").alias("a"),
                col("header", along + "_end").alias("b"),
                col("header", across + "_start").alias("c"),
                col("header", across + "_end").alias("d"),
                col("header", "cell_index").alias("header_index"),
            )

        paths = path_columns(row, "row", "col", "row").union_all(
            path_columns(column, "column", "row", "col")
        )
        partition = [col("pointer"), col("cell_index"), col("axis")]
        order = [col(name) for name in ("a", "b", "c", "d", "header_index")]
        checked = paths.select(
            star(),
            *(
                fn("lag", col(name))
                .over(partition_by=partition, order_by=order)
                .alias("previous_" + name)
                for name in ("b", "c", "d")
            ),
        ).select(
            star(),
            (
                (col("previous_b") > col("a"))
                | (col("previous_c") > col("c"))
                | (col("previous_d") < col("d"))
            ).alias("invalid"),
        )
        paths_by_target = defaultdict(list)
        invalid = set()
        for pointer, index, axis, _a, _b, _c, _d, header, _pb, _pc, _pd, bad in checked.sort(
            *partition, *order
        ).fetchall():
            key = pointer, index, axis
            paths_by_target[key].append(header)
            if bad:
                invalid.add(key)
        result = {pointer: [] for pointer in tables}
        for pointer, index, start, end, *_rest in target.sort(
            col("pointer"), col("cell_index")
        ).fetchall():
            row_extent = (
                (start, end) if start is not None and end is not None and 0 <= start < end else None
            )
            result[pointer].append(
                NativeTableTarget(
                    index,
                    row_extent,
                    ()
                    if (pointer, index, "row") in invalid
                    else tuple(paths_by_target[pointer, index, "row"]),
                    ()
                    if (pointer, index, "column") in invalid
                    else tuple(paths_by_target[pointer, index, "column"]),
                )
            )
        return {pointer: tuple(targets) for pointer, targets in result.items()}

    def contained_pairs(self, containers, members, *, overlap=False):
        """Return all containment answers in the populations' explicit encounter order."""
        outer = self.engine.from_arrow(
            pa.Table.from_pylist(
                [dict(extent_ordinal=i, start=a, end=b) for i, (a, b) in enumerate(containers)],
                schema=_EXTENT_SCHEMA,
            )
        ).set_alias("outer")
        inner = self.engine.from_arrow(
            pa.Table.from_pylist(
                [dict(extent_ordinal=i, start=a, end=b) for i, (a, b) in enumerate(members)],
                schema=_EXTENT_SCHEMA,
            )
        ).set_alias("inner")
        condition = (
            (col("outer", "start") < col("inner", "end"))
            & (col("inner", "start") < col("outer", "end"))
            if overlap
            else (col("outer", "start") <= col("inner", "start"))
            & (col("inner", "start") < col("inner", "end"))
            & (col("inner", "end") <= col("outer", "end"))
        )
        pairs = outer.join(inner, condition).select(
            col("outer", "extent_ordinal").alias("container"),
            col("inner", "extent_ordinal").alias("member"),
        )
        result = defaultdict(list)
        for container, member in pairs.sort(col("container"), col("member")).fetchall():
            result[container].append(member)
        return result

    def ordered_matches(self, questions, declarations, cues):
        """Range-join ordered witnesses after counting every earlier symbol cue."""
        query_schema = pa.schema(
            [
                ("ordinal", pa.int64()),
                ("parent", pa.string()),
                ("position", pa.int64()),
                ("symbol", pa.string()),
                ("name", pa.string()),
                ("start", pa.int64()),
            ]
        )
        declaration_schema = pa.schema(
            [
                ("ordinal", pa.int64()),
                ("parent", pa.string()),
                ("position", pa.int64()),
                ("symbol", pa.string()),
                ("name", pa.string()),
                ("cue", pa.int64()),
                ("end", pa.int64()),
            ]
        )
        query = self.engine.from_arrow(
            pa.Table.from_pylist(questions, schema=query_schema)
        ).set_alias("query")
        cue = self.engine.from_arrow(
            pa.table(
                {
                    "position": pa.array([position for position, _ in cues], type=pa.int64()),
                    "symbol": pa.array([symbol for _, symbol in cues], type=pa.string()),
                }
            )
        ).set_alias("cue")
        unique = (
            query.join(
                cue,
                (col("cue", "symbol") == col("query", "symbol"))
                & (col("cue", "position") < col("query", "start")),
            )
            .select(
                col("query", "ordinal").alias("question"),
                col("cue", "position").alias("cue"),
            )
            .select(star(), count_all().over(partition_by=[col("question")]).alias("matches"))
            .filter(col("matches") == 1)
            .set_alias("unique")
        )
        selected = (
            query.join(unique, col("query", "ordinal") == col("unique", "question"))
            .select(
                col("query", "ordinal"),
                col("query", "parent"),
                col("query", "position"),
                col("query", "symbol"),
                col("query", "name"),
                col("query", "start"),
                col("unique", "cue"),
            )
            .set_alias("selected")
        )
        declaration = self.engine.from_arrow(
            pa.Table.from_pylist(declarations, schema=declaration_schema)
        ).set_alias("declaration")
        condition = (
            (col("selected", "parent") == col("declaration", "parent"))
            & (col("selected", "position") > col("declaration", "position"))
            & (col("declaration", "end") <= col("selected", "start"))
            & (col("selected", "symbol") == col("declaration", "symbol"))
            & (col("selected", "name") == col("declaration", "name"))
            & (col("selected", "cue") == col("declaration", "cue"))
        )
        return (
            selected.join(declaration, condition)
            .select(
                col("selected", "ordinal").alias("question"),
                col("declaration", "ordinal").alias("declaration"),
            )
            .sort(col("question"), col("declaration"))
            .fetchall()
        )

    def artifact_matches(self, records):
        """Join retained artifact subjects to their own pointer and containing piece."""
        schema = pa.schema(
            [
                ("ordinal", pa.int64()),
                ("pointer", pa.string()),
                ("start", pa.int64()),
                ("end", pa.int64()),
            ]
        )
        subjects = self.engine.from_arrow(
            pa.Table.from_pylist(
                [
                    dict(
                        ordinal=index,
                        pointer=record.payload["pointer"],
                        start=record.span("subject")[0],
                        end=record.span("subject")[1],
                    )
                    for index, record in enumerate(records)
                ],
                schema=schema,
            )
        ).set_alias("subject")
        piece = self._pieces.filter(col("native_text")).set_alias("piece")
        matches = piece.join(
            subjects,
            (col("piece", "pointer") == col("subject", "pointer"))
            & (col("piece", "start") <= col("subject", "start"))
            & (col("subject", "start") < col("subject", "end"))
            & (col("subject", "end") <= col("piece", "end")),
        ).select(
            col("piece", "piece_ordinal").alias("piece"), col("subject", "ordinal").alias("subject")
        )
        result = defaultdict(list)
        for piece, subject in matches.sort(col("piece"), col("subject")).fetchall():
            result[self._selected_ordinals[piece]].append(subject)
        return result

    def table_counterparts(self, tables, pairs):
        """Prepare each table once, then match all observed/schematic pairs by extent."""
        import re

        coordinates = (
            "start_row_offset_idx",
            "end_row_offset_idx",
            "start_col_offset_idx",
            "end_col_offset_idx",
        )
        schema = pa.schema(
            [
                ("pointer", pa.string()),
                ("ordinal", pa.int64()),
                ("text", pa.string()),
                ("numeric", pa.bool_()),
                *((name, pa.int64()) for name in coordinates),
            ]
        )
        cells = []
        for pointer in dict.fromkeys(pointer for pair in pairs for pointer in pair):
            for index, cell in enumerate(tables[pointer]["data"]["table_cells"]):
                if not all(type(cell.get(name)) is int for name in coordinates):
                    continue
                text = cell.get("text", "").strip()
                cells.append(
                    dict(
                        pointer=pointer,
                        ordinal=index,
                        text=text,
                        numeric=re.fullmatch(r"\d+", text) is not None,
                        **{name: cell[name] for name in coordinates},
                    )
                )
        relation = self.engine.from_arrow(pa.Table.from_pylist(cells, schema=schema))
        observed = relation.filter(col("numeric")).set_alias("observed")
        schematic = relation.select(
            star(),
            fn("max", col("ordinal"))
            .over(partition_by=[col("pointer"), *(col(name) for name in coordinates)])
            .alias("last"),
        )
        schematic = schematic.filter(col("ordinal") == col("last")).set_alias("schematic")
        pair_schema = pa.schema(
            [
                ("pair", pa.int64()),
                ("observed_pointer", pa.string()),
                ("schematic_pointer", pa.string()),
            ]
        )
        selected = self.engine.from_arrow(
            pa.Table.from_pylist(
                [
                    dict(pair=index, observed_pointer=left, schematic_pointer=right)
                    for index, (left, right) in enumerate(pairs)
                ],
                schema=pair_schema,
            )
        ).set_alias("pair")
        left = (
            selected.join(observed, col("pair", "observed_pointer") == col("observed", "pointer"))
            .select(
                col("pair", "pair"),
                col("pair", "schematic_pointer"),
                col("observed", "ordinal"),
                *(col("observed", name) for name in coordinates),
            )
            .set_alias("left")
        )
        condition = col("left", "schematic_pointer") == col("schematic", "pointer")
        for name in coordinates:
            condition = condition & (col("left", name) == col("schematic", name))
        matches = left.join(schematic, condition).select(
            col("left", "pair").alias("pair"),
            col("left", "ordinal").alias("observed"),
            col("schematic", "ordinal").alias("schematic"),
            col("schematic", "text").alias("symbol"),
        )
        result = {pair: [] for pair in pairs}
        for pair, observed, schematic, symbol in matches.sort(
            col("pair"), col("observed")
        ).fetchall():
            result[pairs[pair]].append((observed, schematic, symbol))
        return result

    def formula_matches(self, questions, symbols):
        """Join all declaration names to their exact adjacent formula occurrences."""
        schema = pa.schema(
            [("ordinal", pa.int64()), ("formula", pa.int64()), ("name", pa.string())]
        )
        query = self.engine.from_arrow(
            pa.Table.from_pylist(
                [
                    dict(ordinal=i, formula=formula, name=name)
                    for i, (formula, name) in enumerate(questions)
                ],
                schema=schema,
            )
        ).set_alias("question")
        candidates = self.engine.from_arrow(
            pa.Table.from_pylist(
                [
                    dict(ordinal=i, formula=formula, name=symbol["name"])
                    for i, (formula, symbol) in enumerate(symbols)
                ],
                schema=schema,
            )
        ).set_alias("symbol")
        matches = query.join(
            candidates,
            (col("question", "formula") == col("symbol", "formula"))
            & (col("question", "name") == col("symbol", "name")),
        ).select(
            col("question", "ordinal").alias("question"), col("symbol", "ordinal").alias("symbol")
        )
        result = defaultdict(list)
        for question, symbol in matches.sort(col("question"), col("symbol")).fetchall():
            result[question].append(symbol)
        return result

    def preceding_matches(self, questions, declarations):
        """Find the unique earlier declaration under the same parent and selected passage."""
        schema = pa.schema(
            [
                ("ordinal", pa.int64()),
                ("passage", pa.int64()),
                ("piece", pa.int64()),
                ("parent", pa.string()),
                ("symbol", pa.string()),
                ("record_count", pa.int64()),
            ]
        )
        query = self.engine.from_arrow(pa.Table.from_pylist(questions, schema=schema)).set_alias(
            "query"
        )
        prior = self.engine.from_arrow(pa.Table.from_pylist(declarations, schema=schema)).set_alias(
            "prior"
        )
        matches = (
            query.join(
                prior,
                (col("query", "passage") == col("prior", "passage"))
                & (col("query", "parent") == col("prior", "parent"))
                & (col("query", "symbol") == col("prior", "symbol"))
                & (col("prior", "piece") < col("query", "piece")),
            )
            .select(
                col("query", "ordinal").alias("question"),
                col("prior", "ordinal").alias("declaration"),
                col("prior", "record_count"),
            )
            .select(star(), count_all().over(partition_by=[col("question")]).alias("matches"))
        )
        return dict(
            matches.filter((col("matches") == 1) & (col("record_count") == 1))
            .select(col("question"), col("declaration"))
            .sort(col("question"))
            .fetchall()
        )

    def unique_matches(self, mentions, captions):
        """Resolve captions only where the complete key population has one occurrence."""
        schema = pa.schema([("ordinal", pa.int64()), ("kind", pa.string()), ("code", pa.string())])
        left = self.engine.from_arrow(
            pa.Table.from_pylist(
                [dict(ordinal=i, kind=key[0], code=key[1]) for i, key in enumerate(mentions)],
                schema=schema,
            )
        ).set_alias("mention")
        right = (
            self.engine.from_arrow(
                pa.Table.from_pylist(
                    [dict(ordinal=i, kind=key[0], code=key[1]) for i, key in enumerate(captions)],
                    schema=schema,
                )
            )
            .select(
                star(), count_all().over(partition_by=[col("kind"), col("code")]).alias("matches")
            )
            .filter(col("matches") == 1)
            .set_alias("caption")
        )
        return (
            left.join(
                right,
                (col("mention", "kind") == col("caption", "kind"))
                & (col("mention", "code") == col("caption", "code")),
            )
            .select(
                col("mention", "ordinal").alias("mention"),
                col("caption", "ordinal").alias("caption"),
            )
            .sort(col("mention"))
            .fetchall()
        )
