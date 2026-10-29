from pathlib import Path

from corpus_structure.core.evidence import MacroDef
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.expression_context import bind_expression_context


def test_only_referenced_macro_closure_changes_expression_meaning():
    raw = {"kind": "expression", "language": "latex", "expression": r"\E x"}
    first = {r"\E": MacroDef(body=r"\A"), r"\A": MacroDef(body="1"), r"\unused": MacroDef(body="9")}
    second = {**first, r"\A": MacroDef(body="2")}
    a = bind_expression_context(raw, first)
    b = bind_expression_context(raw, second)
    assert set(a["macro_context"]) == {r"\E", r"\A"}
    assert a != b
    assert bind_expression_context(raw, {**first, r"\unused": MacroDef(body="different")}) == a
    assert "macro_context" not in raw
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(SourceBundle("core", (SourceArtifact("core", root.read_bytes()),)))
    qualification: dict[str, object] = {"modality": "asserted", "polarity": True}
    assert prepared.fact_identity("z", "s", "p", a, qualification) != prepared.fact_identity(
        "z", "s", "p", b, qualification
    )
    value = prepared.validate_python("Value", a)
    assert value.model_dump(exclude_unset=True)["macro_context"][r"\A"]["body"] == "1"
    cyclic = bind_expression_context(raw, {r"\E": MacroDef(body=r"\E")})
    assert set(cyclic["macro_context"]) == {r"\E"}
