"""Reconstruct portable table correspondence from selected source and contributions."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
from itertools import product
from math import isclose, log
from typing import Any

from corpus_structure.methods.local_interpretation import local_constraint_id
from corpus_structure.methods.table_interpretation import (
    CORRESPONDENCE_POLICY_VERSION,
    MAX_BAND_EDGES,
    TableCorrespondenceRequest,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_interpretation_reports import (
    validate_local_interpretation_report,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_interpretation import (
    Candidate,
    CandidateKind,
    CandidateSelection,
    Choice,
    CompositeEvent,
    Decision,
    DependenceScope,
    Dependency,
    DependencyKind,
    HardConstraint,
    LogPotential,
    interpret_local,
)

_CELL = re.compile(r"^(.*)/data/table_cells/([0-9]+)$")
_CUE = re.compile(
    r"\bdata shown in Table ([0-9]+(?:\.[0-9]+)+)\b.*?"
    r"\bgeneral data table will look as shown in Table ([0-9]+(?:\.[0-9]+)+)\b",
    re.IGNORECASE,
)
_DECLARATIONS = {
    "row_sum": r"row sums by (\w+) and (\w+)",
    "column_sum": r"column sums by (\w+) and (\w+)",
    "sample_count": r"size of the data set will be denoted by (\w+)",
    "observed_count": r"ijth entry in the table will be denoted by (sij)",
}
_ROLES = {"header", "note", "unit", "value_role"}
_UNAVAILABLE = "No eligible table correspondence band in the selected source view."


def _retained_rows(rows, source):
    context = source["context"]
    nodes = {item["self_ref"]: item for item in (*context["items"], *context["ancestors"])}
    cell_pieces = {
        (p["item_ref"], int(p["cell_index"]))
        for p in context["pieces"]
        if p.get("source_field") == "cell_text"
    }
    prose = {
        p["item_ref"]
        for p in context["pieces"]
        if p["kind"] == "native_text" and "cell_index" not in p
    }
    participants, cells, declarations = {}, {}, {}
    for row in rows:
        if row["semantic_type"] != "structural.located_participant" or len(row["anchors"]) != 1:
            continue
        key = row["contribution_id"]
        anchor = row["anchors"][0]
        pointer = anchor["pointer"]
        meaning = source_python(row["value"])
        participants[key] = row, anchor, meaning
        if (anchor["space"], anchor["precision"]) != ("native", "exact"):
            continue
        if match := _CELL.fullmatch(pointer):
            table, index = match.group(1), int(match.group(2))
            if (table, index) not in cell_pieces:
                continue
            data = nodes[table]["data"]["table_cells"][index]
            body = data["text"]
            if (
                anchor["start"] != 0
                or anchor["end"] != len(body)
                or anchor["source_piece"] != body
                or meaning["text"] != body
                or row["pin"]["source_view_id"] != source["source_view_id"]
                or row["pin"]["product_digest"] != source["ref"]["native_product"]["content_digest"]
            ):
                continue
            cells[key] = (
                table,
                body,
                tuple(
                    data[f"{bound}_{axis}_offset_idx"]
                    for axis in ("row", "col")
                    for bound in ("start", "end")
                ),
            )
        elif meaning.get("role") == "table_role_declaration" and pointer in prose:
            pattern = _DECLARATIONS.get(meaning.get("measure_role"))
            body = nodes[pointer]["text"]
            if (
                pattern is None
                or meaning.get("source_pointer") != pointer
                or meaning.get("text") != anchor["source_piece"]
                or body[anchor["start"] : anchor["end"]] != anchor["source_piece"]
            ):
                continue
            cue = _CUE.search(body)
            symbols = re.fullmatch(pattern, anchor["source_piece"], re.IGNORECASE)
            if cue and symbols and cue[1] != cue[2]:
                declarations[key] = (meaning["region"], anchor, cue.groups(), symbols.groups())
    return nodes, participants, cells, declarations


def _band_edges(rows, participants, cells):
    bands = defaultdict(list)
    for row in rows:
        if row["semantic_type"] != "structural.scoped_attachment":
            continue
        meaning = source_python(row["value"])
        role, subject, target = meaning["relation"], meaning["subject_id"], meaning["target_id"]
        if subject not in cells or target not in participants or role not in _ROLES:
            continue
        source, anchor, subject_meaning = participants[subject]
        target_row, target_anchor, target_meaning = participants[target]
        region, _, (r0, r1, c0, c1) = cells[subject]
        component = row.get("component") or {}
        basis = meaning.get("basis")
        key = row["contribution_id"]
        if (
            meaning["protocol"] != "scoped-attachment-1"
            or meaning["region"] != region
            or meaning["scope"] != region
            or row["pin"] != source["pin"]
            or target_row["pin"] != source["pin"]
            or subject_meaning["role"] != "cell"
            or component.get("kind") != "scoped_attachment"
            or component.get("attachment_contribution_id") != subject
            or component.get("target_contribution_id") != target
            or component.get("attachment_kind") != role
            or component.get("scope") != region
            or meaning["dependencies"] != row["computation_dependencies"]
            or basis not in {b["kind"] for b in component["bases"]}
            or (
                target not in cells
                and target_meaning["role"] not in {"note", "table_role_declaration"}
            )
        ):
            continue
        target_cell = cells.get(target)
        header = (
            target_cell is not None
            and target_cell[0] == region
            and target_meaning["role"] == "header"
            and role in {"header", "unit", "value_role"}
            and basis in {"native_geometry", "matched_cue"}
        )
        disjoint = False
        direct = role in {"note", "unit"} and basis == "matched_cue"
        axis = role if role == "value_role" else key
        if header and target_cell is not None:
            tr0, tr1, tc0, tc1 = target_cell[2]
            disjoint = c1 <= tc0 or tc1 <= c0
            direct |= tc0 <= c0 and c1 <= tc1 and tr1 <= r0
            if role == "header":
                axis = f"({tr0}, {tr1})"
        bands[region, r0, r1].append(
            dict(
                id=key,
                axis=f"{subject}/{role}/{axis}",
                role=role,
                direct=direct,
                disjoint=disjoint,
                evidence=[key, subject, target],
                basis=basis,
                deps=row["computation_dependencies"],
                anchor=anchor,
                target_anchor=target_anchor,
                coordinates=(r0, r1, c0, c1),
                target_cell=target_cell,
            )
        )
    return bands


def _caption_pointers(nodes, table, code):
    pattern = re.compile(r"^Table\s+" + re.escape(code) + r"(?=:|\s|$)", re.IGNORECASE)
    for citation in nodes[table].get("captions", ()):
        pointer = citation["$ref"]
        if pointer not in nodes:
            raise ValueError("table correspondence lacks an original caption item")
        caption = nodes[pointer]
        if caption.get("label") == "caption" and pattern.search(caption["text"]):
            yield pointer


def _premises(edges, region, nodes, declarations, source) -> list[dict[str, Any]]:
    bindings = defaultdict(list)
    for edge in edges:
        target = edge["target_cell"]
        if (
            edge["role"] != "value_role"
            or edge["basis"] != "matched_cue"
            or target is None
            or target[0] == region
            or not re.fullmatch(r"\s*[0-9]+\s*", edge["anchor"]["source_piece"])
        ):
            continue
        schematic, symbol, target_extent = target
        r0, r1, c0, c1 = edge["coordinates"]
        tr0, tr1, tc0, tc1 = target_extent
        if not (r0 < tr1 and tr0 < r1 and c0 < tc1 and tc0 < c1):
            continue
        symbol = symbol.strip()
        symbol = "sij" if re.fullmatch(r"s[0-9]+", symbol) else symbol.lower()
        for declaration in sorted(set(edge["deps"]) & declarations.keys()):
            owner, anchor, codes, symbols = declarations[declaration]
            if owner != region or symbol not in {part.lower() for part in symbols}:
                continue
            for a, b in product(
                _caption_pointers(nodes, region, codes[0]),
                _caption_pointers(nodes, schematic, codes[1]),
            ):
                bindings[schematic, anchor["pointer"], a, b].append(
                    (
                        edge,
                        {
                            "dependencies": [*edge["evidence"], declaration],
                            "observed_anchor": edge["anchor"]["anchor_id"],
                            "schematic_anchor": edge["target_anchor"]["anchor_id"],
                            "declaration_anchor": anchor["anchor_id"],
                            "alignment": "exact"
                            if edge["coordinates"] == target_extent
                            else "overlap",
                        },
                    )
                )
    ref = source["ref"]
    premises = []
    for (schematic, declaration, observed_caption, schematic_caption), members in sorted(
        bindings.items()
    ):
        distinct = all(
            len({edge["evidence"][side] for edge, _ in members}) == len(members) for side in (1, 2)
        )
        fixed = (
            len(bindings) == 1
            and distinct
            and all(proof["alignment"] == "exact" for _, proof in members)
            and all(
                nodes[region]["data"].get(k) == nodes[schematic]["data"].get(k)
                for k in ("num_rows", "num_cols")
            )
        )
        premise = dict(
            source_revision=ref["native_product"]["content_digest"],
            source_view_id=source["source_view_id"],
            source_projection=ref["projection_digest"],
            source_recipe=ref["recipe_digest"],
            observed_table=region,
            schematic_table=schematic,
            observed_caption=observed_caption,
            schematic_caption=schematic_caption,
            declaration_pointer=declaration,
            bindings={edge["id"]: proof for edge, proof in members},
        )
        premises.append(
            {
                **premise,
                "identity": "table-correspondence:" + sha256(canonical_bytes(premise)).hexdigest(),
                "standing": "fixed" if fixed else "alternative",
            }
        )
    return premises


def _band_request(scope_id, deps, edges, premises, ref, scale):
    policy = f"table-policy:{CORRESPONDENCE_POLICY_VERSION}:correspondence:{scale:g}"
    revision = ref["native_product"]["content_digest"]
    model = "table-model:" + revision
    ontology = "table-ontology:scoped-table-roles"
    weight = scale * log(2.0)
    axes = defaultdict(list)
    for edge in edges:
        axes[edge["axis"]].append(edge)
    auxiliary = bool(premises) and (len(premises) != 1 or premises[0]["standing"] != "fixed")
    decisions, direct, compatibility, scopes, masks = [], [], [], [], []
    events = defaultdict(list)
    if auxiliary:
        decisions.append(
            Decision(
                "M",
                (
                    Candidate(
                        "unresolved",
                        CandidateKind.UNRESOLVED,
                        "shared correspondence unresolved within retained evidence",
                    ),
                    *(Candidate(p["identity"]) for p in premises),
                ),
            )
        )
        direct.append(
            LogPotential(
                "shared-correspondence-evidence",
                ("M",),
                (0.0, *(weight for _ in premises)),
                tuple(sorted({policy, *(p["identity"] for p in premises)})),
            )
        )
    for axis, members in sorted(axes.items()):
        role = members[0]["role"]
        options = [Candidate("unresolved", CandidateKind.UNRESOLVED, "retained scope incomplete")]
        if role in {"note", "unit"}:
            options.append(Candidate("does_not_apply"))
        by_key = {e["id"]: e for e in members}
        options.extend(Candidate(key) for key in sorted(by_key))
        decisions.append(Decision(axis, tuple(options)))
        direct.append(
            LogPotential(
                "source-choice:" + axis,
                (axis,),
                tuple(
                    weight
                    if (edge := by_key.get(c.key)) and edge["direct"] and not edge["disjoint"]
                    else 0.0
                    for c in options
                ),
                (*sorted({dep for edge in members for dep in edge["evidence"]}), policy),
            )
        )
        forbidden = {edge["id"] for edge in members if edge["disjoint"]}
        if forbidden:
            masks.append(
                HardConstraint(
                    "source-disjoint:" + axis,
                    (axis,),
                    tuple(c.key not in forbidden for c in options),
                    tuple(
                        sorted(
                            {
                                ontology,
                                *(dep for key in forbidden for dep in by_key[key]["evidence"]),
                            }
                        )
                    ),
                )
            )
        events[role].extend(
            (Choice(axis, c.key),) for c in options if c.key in by_key and c.key not in forbidden
        )
        linked = [
            (p["identity"], proof)
            for p in premises
            for key, proof in p["bindings"].items()
            if key in by_key
        ]
        if linked:
            evidence = tuple(
                sorted(
                    {
                        policy,
                        *(key for key, _ in linked),
                        *(dep for _, proof in linked for dep in proof["dependencies"]),
                    }
                )
            )
            choices = ([{}] if auxiliary else []) + [p["bindings"] for p in premises]
            values = tuple(
                (weight if proof["alignment"] == "exact" else weight / 2) if proof else 0.0
                for bindings, c in product(choices, options)
                for proof in (bindings.get(c.key),)
            )
            scope = ("M", axis) if auxiliary else (axis,)
            compatibility.append(
                LogPotential("correspondence-role:" + axis, scope, values, evidence)
            )
            if auxiliary:
                scopes.append(
                    DependenceScope(
                        scope,
                        evidence,
                        "One source correspondence conditions this local role reading",
                    )
                )
    dependencies = (
        *(Dependency(dep, DependencyKind.OBSERVATION, revision) for dep in deps),
        *(
            Dependency(p["identity"], DependencyKind.CONTEXT, ref["projection_digest"])
            for p in sorted(premises, key=lambda item: item["identity"])
        ),
        Dependency(model, DependencyKind.MODEL, revision),
        Dependency(ontology, DependencyKind.ONTOLOGY, CORRESPONDENCE_POLICY_VERSION),
        Dependency("table-executor:exact-local-1", DependencyKind.CONTEXT, "exact-local-1"),
        Dependency(policy, DependencyKind.POLICY, CORRESPONDENCE_POLICY_VERSION),
    )
    request = TableCorrespondenceRequest(
        decisions=tuple(decisions),
        potentials=tuple(direct + compatibility),
        constraints=tuple(masks),
        dependencies=dependencies,
        selection=CandidateSelection(
            scope_id,
            deps,
            exclusions=tuple(
                "source-disjoint:" + e["id"]
                for e in sorted(edges, key=lambda item: item["id"])
                if e["disjoint"]
            ),
        ),
        model_dependency_id=model,
        ontology_dependency_id=ontology,
        policy_dependency_id=policy,
        events=tuple(
            CompositeEvent(
                "any-" + role,
                f"At least one retained {role} reading applies in this table row",
                tuple(derivations),
            )
            for role, derivations in sorted(events.items())
            if derivations
        ),
        dependence_scopes=tuple(scopes),
        correspondence_status="ambiguous" if auxiliary else "fixed" if premises else "unavailable",
        correspondence_reason=(
            "Retained source permits competing or unresolved correspondence."
            if auxiliary
            else (
                "No exact observed-to-schematic declaration and eligible matched cells in this row."
            )
            if not premises
            else None
        ),
    )
    return {**asdict(request), "correspondence_premises": premises}


def _same_semantics(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return (
            isclose(a, b, rel_tol=1e-12, abs_tol=1e-12) if float in (type(a), type(b)) else a == b
        )
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same_semantics(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_semantics(a[k], b[k]) for k in a)
    return a == b


def verify_table_correspondence(report, source):
    from corpus_structure.methods.table_interpretation import _correspondence_request_adapter

    body = report["body"]
    config = report["configuration"]
    operations = [o for o in body["contribution_operations"] if "local_interpretation" in o]
    rows = body["contributions"]
    if config.get("interpretation_mode") != "correspondence":
        if any(
            o["local_interpretation"]["policy_version"] == CORRESPONDENCE_POLICY_VERSION
            for o in operations
        ):
            raise ValueError("table correspondence differs from selected policy")
        return
    scale = float(config["interpretation_weight_scale"])
    if scale not in (0.5, 1.0, 2.0):
        raise ValueError("invalid retained table correspondence weight")
    nodes, participants, cells, declarations = _retained_rows(rows, source)
    bands = _band_edges(rows, participants, cells)
    expected = {}
    by_id = {row["contribution_id"]: row for row in rows}
    for (region, r0, r1), edges in bands.items():
        premises = _premises(edges, region, nodes, declarations, source)
        ids = {key for edge in edges for key in edge["evidence"]}
        ids.update(
            key
            for p in premises
            for proof in p["bindings"].values()
            for key in proof["dependencies"]
        )
        retained = [by_id[key] for key in sorted(ids)]
        deps = tuple(
            sorted(ids | {dep for row in retained for dep in row["computation_dependencies"]})
        )
        question = f"source correspondence for {region} row [{r0}, {r1})"
        scope = local_constraint_id(question, retained, deps)
        reason = None
        request = None
        if len(edges) > MAX_BAND_EDGES:
            reason = (
                f"Exact correspondence policy permits at most {MAX_BAND_EDGES}"
                " retained attachments per row."
            )
        else:
            request = _band_request(scope, deps, edges, premises, source["ref"], scale)
        expected[scope] = question, sorted(ids), deps, reason, request
    if not bands and body["operation_version"] != "8":
        question = f"source correspondence availability for view {source['source_view_id']}"
        deps = ("source-projection:" + source["ref"]["projection_digest"],)
        expected[local_constraint_id(question, (), deps)] = question, [], deps, _UNAVAILABLE, None
    if (
        len(operations) != len(expected)
        or {o["operation_key"] for o in operations} != expected.keys()
    ):
        raise ValueError("table correspondence differs from complete source-conditioned bands")
    for operation in operations:
        validate_local_interpretation_report(operation, rows)
        question, ids, deps, reason, request = expected[operation["operation_key"]]
        actual = operation["local_interpretation"]
        if (
            operation["question"] != question
            or list(actual["contribution_ids"]) != ids
            or tuple(actual["dependencies"]) != deps
            or actual["policy_version"] != CORRESPONDENCE_POLICY_VERSION
        ):
            raise ValueError("table correspondence source or policy differs")
        if request is None:
            if actual["outcome"] != "not_run" or actual["reason"] != reason:
                raise ValueError("table correspondence unavailable outcome differs")
            continue
        if "request" not in actual or not _same_semantics(
            source_python(actual["request"]), request
        ):
            raise ValueError("table correspondence request differs from source-conditioned replay")
        result = source_python(actual["result"])
        if result["outcome"] in {"cancelled", "resource_limit"}:
            continue
        recomputed = asdict(
            interpret_local(_correspondence_request_adapter().validate_python(request))
        )
        result["search"].pop("elapsed_seconds")
        recomputed["search"].pop("elapsed_seconds")
        if not _same_semantics(result, recomputed):
            raise ValueError("table correspondence result differs from replay")


def verify_table_correspondence_closure(root, manifest):
    from .review_bundle import _detached_relation

    reports = [
        row
        for row in _detached_relation(root, manifest, "reports")
        if row.get("method") == "structure.scoped_relations"
        and (row.get("body") or {}).get("operation_version") in {"8", "9"}
        and (row.get("body") or {}).get("outcome") in {"produced", "empty"}
    ]
    ids = {report["origin_unit_id"] for report in reports}
    if ids:
        sources = {
            source["source_view_id"]: source
            for source in _detached_relation(root, manifest, "sources")
            if source["source_view_id"] in ids
        }
        for report in reports:
            source = sources.get(report["origin_unit_id"])
            if source is None:
                raise ValueError("table correspondence verification lacks exact retained source")
            verify_table_correspondence(report, source)
