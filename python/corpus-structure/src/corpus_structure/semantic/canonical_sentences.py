"""Cheap declared native-to-canonical value projection, without NLP execution."""


def canonical_sentence_values(inventory: dict) -> dict:
    """Declared value projection; native label changes cannot alter canonical units."""
    packets = inventory["members"]
    tokens = {
        packet["member_id"]: packet["body"]
        for packet in packets
        if packet["body"]["record_type"] == "token"
    }
    sentences = [
        {
            **{
                key: packet["body"][key]
                for key in ("local_id", "block_id", "ordinal", "start", "end")
            },
            "tokens": [
                {
                    key: tokens[identifier][key]
                    for key in (
                        "local_id",
                        "ordinal",
                        "start",
                        "end",
                        "space",
                        "role",
                        "piece_indices",
                    )
                }
                for identifier in packet["body"]["token_ids"]
            ],
        }
        for packet in packets
        if packet["body"]["record_type"] == "sentence"
    ]
    return {
        **{key: inventory[key] for key in ("source", "selectors", "outcome", "coverage")},
        "sentences": sentences,
    }


def canonical_sentence_operation_sources():
    from pathlib import Path

    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    return PythonSourceCollection(
        tuple(
            PythonSource(module, path.read_bytes(), str(path))
            for module, path in (
                (
                    "corpus_structure.methods.canonical_sentences",
                    root / "methods/canonical_sentences.py",
                ),
                ("corpus_structure.semantic.canonical_sentences", Path(__file__)),
            )
        )
    )
