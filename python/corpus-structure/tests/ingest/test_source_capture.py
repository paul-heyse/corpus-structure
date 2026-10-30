"""Independent source boundaries and native HTML5 compatibility for source capture."""

from __future__ import annotations

import pytest
from html5lib import HTMLParser, treebuilders
from lxml import etree

from corpus_structure.ingest.html import _parse_with_capture, build_rendition
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.ingest.source_capture import CaptureParser, SourceCapture

SOURCE = "siegrist_random/random/test/Page.html"


def _rows(product, representation):
    return sorted((r for r in product["components"] if r["representation_id"] == representation), key=lambda r:r["ordinal"])


def _partition(product, representation, content):
    rows=_rows(product, representation)
    position=0
    for row in rows:
        assert row["start_offset"] == position
        assert row["end_offset"] > position
        position=row["end_offset"]
    assert position == len(content)
    assert b"".join(content[r["start_offset"]:r["end_offset"]] for r in rows)==content if isinstance(content,bytes) else "".join(content[r["start_offset"]:r["end_offset"]] for r in rows)==content


@pytest.mark.parametrize("raw", [
    b'<P A="x > = y" a=\'z\' empty="">x&amp;y</P><!--c-->',
    b'<!doctype html><table>a&amp;b<tr><td>x</table>',
    b'<p><b>one<i>two</b>three</i>',
    b'<pre>\ntext</pre><textarea>\ntext&amp;</textarea>',
    b'<script>if(x<2){x++}</script><svg><![CDATA[a<b]]></svg>',
    b'\xef\xbb\xbf<p>\xc3\xa9\r\nx</p>',
    b'<meta charset="utf-8"><p>\xe2A</p>',
    b' '*1025+b'<meta charset="utf-8"><p>\xc3\xa9</p>',
    b'<p a="unterminated',
    b'',
])
def test_native_tree_errors_and_complete_source_partitions(raw):
    root, detail, capture=_parse_with_capture(raw)
    native=HTMLParser(tree=treebuilders.getTreeBuilder("lxml"),namespaceHTMLElements=False)
    expected=native.parse(raw,useChardet=False).getroot()
    assert etree.tostring(root)==etree.tostring(expected)
    assert [(e.line,e.column,e.code) for e in detail.parser_errors]==[(pos[0],pos[1],code) for pos,code,_ in native.errors]
    values=capture.finish("",()).values()
    _partition(values,"raw",raw)
    _partition(values,"decoded",capture.source)
    assert values["provenance_state"]=="complete"
    if b' '*1025 in raw and b'charset="utf-8"' in raw:
        assert capture.parser.encodings==["windows-1252","utf-8"]
    assert all(n.get("representation_id")=="decoded" for n in values["nodes"] if n["origin"]=="literal")
    assert all("start_offset" not in n for n in values["nodes"] if n["origin"]=="synthetic")


def test_duplicate_attribute_quoting_and_values_have_independent_exact_boundaries():
    raw=b'<P A="x > = y" a=\'z\' empty="">'
    _,_,capture=_parse_with_capture(raw)
    rows=capture.finish("",()).values()["components"]
    decoded=[r for r in rows if r["representation_id"]=="decoded"]
    attrs=[(r["start_offset"],r["end_offset"],capture.source[r["start_offset"]:r["end_offset"]]) for r in decoded if r["category"]=="attribute_name"]
    assert attrs==[(3,4,"A"),(15,16,"a"),(21,26,"empty")]
    assert [(r["start_offset"],r["end_offset"],capture.source[r["start_offset"]:r["end_offset"]]) for r in decoded if r["category"]=="attribute_value"]==[(6,13,"x > = y"),(18,19,"z")]
    assert capture.parser.source_tokenizer.attributes==[(("a","x > = y"),("a","z"),("empty",""))]
    attributes = [n for n in capture.finish("", ()).values()["nodes"] if n["kind"] == "attribute"]
    assert [(n["name"], n["value"], n["ordinal"], n["attribute_outcome"]) for n in attributes] == [("a", "x > = y", 0, "retained"), ("a", "z", 1, "discarded_duplicate"), ("empty", "", 2, "retained")]
    assert [capture.source[n["start_offset"]:n["end_offset"]] for n in attributes] == ['A="x > = y"', "a='z'", 'empty=""']
    assert [(n['value_start_offset'], n['value_end_offset']) for n in attributes] == [(6, 13), (18, 19), (28, 28)]


