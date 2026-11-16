"""Independent current source members for pure bounded context controls."""

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredRecordSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources
from corpus_structure.semantic.source_products import native_projection_identity, source_subject

A = '["fixture:context:1",null]'
B = '["fixture:context:2",null]'
C = '["fixture:context:3",null]'


def source(identity, text, *, pieces=None, ancestors=(), membership="direct",
           document="document:context", recognition=()):
    """Supplied semantic addresses, without a native publication or provider claim."""
    if pieces is None:
        pieces = [dict(kind="native_text", item_ref=f"#/texts/{identity}", start=0, end=len(text))]
    pointers = list(dict.fromkeys(piece["item_ref"] for piece in pieces if "item_ref" in piece))
    items = [dict(self_ref=pointer, label="text") for pointer in pointers]
    parents = [dict(self_ref=pointer, label="section") for pointer in ancestors]
    projection = native_projection_identity(text, pieces, items, recognition, parents)
    coordinate = dict(document=document, document_subject=original_document_subject(document),
                      projection=projection, section_pointer=f"#/groups/{identity}", membership=membership)
    value = dict(source=coordinate, text=text, pieces=pieces, items=items, ancestors=parents,
                 recognition=list(recognition), selectors=[dict(projection=projection, start=0, end=len(text))])
    context = SubjectContext("fixture:context", source_subject(coordinate), document,
        canonical_bytes(dict(source=coordinate, selectors=value["selectors"])),
        subject_definition="original-source-view")
    address = DeclaredRecordSource(document, projection, coordinate["section_pointer"], membership,
                                  context, f"fixture:context:{identity}", None, "kind:fixture-native-source")
    return DeclaredNativeFrameSource(canonical_bytes(value).decode(), canonical_bytes(address.pin()).decode())


def context(primary, pieces, *, related=(), retrievals=(), **kwargs):
    return NativeSourceContext(primary, related, pieces, "measurement roles", "bounded-policy-1",
        "roles supplied", retrievals,
        preparation=PreparedNativeSources((primary, *(entry.source for entry in related))), **kwargs)
