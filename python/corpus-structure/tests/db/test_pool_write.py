"""The current Arrow publication boundary exposes no arbitrary admitted-table writer."""


def test_arbitrary_admitted_arrow_write_api_is_retired() -> None:
    from corpus_structure.semantic import arrow_publication as write

    assert not hasattr(write, "write_arrow")
    assert callable(write.publish_arrow)