def test_foster_text_slot_retains_ordered_actual_token_origins():
    root,_,capture=_parse_with_capture(b'<table>a&amp;b<tr><td>x</table>')
    body=root.find("body")
    assert body.text=="a&b"
    origins=capture.slot(body,"text")
    assert [(s.start,s.end) for c in origins for s in c.sources]==[(7,8),(8,13),(13,14)]
    assert any(n["origin"]=="synthetic" for n in capture.parser.tree.nodes.values())


def test_replacement_decoder_keeps_indivisible_original_group():
    raw=b'<meta charset="utf-8"><p>\xe2A</p>'
    _,_,capture=_parse_with_capture(raw)
    assert capture.decoded.endswith("<p>\ufffdA</p>")
    assert any(raw[a:b]==b"\xe2A" and capture.decoded[c:d]=="\ufffdA" for a,b,c,d in capture.decoder_groups)
    values=capture.finish("",()).values()
    assert any(raw[r["start_offset"]:r["end_offset"]]==b"\xe2A" and r["category"]=="malformed" for r in _rows(values,"raw"))


def test_canonical_projection_separators_markers_exclusion_and_nfc(profile):
    raw=b'<meta charset="utf-8"><body><script>ignored</script><p>e<b></b>\xcc\x81 <q>x</q></p><p>tail</p></body>'
    built=build_rendition(raw,profile,SentenceConfig(),source_uri=SOURCE)
    assert built.content.canonical_text=="\u00e9 \u201cx\u201d\n\ntail"
    assert built.parsing_product is not None
    values=built.parsing_product.values()
    _partition(values,"raw",raw)
    _partition(values,"canonical",built.content.canonical_text)
    canonical=_rows(values,"canonical")
    assert any(built.content.canonical_text[r["start_offset"]:r["end_offset"]]=="\n\n" and r["category"]=="canonical_separator" for r in canonical)
    synthetic=[m["mapping_id"] for m in values["mappings"] if m["fidelity"]=="synthetic"]
    assert len(synthetic)>=3
    assert all(not any(e["side"]=="source" and e["mapping_id"]==key for e in values["mapping_endpoints"]) for key in synthetic)
    assert any(e["representation_id"]=="raw" and e["side"]=="source" for e in values["mapping_endpoints"])


def test_excluding_element_does_not_exclude_its_kept_tail(profile):
    raw=b'<body><p>before<script>ignored</script>kept</p></body>'
    built=build_rendition(raw,profile,SentenceConfig(),source_uri=SOURCE)
    assert built.content.canonical_text=="beforekept"
    assert built.parsing_product is not None
    values=built.parsing_product.values()
    decoded=next(r["text_content"] for r in values["representations"] if r["representation_id"]=="decoded")
    excluded={m["mapping_id"] for m in values["mappings"] if m["fidelity"]=="excluded"}
    slices=[decoded[e["start_offset"]:e["end_offset"]] for e in values["mapping_endpoints"] if e["mapping_id"] in excluded and e["representation_id"]=="decoded"]
    assert "ignored" in slices
    assert all("kept" not in item for item in slices)


def test_same_length_decoder_disagreement_refuses_source_coordinates():
    raw = b"<p>source</p>"
    parser = CaptureParser()
    parser.parse(raw, useChardet=False)
    observed = parser.source_tokenizer.cursor_stream.native_chunks
    observed[0] = observed[0].replace("source", "wrong!")
    with pytest.raises(ValueError, match="coordinate spaces differ"):
        SourceCapture(raw, parser)


def test_comment_occurrences_and_implied_element_names_remain_structural():
    _, _, capture = _parse_with_capture(b"<!--before--><table><tr><td>x<!--inside--></table><!--after-->")
    values = capture.finish("", ()).values()
    comments = [n for n in values["nodes"] if n["kind"] == "comment"]
    assert {n["value"] for n in comments} == {"before", "inside", "after"}
    assert all(n["origin"] == "literal" for n in comments)
    assert any(n.get("name") == "tbody" and n["origin"] == "synthetic" for n in values["nodes"])
    assert any(n["node_id"] == "document" for n in values["nodes"])


