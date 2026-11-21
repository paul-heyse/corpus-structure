"""Current-model acquisition and retention for the declared native protocol."""

from corpus_structure.model.compiled import model_projection

from .data_operation_wire import _prepare_protocol_content, _prepared_protocol


@model_projection
def ambient_protocol_content() -> bytes:
    return _prepare_protocol_content(None)


@model_projection
def ambient_protocol():
    # Archived inspection cannot evict the current capture's prepared protocol.
    return _prepared_protocol(ambient_protocol_content())


@model_projection
def ambient_contextual_fields():
    from .data_operation_wire import _contextual_fields, _wire_correspondence_document

    return _contextual_fields(_wire_correspondence_document())


@model_projection
def ambient_demand_interpretation():
    from .data_operation_wire import wire_contextual_fields, wire_contracts
    from .selected_support_contract import prepare_demand_interpretation

    return prepare_demand_interpretation(
        wire_contracts()["read_demand_result"]["output"], wire_contextual_fields()
    )
