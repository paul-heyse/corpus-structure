"""Compare fixed and multilevel Splink settings on one controlled private pair frame."""

from collections import Counter
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import unicodedata

import duckdb
from splink import DuckDBAPI, Linker, SettingsCreator
from splink.comparison_level_library import (
    ArrayIntersectLevel,
    CustomLevel,
    ElseLevel,
    ExactMatchLevel,
    JaroWinklerLevel,
    Or,
)
from splink.comparison_library import CustomComparison, ExactMatch

from corpus_structure.semantic.artifact_identity import normalized_code, predict_artifact_pairs


FRAME = (
    Path(__file__).resolve().parent.parent
    / "2026-11-06_wce-completion-repair/source-references/source-reference.json"
)
PRIOR = 0.1
EXACT = {"code_m": 0.9, "code_u": 0.01, "title_m": 0.8, "title_u": 0.05}
TITLE_M = [0.48, 0.21, 0.12, 0.12, 0.07]
TITLE_U = [0.05, 0.02, 0.04, 0.12, 0.77]
NAMESPACE = "controlled-chapter"
# Raw title, code and authentic alias state are independent prepared columns.
CASES = (
    ("unicode_exact", ("Résumé", "1", None), ("Re\u0301sume\u0301", "1", ["Résumé"]), (1, 4)),
    ("generic_exact", ("Summary", "1", None), ("Summary", "2", []), (0, 4)),
    ("title_to_alias", ("Grid", "3", None), ("Sample totals", "3", ["Grid"]), (1, 3)),
    ("alias_to_alias", ("Distribution", "4", ["D"]), ("Chance", "4", ["D"]), (1, 3)),
    ("fuzzy_high", ("abcdefghij", "5", None), ("abcdefghik", "5", []), (1, 2)),
    ("fuzzy_transposition", ("martha", "6", []), ("marhta", "6", None), (1, 2)),
    ("fuzzy_moderate", ("abcdefgh", "7", None), ("abcdeq", "7", None), (1, 1)),
    ("disagreement", ("Cats", "8", None), ("Dogs", "8", []), (1, 0)),
    ("missing_name", (None, "9", None), ("Density", "9", []), (1, -1)),
    ("malformed_code", ("Sample", "??", None), ("Sample", "10", []), (-1, 4)),
)


def normal_title(value):
    return unicodedata.normalize("NFC", value).strip().casefold() if value else None


def prepared(identity, values):
    raw_title, raw_code, observed_aliases = values
    return dict(
        unique_id=identity,
        raw_title=raw_title,
        raw_code=raw_code,
        code=normalized_code(raw_code),
        namespace=NAMESPACE,
        title=normal_title(raw_title),
        fixed_title=raw_title.casefold().strip() if raw_title else None,
        alias_state="unknown" if observed_aliases is None else "observed" if observed_aliases else "known_empty",
        aliases=[normal_title(alias) for alias in observed_aliases or ()],
    )


def comparisons():
    absent_code = CustomLevel(
        "code_l IS NULL OR code_r IS NULL OR namespace_l IS NULL OR namespace_r IS NULL "
        "OR namespace_l <> namespace_r",
        "Code unavailable",
    ).configure(is_null_level=True)
    alias_match = Or(
        CustomLevel("list_contains(aliases_l, title_r) OR list_contains(aliases_r, title_l)"),
        ArrayIntersectLevel("aliases"),
    ).configure(label_for_charts="Observed alias agreement")
    absent_name = CustomLevel(
        "NOT ((title_l IS NOT NULL AND title_r IS NOT NULL) "
        "OR (title_l IS NOT NULL AND alias_state_r = 'observed') "
        "OR (title_r IS NOT NULL AND alias_state_l = 'observed') "
        "OR (alias_state_l = 'observed' AND alias_state_r = 'observed'))",
        "Name unavailable",
    ).configure(is_null_level=True)
    return [
        CustomComparison(
            [absent_code, ExactMatchLevel("code"), ElseLevel()], output_column_name="scoped_code"
        ).configure(m_probabilities=[0.9, 0.1], u_probabilities=[0.01, 0.99]),
        CustomComparison(
            [
                absent_name,
                ExactMatchLevel("title", term_frequency_adjustments=True),
                alias_match,
                JaroWinklerLevel("title", 0.95),
                JaroWinklerLevel("title", 0.85),
                ElseLevel(),
            ],
            output_column_name="name",
        ).configure(m_probabilities=TITLE_M, u_probabilities=TITLE_U),
    ]