def test_trailing_stateful_decoder_bytes_are_retained_without_codepoint_invention():
    raw = b'<meta charset="iso-2022-jp"><p>' + "日本".encode("iso2022_jp") + b"</p>\x1b(B"
    _, _, capture = _parse_with_capture(raw)
    values = capture.finish("", ()).values()
    _partition(values, "raw", raw)
    assert capture.decoder_groups[-1] == (len(raw)-3, len(raw), len(capture.decoded), len(capture.decoded))
    excluded = {m["mapping_id"] for m in values["mappings"] if m["fidelity"] == "excluded"}
    assert any(e["mapping_id"] in excluded and e["representation_id"] == "raw" and e["start_offset"] == len(raw)-3 and e["end_offset"] == len(raw) for e in values["mapping_endpoints"])


def test_unclosed_tag_retains_native_lexical_attribute_boundaries():
    _, _, capture = _parse_with_capture(b'<p a="unterminated')
    rows = capture.finish("", ()).values()["components"]
    actual = [(r["category"], r["start_offset"], r["end_offset"]) for r in rows if r["representation_id"] == "decoded"]
    assert actual == [("tag_open", 0, 1), ("tag_name", 1, 2), ("whitespace", 2, 3), ("attribute_name", 3, 4), ("attribute_delimiter", 4, 6), ("attribute_value", 6, 18)]


def test_final_native_text_slots_have_durable_owners_and_ordered_contributions(profile):
    built = build_rendition(b"<p>a<b>x</b>t</p>", profile, SentenceConfig(), source_uri=SOURCE)
    assert built.parsing_product is not None
    values = built.parsing_product.values()
    slots = {node["node_id"]: node for node in values["nodes"] if node["kind"] == "text"}
    assert {(n["name"], n["value"], n["origin"]) for n in slots.values()} == {("text", "a", "derived"), ("text", "x", "derived"), ("tail", "t", "derived")}
    nodes = {node["node_id"]: node for node in values["nodes"]}
    owners = {}
    for relation in values["relationships"]:
        if relation["kind"] != "text_of":
            continue
        endpoints = sorted((e for e in values["endpoints"] if e["relationship_id"] == relation["relationship_id"]), key=lambda e:e["ordinal"])
        owners[slots[endpoints[0]["node_id"]]["value"]] = nodes[endpoints[1]["node_id"]]["name"]
    assert owners == {"a": "p", "x": "b", "t": "b"}
    assert all("start_offset" not in node for node in slots.values())
    assert sum(r["kind"] == "derived_from" for r in values["relationships"]) >= 3


@pytest.mark.parametrize("raw", [
    b"<p>plain&amp;tail</p>",
    b"<table>a&amp;b<tr><td>x</table>",
    b"<p><b>one<i>two</b>three</i>",
    b"<pre>\ntext</pre><textarea>\ntext&amp;</textarea>",
    b"\xef\xbb\xbf<p>\xc3\xa9\r\nx</p>",
    b'<meta charset="utf-8"><p>\xe2A</p>',
    b" "*1025+b'<meta charset="utf-8"><p>\xc3\xa9</p>',
    b"<p>a\x00b</p>",
])
def test_canonical_origin_universe_is_rooted_for_qualified_native_cases(profile, raw):
    built = build_rendition(raw, profile, SentenceConfig(), source_uri=SOURCE)
    assert built.parsing_product is not None
    values = built.parsing_product.values()
    unknown = [mapping["reason"] for mapping in values["mappings"] if mapping["fidelity"] == "unknown"]
    assert unknown == []
    assert values["provenance_state"] == "complete"
    assert values["provenance_universe"] == "canonical_output"
    assert values["adapter_id"] == "html5lib-source-1"
    if b"\x00" in raw:
        from base64 import b64decode
        decoded = next(row for row in values["representations"] if row["representation_id"] == "decoded")
        assert "text_content" not in decoded
        assert b64decode(decoded["text_content_utf8_base64"]).decode("utf-8") == "<p>a\x00b</p>"
        assert b"\x00" not in built.parsing_product.payload
        assert built.content.canonical_text == "ab"


def test_foreign_attribute_names_use_the_native_qualified_namespace_rules():
    _, _, capture = _parse_with_capture(b'<svg viewBox="0 0 1 1" xlink:href="#x"></svg>')
    values = capture.finish("", ()).values()
    attributes = [node for node in values["nodes"] if node["kind"] == "attribute"]
    assert {node["name"] for node in attributes} == {"viewBox", "{http://www.w3.org/1999/xlink}href"}
    assert [capture.source[node["name_start_offset"]:node["name_end_offset"]] for node in attributes] == ["viewBox", "xlink:href"]
