"""Render the independent GS120 case frame from the neutral retained source packets."""

from hashlib import file_digest
from itertools import product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
PACKETS = (
    ROOT
    / "docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/attempt001/source-packets"
)


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def freeze(*, marginal_roles=False):
    inputs, views, anchors = {}, {}, {}
    table_census = {}
    for packet in sorted(PACKETS.glob("grinstead*.json")):
        record = json.loads(packet.read_text())
        filename = str(packet.relative_to(ROOT))
        inputs[filename] = {
            "sha256": digest(packet),
            "parent_sha256": record["parent_pdf_sha256"],
            "excerpt_sha256": record["source_pdf_sha256"],
            "pages": record["parent_physical_pages"],
        }
        for view in record["views"]:
            key = view["passage"]["passage_id"]
            views[key] = (view, filename, record["page_map"])
            for item in view["native_context"]["items"]:
                if item["label"] != "table":
                    continue
                table_key = (view["source"]["native_content_digest"], item["self_ref"])
                table_census[table_key] = {
                    "view_id": view["native_view"]["id"],
                    "native_content_digest": table_key[0],
                    "native_pointer": table_key[1],
                    "footnote_links": item["footnotes"],
                }

    assert len(inputs) == 12 and len(views) == 48
    assert sorted(p for info in inputs.values() for p in info["pages"]) == list(range(191, 311))

    def anchor(name, view_id, pointer, *, quote=None, cell=None):
        passage_id = f"gs120-recovered-source-{view_id}"
        view, packet, page_map = views[passage_id]
        pages = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in page_map}
        item = next(i for i in view["native_context"]["items"] if i["self_ref"] == pointer)
        target = item["data"]["table_cells"][cell] if cell is not None else item
        native_text = target["text"]
        if quote is None:
            quote = native_text
        assert quote and native_text.count(quote) == 1, (name, native_text, quote)
        local_start = native_text.index(quote)
        local_end = local_start + len(quote)
        spans = []
        for piece in view["native_context"]["pieces"]:
            if piece.get("item_ref") != pointer or piece.get("cell_index") != cell:
                continue
            start, end = piece["start"], piece["end"]
            projected = view["passage"]["text"][start:end]
            if projected == native_text:
                spans.append([start + local_start, start + local_end])
            elif projected.count(quote) == 1:
                offset = projected.index(quote)
                spans.append([start + offset, start + offset + len(quote)])
        assert len(spans) <= 1, (name, spans)
        anchors[name] = {
            "packet": packet,
            "passage_id": passage_id,
            "source": view["source"],
            "native_pointer": pointer if cell is None else f"{pointer}/data/table_cells/{cell}",
            "native_field": "text",
            "native_span": [local_start, local_end],
            "quote": quote,
            "projected_span": spans[0] if spans else None,
            "projection_state": "located" if spans else "native_only",
            "physical_pages": sorted({pages[p["page_no"]] for p in item["prov"]}),
        }
        if cell is not None:
            anchors[name]["table_cell"] = {
                "index": cell,
                "rows": [target["start_row_offset_idx"], target["end_row_offset_idx"]],
                "columns": [target["start_col_offset_idx"], target["end_col_offset_idx"]],
                "native_row_header": target["row_header"],
                "native_column_header": target["column_header"],
            }
        return name

    for cell in range(12):
        anchor(f"dice-cell-{cell}", 124, "#/tables/0", cell=cell)
    anchor("dice-caption", 124, "#/texts/37")
    anchor("dice-method", 124, "#/texts/30")
    anchor("normal-parameters", 116, "#/texts/199")
    anchor("normal-z-definition", 117, "#/texts/21")
    anchor("normal-z-term", 117, "#/texts/21", quote="standard normal random variable")
    anchor("normal-standardization", 117, "#/texts/34")
    anchor("normal-inverse-transform", 117, "#/texts/35")
    anchor("normal-transform-use", 117, "#/texts/30", quote="X = σZ + µ")
    anchor("normal-x-declaration", 143, "#/texts/24")
    anchor("normal-x-z-bridge", 143, "#/texts/26")
    anchor("normal-mean", 143, "#/texts/27")
    anchor("normal-variance", 143, "#/texts/28")
    anchor("gamma-n-lambda", 116, "#/texts/82")
    anchor("gamma-half-shape", 153, "#/texts/63")
    anchor("gamma-unit-shape", 153, "#/texts/67")
    anchor("gamma-chi-square", 154, "#/texts/72")
    anchor("bibliographic-marker", 117, "#/texts/20", quote="See Box and Muller.9")
    anchor("bibliographic-note", 117, "#/texts/25")

    cases = []

    def case(name, family, state, members, expected, explanation):
        cases.append({
            "id": name,
            "family": family,
            "judgment": state,
            "anchors": members,
            "expected": expected,
            "reason": explanation,
        })

    for cell, band, measure, role in (
        (8, 0, 3, "count"),
        (9, 0, 4, "relative_frequency"),
        (10, 1, 5, "count"),
        (11, 1, 6, "relative_frequency"),
    ):
        other_band = 1 - band
        competing_measure = measure + (2 if band == 0 else -2)
        value, row, sample, header = [f"dice-cell-{i}" for i in (cell, 7, band, measure)]
        case(
            f"GS120-WCE-R15-DICE-{cell}", "scoped_table_composition", "supported",
            [value, row, sample, header, "dice-cell-2", "dice-caption", "dice-method"],
            {"value": value, "row_label": row, "row_header": "dice-cell-2",
             "sample_size_header": sample, "measure_header": header, "value_role": role},
            "The first Winning row crosses two merged sample-size bands, each with its own "
            "Frequency and Relative Frequency columns. The Winning heading and prose support "
            "the row role even though the retained first data cell has row_header false.",
        )
        case(
            f"GS120-WCE-R15-DICE-CROSS-{cell}", "scoped_table_composition", "unsupported",
            [value, f"dice-cell-{other_band}", f"dice-cell-{competing_measure}", sample, header],
            {"excluded_sample_size_header": f"dice-cell-{other_band}",
             "excluded_measure_header": f"dice-cell-{competing_measure}"},
            "Repeated measure wording does not override the exact disjoint native column spans.",
        )

    case(
        "GS120-WCE-R03-DICE-NOTE", "table_note_scope", "unstated_in_inspected_scope",
        ["dice-caption", "dice-method"],
        {"table_note_link": "absent_in_retained_table", "row_or_band_applicability": "unestablished"},
        "The native table has no footnote links. The selected caption and methodological prose "
        "give no row- or band-specific note. This is bounded to these retained regions.",
    )
    case(
        "GS120-WCE-R03-BIB-NOTE", "bibliographic_note_scope", "supported",
        ["bibliographic-marker", "bibliographic-note", "normal-z-definition"],
        {"source": "bibliographic-marker", "target": "bibliographic-note",
         "relationship": "bibliographic_reference", "table_applicability": "unsupported"},
        "Body marker 9 and matching note 9 cite an article for the surrounding normal-variate "
        "discussion. The marker does not delimit any table, row, band, or cell.",
    )
    case(
        "GS120-WCE-R15-NORMAL-USE", "located_usage", "supported",
        ["normal-z-definition", "normal-z-term", "normal-transform-use",
         "normal-standardization", "normal-inverse-transform"],
        {"use": "normal-transform-use", "target": "normal-z-definition",
         "relationship": "uses_standard_normal_Z_as_input", "target_symbol": "Z"},
        "The nearby definition supplies the standard-normal Z that the transform uses to obtain "
        "the parametrized X. This use is outside the defining span itself.",
    )
    case(
        "GS120-WCE-R03-NORMAL-LOCATION-SCALE", "parameter_synthesis", "supported",
        ["normal-x-declaration", "normal-x-z-bridge", "normal-mean", "normal-variance", "normal-parameters"],
        {"local_variable": "X", "mean": "µ", "standard_deviation": "σ", "variance": "σ²",
         "scale_is_variance": False},
        "The declaration introduces the nonstandard X with µ and σ. The bridge and two local "
        "formulas state E(X)=µ and V(X)=σ², distinguishing the scale from its squared value.",
    )
    case(
        "GS120-WCE-R15-NORMAL-FALSE-BRIDGE", "located_usage", "unsupported",
        ["normal-x-z-bridge", "normal-x-declaration", "normal-z-definition"],
        {"source_variable": "X", "target_variable": "Z", "excluded_relationship": "same_variable"},
        "The affine transform makes X and Z distinct local variables with different distribution "
        "roles. Related variables cannot be merged as same-variable identity.",
    )
    case(
        "GS120-WCE-R03-GAMMA-LOCAL-PARAMETERS", "parameter_synthesis", "supported",
        ["gamma-n-lambda", "gamma-half-shape", "gamma-unit-shape", "gamma-chi-square"],
        {"source_116_local_parameters": ["λ", "n"], "source_153_local_parameters": ["λ", "β"],
         "source_154_chi_square_parameters": {"λ": "1/2", "β": "n/2"},
         "global_symbol_equivalence": "unestablished"},
        "The cases explicitly state local parameter roles and values. The symbol n in the "
        "chi-squared passage counts summands and supplies degrees of freedom. It cannot be "
        "identified with β by glyph or family resemblance alone.",
    )

    # The population is defined by source regions and roles before considering any candidate route.
    # Each tuple records an authored positive about two inspected native items.
    groups = {
        "chapter5_figures": [
            ("5.3", 110, 131, 110, 138, "Flying-bomb hit counts and their plotted frequencies."),
            ("5.5", 115, 35, 115, 19, "Powerball choices and the spike graph of that lottery data."),
            ("5.12", 119, 82, 119, 85, "Chi-squared result with three degrees of freedom."),
        ],
        "chapter7_figures": [
            ("7.2", 149, 191, 150, 2, "Two uniform densities, supported over the sum's finite domain."),
            ("7.3", 150, 28, 150, 12, "Two exponential densities, with the negative-side zero result."),
            ("7.4", 154, 84, 154, 89, "Chi-squared density with five degrees of freedom."),
            ("7.5", 154, 85, 154, 100, "Repeated rolls of a fair die, distinguished from the reference density."),
            ("7.6", 155, 147, 154, 119, "The several summand counts in the uniform convolution."),
            ("7.7", 155, 173, 155, 154, "The several summand counts in the normal convolution."),
            ("7.8", 155, 177, 156, 184, "The several summand counts in the exponential convolution."),
        ],
        "chapter5_6_tables": [
            ("5.8", 119, 72, 118, 65, "Observed grades and gender for the calculus class."),
            ("5.9", 119, 73, 118, 66, "Expected values for the comparison with the observed grades."),
            ("6.1", 124, 30, 124, 37, "The two frequency simulations of the dice game."),
        ],
    }
    strata, pairs = [], []
    for group, entries in groups.items():
        keys = []
        interpretations = {}
        supported_pairs = set()
        prefix = "Table" if group.endswith("tables") else "Figure"
        for code, ref_view, ref_pointer, cap_view, cap_pointer, reason in entries:
            reference = f"{group}-{code}-reference"
            caption = f"{group}-{code}-caption"
            anchor(f"{reference}-context", ref_view, f"#/texts/{ref_pointer}")
            anchor(reference, ref_view, f"#/texts/{ref_pointer}", quote=f"{prefix} {code}")
            anchor(caption, cap_view, f"#/texts/{cap_pointer}")
            keys.append((code, reference, caption))
            interpretations[code] = reason
            supported_pairs.add((reference, caption))
        strata.append({"id": group, "reference_anchors": [ref for _, ref, _ in keys],
                       "caption_anchors": [cap for _, _, cap in keys],
                       "pair_selection": "all_reference_by_caption_pairs_within_stratum"})
        for (left_code, reference, _), (right_code, _, caption) in product(keys, repeat=2):
            supported = (reference, caption) in supported_pairs
            pairs.append({
                "id": f"GS120-WCE-R19-{group}-{left_code}-{right_code}",
                "stratum": group,
                "reference_anchor": reference,
                "reference_context_anchor": f"{reference}-context",
                "caption_anchor": caption,
                "judgment": "supported" if supported else "unsupported",
                "reason": interpretations[left_code] if supported else (
                    f"The reference concerns {prefix} {left_code}. {interpretations[left_code]} "
                    f"The caption identifies the distinct {prefix} {right_code}. "
                    f"{interpretations[right_code]}"
                ),
                "revision_identity": "unestablished",
                "alias_state": "unknown",
            })

    assert len(pairs) == 67 and sum(row["judgment"] == "supported" for row in pairs) == 13
    if marginal_roles:
        # The observed table has blank margins. Its adjacent schematic and prose give an
        # independently located interpretation of those roles rather than a guessed header.
        definitions = anchor("marginal-definitions", 111, "#/texts/16")
        observed_caption = anchor("observed-caption", 111, "#/texts/14")
        schematic_caption = anchor("schematic-caption", 111, "#/texts/15")
        role_cases = []
        for i, role, scope in (
            (3, "observed_count", "Female and Democrat"),
            (4, "observed_count", "Female and Republican"),
            (7, "observed_count", "Male and Democrat"),
            (8, "observed_count", "Male and Republican"),
            (5, "row_marginal_count", "Female"),
            (9, "row_marginal_count", "Male"),
            (10, "column_marginal_count", "Democrat"),
            (11, "column_marginal_count", "Republican"),
            (12, "grand_total_count", "whole data set"),
        ):
            cell = anchor(f"marginal-observed-{i}", 111, "#/tables/0", cell=i)
            peer = anchor(f"marginal-schematic-{i}", 111, "#/tables/1", cell=i)
            role_cases.append({
                "id": f"GS120-WCE-R18-MARGINAL-{i}",
                "observed_cell": cell,
                "same_position_schematic_cell": peer,
                "role": role,
                "scope": scope,
                "measure": "count",
                "other_units": "unstated",
                "note_applicability": "unestablished",
                "proof": [cell, peer, definitions, observed_caption, schematic_caption],
            })
        role_anchors = {key: value for key, value in anchors.items() if key.startswith(
            ("marginal-", "observed-caption", "schematic-caption")
        )}
        return {
            "protocol": "wce-gs120-audit-repair-marginal-role-reference-1",
            "baseline": "3187254d3",
            "author": "source_refs",
            "inputs": {value["packet"]: inputs[value["packet"]] for value in role_anchors.values()},
            "anchors": role_anchors,
            "cases": role_cases,
            "source_question": (
                "Which cells in the observed table are individual counts, row or column "
                "marginals, or the grand total under the shared schematic and prose?"
            ),
            "source_limit": (
                "Same-position schematic and prose support the roles jointly. Native geometry "
                "has no named header for the marginal cells, and bare integers do not identify "
                "their role. No table note or unit interpretation beyond count is established."
            ),
        }
    return {
        "protocol": "wce-gs120-audit-repair-source-reference-1",
        "baseline": "3187254d3",
        "author": "source_refs",
        "source_exposure": "shared development, previously exposed, only neutral packets read",
        "coordinate_contract": "zero-based half-open Unicode offsets on pinned native or projected text",
        "inputs": inputs,
        "anchors": anchors,
        "cases": cases,
        "artifact_lineage_strata": strata,
        "artifact_lineage_pairs": pairs,
        "native_table_note_link_census": sorted(
            table_census.values(), key=lambda row: (row["view_id"], row["native_pointer"])
        ),
    }


if __name__ == "__main__":
    assert sys.argv[1:] in ([], ["--marginal-roles"])
    print(json.dumps(freeze(marginal_roles=bool(sys.argv[1:])), ensure_ascii=False, indent=2,
                     sort_keys=True))