def predict(connection, rows, keys, compare, prior):
    api = DuckDBAPI(connection=connection)
    settings = SettingsCreator(
        link_type="dedupe_only",
        probability_two_random_records_match=prior,
        comparisons=compare,
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=True,
    )
    linker = Linker(api.register(rows, dataset_display_name="artifacts"), settings)
    result = predict_artifact_pairs(linker, keys)
    return result, linker


def main():
    raw_frame = FRAME.read_bytes()
    reference_cases = json.loads(raw_frame)["artifact_lineage_pairs"]
    assert all("reference_anchor" in row and "caption_anchor" in row for row in reference_cases)
    rows = [
        prepared(f"{case}:{side}", values)
        for case, left, right, _ in CASES
        for side, values in (("l", left), ("r", right))
    ]
    # These four additional corpus-frequency opportunities have no judged pair in this probe.
    rows.extend(prepared(f"frequency:{i}", ("Summary", f"20{i}", None)) for i in range(4))
    keys = tuple((f"{case}:l", f"{case}:r") for case, *_ in CASES)
    fixed = [
        ExactMatch(column).configure(
            m_probabilities=[m, 1 - m], u_probabilities=[u, 1 - u]
        )
        for column, m, u in (
            ("code", EXACT["code_m"], EXACT["code_u"]),
            ("fixed_title", EXACT["title_m"], EXACT["title_u"]),
        )
    ]
    with duckdb.connect() as connection:
        control, _ = predict(connection, rows, keys, fixed, PRIOR)
    with duckdb.connect() as connection:
        candidate, linker = predict(connection, rows, keys, comparisons(), PRIOR)
        tf = sorted(
            linker.table_management.compute_tf_table("title").as_record_list(),
            key=lambda row: row["title"],
        )
    by_case = {key[0].removesuffix(":l"): candidate[key] for key in keys}
    assert by_case["generic_exact"]["mw_tf_adj_name"] < by_case["unicode_exact"]["mw_tf_adj_name"] < 0
    assert by_case["title_to_alias"]["mw_tf_adj_name"] == 0
    assert by_case["missing_name"]["mw_name"] == 0
    assert by_case["malformed_code"]["mw_scoped_code"] == 0
    results = []
    for (case, _, _, expected), key in zip(CASES, keys, strict=True):
        scored = candidate[key]
        levels = scored["gamma_scoped_code"], scored["gamma_name"]
        assert levels == expected, (case, levels, expected)
        results.append(dict(
            case=case,
            exact_probability=control[key]["match_probability"],
            multilevel_probability=scored["match_probability"],
            evidence={name: value for name, value in scored.items() if name.startswith(("gamma_", "mw_", "tf_"))},
        ))
    return dict(
        outcome="partial",
        source_frame=dict(
            sha256=sha256(raw_frame).hexdigest(),
            reference_to_caption=len(reference_cases),
            reference_judgments=Counter(row["judgment"] for row in reference_cases),
            alias_states=Counter(row["alias_state"] for row in reference_cases),
            revision_states=Counter(row["revision_identity"] for row in reference_cases),
            usable_same_lineage_judgments=0,
        ),
        provider=dict(splink=version("splink"), duckdb=version("duckdb")),
        policy=dict(
            standing="private_controlled_mechanism",
            prior=PRIOR,
            exact_control=EXACT,
            parameters="provisional authored values; no calibration",
            scoped_code_m=[0.9, 0.1],
            scoped_code_u=[0.01, 0.99],
            names_m=TITLE_M,
            names_u=TITLE_U,
            normalized_title="NFC, trim, casefold",
            jaro_winkler_bins=[0.95, 0.85],
            tf_population_count=len(rows),
        ),
        prepared_rows=rows,
        tf_lookup=tf,
        exact_pair_results=results,
    )


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False, sort_keys=True))
