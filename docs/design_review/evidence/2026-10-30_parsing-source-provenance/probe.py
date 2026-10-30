"""Bounded html5lib 1.1 source-location seams, not a production adapter.

The copied control flow is confined to HTMLParser._parse and HTMLTokenizer.__iter__.
All tokenization states and all HTML5 tree-construction phases remain upstream.
"""

from collections import deque
from copy import deepcopy
import codecs
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from html5lib import HTMLParser, _tokenizer, treebuilders
from html5lib.constants import EOF, _ReparseException, tokenTypes
from lxml import etree


class CursorStream:
    """Observe native normalized-codepoint consumption, including reconsume."""

    def __init__(self, native):
        self.native = native
        self.cursor = 0
        self.events = []
        self.owners = {}
        self.active_state = None

    def __getattr__(self, name):
        return getattr(self.native, name)

    def char(self):
        start = self.cursor
        value = self.native.char()
        if value is not EOF:
            self.cursor += len(value)
            for position in range(start, self.cursor):
                self.owners[position] = self.active_state
        self.events.append(("char", start, self.cursor, value))
        return value

    def charsUntil(self, characters, opposite=False):
        start = self.cursor
        value = self.native.charsUntil(characters, opposite)
        self.cursor += len(value)
        for position in range(start, self.cursor):
            self.owners[position] = self.active_state
        self.events.append(("charsUntil", start, self.cursor, value))
        return value

    def unget(self, value):
        self.native.unget(value)
        start = self.cursor
        if value is not EOF:
            self.cursor -= len(value)
            for position in range(self.cursor, start):
                self.owners.pop(position, None)
        self.events.append(("unget", start, self.cursor, value))
        assert self.cursor >= 0


class TrackedTokenizer(_tokenizer.HTMLTokenizer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = CursorStream(self.stream)
        self.pass_number = 0
        self.tokens = []
        self.state_events = []
        self.pre_emit_attributes = []

    def emitCurrentToken(self):
        token = self.currentToken
        if token["type"] == tokenTypes["StartTag"]:
            self.pre_emit_attributes.append(
                {"pass": self.pass_number, "name": token["name"],
                 "attributes": deepcopy(token["data"])}
            )
        super().emitCurrentToken()

    def __iter__(self):
        self.tokenQueue = deque([])
        start = self.stream.cursor
        while True:
            state = self.state.__name__
            before = self.stream.cursor
            self.stream.active_state = state
            more = self.state()
            after = self.stream.cursor
            self.state_events.append(
                {"pass": self.pass_number, "state": state, "start": before, "end": after}
            )
            while self.stream.errors:
                yield {"type": tokenTypes["ParseError"], "data": self.stream.errors.pop(0)}
            queued = [token for token in self.tokenQueue
                      if token["type"] != tokenTypes["ParseError"]]
            while self.tokenQueue:
                token = self.tokenQueue.popleft()
                if token["type"] != tokenTypes["ParseError"]:
                    number = len(self.tokens)
                    token["_probe_id"] = number
                    record = deepcopy(token)
                    record.update({"pass": self.pass_number, "start": start, "end": after,
                                   "shared_state_output": len(queued) > 1})
                    self.tokens.append(record)
                    self.parser.tree.active_token = number
                    self.parser.tree.active_sources = [number]
                    yield token
                else:
                    yield token
            if queued:
                start = after
            if not more:
                break


NativeBuilder = treebuilders.getTreeBuilder("lxml")


class TrackedBuilder(NativeBuilder):
    def __init__(self, *args, **kwargs):
        self.events = []
        self.active_token = None
        self.active_sources = []
        self.sequence = 0
        super().__init__(*args, **kwargs)
        native_element = self.elementClass
        owner = self

        class Element(native_element):
            def __init__(self, *element_args, **element_kwargs):
                super().__init__(*element_args, **element_kwargs)
                self.probe_id = owner.sequence
                owner.sequence += 1

            def cloneNode(self):
                cloned = super().cloneNode()
                owner.events.append({"kind": "clone", "source": self.probe_id,
                                     "target": cloned.probe_id, "name": self.name,
                                     "active_token": owner.active_token})
                return cloned

            def appendChild(self, node):
                owner.events.append({"kind": "append", "parent": self.probe_id,
                                     "child": getattr(node, "probe_id", None),
                                     "name": getattr(node, "name", None), "active_token": owner.active_token})
                return super().appendChild(node)

            def insertBefore(self, node, refNode):
                owner.events.append({"kind": "insert_before", "parent": self.probe_id,
                                     "child": getattr(node, "probe_id", None),
                                     "before": getattr(refNode, "probe_id", None),
                                     "active_token": owner.active_token})
                return super().insertBefore(node, refNode)

            def removeChild(self, node):
                owner.events.append({"kind": "remove", "parent": self.probe_id,
                                     "child": getattr(node, "probe_id", None),
                                     "active_token": owner.active_token})
                return super().removeChild(node)

            def insertText(self, data, insertBefore=None):
                owner.events.append({"kind": "text", "parent": self.probe_id,
                                     "name": self.name, "data": str(data),
                                     "before": getattr(insertBefore, "probe_id", None),
                                     "active_token": owner.active_token,
                                     "source_tokens": list(owner.active_sources)})
                return super().insertText(data, insertBefore)

            def reparentChildren(self, newParent):
                owner.events.append({"kind": "reparent", "source": self.probe_id,
                                     "target": newParent.probe_id,
                                     "active_token": owner.active_token})
                return super().reparentChildren(newParent)

        self.elementClass = Element

    def insertElementNormal(self, token):
        result = super().insertElementNormal(token)
        self.events.append({"kind": "element", "node": result.probe_id,
                            "name": token["name"], "source_token": token.get("_probe_id"),
                            "active_token": self.active_token})
        return result

    def createElement(self, token):
        result = super().createElement(token)
        self.events.append({"kind": "create", "node": result.probe_id,
                            "name": token["name"], "source_token": token.get("_probe_id"),
                            "active_token": self.active_token})
        return result


class TrackedParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        native_phase = type(self.phases["inTableText"])

        class TableText(native_phase):
            def flushCharacters(phase):
                before = phase.tree.active_sources
                phase.tree.active_sources = [token["_probe_id"]
                                             for token in phase.characterTokens]
                try:
                    return super().flushCharacters()
                finally:
                    phase.tree.active_sources = before

        self.phases["inTableText"] = TableText(self, self.tree)

    def _parse(self, stream, innerHTML=False, container="div", scripting=False, **kwargs):
        self.innerHTMLMode = innerHTML
        self.container = container
        self.scripting = scripting
        self.tokenizer = TrackedTokenizer(stream, parser=self, **kwargs)
        self.reset()
        self.pass_encodings = [self.tokenizer.stream.charEncoding[0].name]
        try:
            self.mainLoop()
        except _ReparseException:
            self.tokenizer.pass_number += 1
            self.tokenizer.stream.cursor = 0
            self.tokenizer.stream.owners = {}
            self.pass_encodings.append(self.tokenizer.stream.charEncoding[0].name)
            self.tree.events.append({"kind": "encoding_restart"})
            self.reset()
            self.mainLoop()



def decoder_contributions(raw, encoding):
    """Finite independent decoder adapter candidate, with grouped contributions.

    A byte-at-a-time diagnostic deliberately favors demonstrable custody over
    speed. A production adapter should group native decoder consumption, not
    persist or dispatch work per byte.
    """
    decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
    byte_start = 0
    decoded_start = 0
    pieces = []
    if encoding == "utf-8" and raw.startswith(b"\xef\xbb\xbf"):
        pieces.append({"kind": "bom", "bytes": [0, 3], "decoded": [0, 0], "text": ""})
        byte_start = 3
    for byte_end in range(byte_start + 1, len(raw) + 1):
        text = decoder.decode(raw[byte_end - 1:byte_end], final=False)
        if text:
            pieces.append({"kind": "decoder_contribution", "bytes": [byte_start, byte_end],
                           "decoded": [decoded_start, decoded_start + len(text)], "text": text})
            decoded_start += len(text)
            byte_start = byte_end
    text = decoder.decode(b"", final=True)
    if text:
        pieces.append({"kind": "decoder_contribution", "bytes": [byte_start, len(raw)],
                       "decoded": [decoded_start, decoded_start + len(text)], "text": text})
        byte_start = len(raw)
    assert byte_start == len(raw)
    assert all(left["bytes"][1] == right["bytes"][0]
               for left, right in zip(pieces, pieces[1:]))
    return pieces


def lexical_partition(normalized, tokenizer, final_tokens):
    """Classify observed state consumption; no alternate tokenization algorithm.

    Last consumption wins after unget, and completed token envelopes supply
    coarse comment/doctype/text categories. Attribute boundaries are selected
    by the upstream state and consumed delimiter. This table is intentionally
    qualified to the probe cases, not a complete production vocabulary.
    """
    assert set(tokenizer.stream.owners) == set(range(len(normalized)))
    categories = ["unknown"] * len(normalized)
    for token in final_tokens:
        token_type = token["type"]
        start, end = token["start"], token["end"]
        if token_type in (tokenTypes["Comment"], tokenTypes["Doctype"]):
            category = "comment" if token_type == tokenTypes["Comment"] else "doctype"
        elif token_type in (tokenTypes["Characters"], tokenTypes["SpaceCharacters"]):
            category = "character_reference" if normalized[start:end].startswith("&") else "text"
        elif token_type in (tokenTypes["StartTag"], tokenTypes["EndTag"]):
            category = "tag"
        else:
            continue
        categories[start:end] = [category] * (end - start)
    for position, state in tokenizer.stream.owners.items():
        if categories[position] != "tag":
            continue
        char = normalized[position]
        if state in ("attributeNameState", "beforeAttributeNameState", "afterAttributeNameState"):
            categories[position] = ("attribute_separator" if char in " \t\n\f" else
                                    "attribute_equals" if char == "=" else
                                    "tag_delimiter" if char in "/>" else "attribute_name")
        elif state == "beforeAttributeValueState":
            categories[position] = ("attribute_separator" if char in " \t\n\f" else
                                    "attribute_quote" if char in "\"'" else
                                    "tag_delimiter" if char == ">" else "attribute_value")
        elif state in ("attributeValueDoubleQuotedState", "attributeValueSingleQuotedState"):
            quote = "\"" if state == "attributeValueDoubleQuotedState" else "'"
            categories[position] = "attribute_quote" if char == quote else "attribute_value"
        elif state == "attributeValueUnQuotedState":
            categories[position] = ("attribute_separator" if char in " \t\n\f" else
                                    "tag_delimiter" if char == ">" else "attribute_value")
        elif state == "afterAttributeValueState":
            categories[position] = ("attribute_separator" if char in " \t\n\f" else "tag_delimiter")
        elif state == "tagNameState":
            categories[position] = ("attribute_separator" if char in " \t\n\f" else
                                    "tag_delimiter" if char in "/>" else "tag_name")
        elif state in ("dataState", "tagOpenState", "closeTagOpenState", "selfClosingStartTagState"):
            categories[position] = "tag_delimiter" if char in "</>" else "tag_name"
    partition = []
    for position, category in enumerate(categories):
        if partition and partition[-1]["category"] == category:
            partition[-1]["end"] = position + 1
        else:
            partition.append({"category": category, "start": position, "end": position + 1})
    for extent in partition:
        extent["source_slice"] = normalized[extent["start"]:extent["end"]]
    assert "".join(extent["source_slice"] for extent in partition) == normalized
    return partition


def native_shape(raw):
    parser = HTMLParser(tree=NativeBuilder, namespaceHTMLElements=False)
    root = parser.parse(raw, useChardet=False)
    return etree.tostring(root, encoding="unicode"), parser.errors


def run_case(name, raw):
    parser = TrackedParser(tree=TrackedBuilder, namespaceHTMLElements=False)
    root = parser.parse(raw, useChardet=False)
    serialized = etree.tostring(root, encoding="unicode")
    expected_tree, expected_errors = native_shape(raw)
    assert serialized == expected_tree, name
    assert parser.errors == expected_errors, name
    tokenizer = parser.tokenizer
    final_pass = tokenizer.pass_number
    final_tokens = [token for token in tokenizer.tokens if token["pass"] == final_pass]
    encoding = tokenizer.stream.charEncoding[0].name
    # This retained-buffer reconstruction verifies cursor coordinates only. It is
    # deliberately NOT claimed to be an original-byte <-> decoded extent map.
    if encoding == "utf-8" and raw.startswith(b"\xef\xbb\xbf"):
        decoded = raw.decode("utf-8-sig", errors="replace")
    else:
        decoded = raw.decode(encoding, errors="replace")
    normalized = decoded.replace("\r\n", "\n").replace("\r", "\n")
    assert tokenizer.stream.cursor == len(normalized), (name, tokenizer.stream.cursor, len(normalized))
    contributions = decoder_contributions(raw, encoding)
    assert "".join(piece["text"] for piece in contributions) == decoded
    partition = lexical_partition(normalized, tokenizer, final_tokens)
    for token in final_tokens:
        token["source_slice"] = normalized[token["start"]:token["end"]]
    # Token-envelope checks are independent literals, not serializer recovery.
    if name == "lexical":
        expected = [
            ("StartTag", 0, 24, '<P A="x" a=\'y\' empty="">'),
            ("Characters", 24, 26, "α\n"),
            ("Characters", 26, 31, "&amp;"),
            ("Characters", 31, 46, "&NotEqualTilde;"),
            ("EndTag", 46, 50, "</P>"),
            ("Comment", 50, 58, "<!--x-->"),
        ]
        actual = [(next(key for key, value in tokenTypes.items() if value == token["type"]),
                   token["start"], token["end"], token["source_slice"]) for token in final_tokens]
        assert actual == expected, actual
        expected_attributes = [
            ("attribute_name", 3, 4, "A"),
            ("attribute_equals", 4, 5, "="),
            ("attribute_quote", 5, 6, '\"'),
            ("attribute_value", 6, 7, "x"),
            ("attribute_quote", 7, 8, '\"'),
            ("attribute_name", 9, 10, "a"),
            ("attribute_equals", 10, 11, "="),
            ("attribute_quote", 11, 12, "'"),
            ("attribute_value", 12, 13, "y"),
            ("attribute_quote", 13, 14, "'"),
            ("attribute_name", 15, 20, "empty"),
            ("attribute_equals", 20, 21, "="),
            ("attribute_quote", 21, 23, '\"\"'),
        ]
        actual_attributes = [(extent["category"], extent["start"], extent["end"],
                              extent["source_slice"]) for extent in partition
                             if extent["category"].startswith("attribute_")
                             and extent["category"] != "attribute_separator"]
        assert actual_attributes == expected_attributes, actual_attributes
        pre = tokenizer.pre_emit_attributes[0]["attributes"]
        assert pre == [["a", "x"], ["a", "y"], ["empty", ""]], pre
        assert final_tokens[0]["data"] == {"a": "x", "empty": ""}
        assert final_tokens[3]["data"] == "≂̸"
    if name == "foster":
        inserted = [event for event in parser.tree.events
                    if event["kind"] == "text" and event["data"] == "a&b"]
        assert len(inserted) == 1, inserted
        text_token_ids = [token["_probe_id"] for token in final_tokens
                          if token.get("data") in ("a", "&", "b")]
        assert len(text_token_ids) == 3
        # A joining phase delays the insertion until a later <tr> token.
        assert inserted[0]["active_token"] not in text_token_ids, inserted
        assert inserted[0]["source_tokens"] == text_token_ids, inserted
        assert any(event["kind"] == "element" and event["name"] == "tbody"
                   and event["source_token"] is None for event in parser.tree.events)
    if name == "adoption":
        assert any(event["kind"] == "clone" for event in parser.tree.events)
    if name == "restart":
        assert parser.pass_encodings == ["windows-1252", "utf-8"], parser.pass_encodings
    summary = {
        "name": name, "input_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw), "decoded_length": len(decoded),
        "normalized_length": len(normalized), "encodings_by_pass": parser.pass_encodings,
        "native_tree_and_errors_equal": True, "final_tree": serialized,
        "tokens": final_tokens, "pre_emit_attributes": tokenizer.pre_emit_attributes,
        "tree_events": parser.tree.events,
        "lexical_partition": partition,
        "decoder_contributions": contributions if name in ("bom", "replacement", "windows1252") else "[bounded groups omitted]",
    }
    if name == "restart":
        summary["final_tree"] = "[large deterministic prefix omitted from report]"
        for token in summary["tokens"]:
            if len(str(token.get("data", ""))) > 100:
                token["data"] = "[1025-character deterministic prefix omitted]"
                token["source_slice"] = "[1025-character deterministic prefix omitted]"
        summary["tree_events"] = [event for event in summary["tree_events"]
                                  if event["kind"] != "text"]
    if name == "lexical":
        summary["state_events"] = tokenizer.state_events
    return summary


def main():
    assert version("html5lib") == "1.1"
    cases = [
        ("lexical", b"\xef\xbb\xbf" + '<P A="x" a=\'y\' empty="">α\r\n&amp;&NotEqualTilde;</P><!--x-->'.encode()),
        ("foster", b"<table>a&amp;b<tr><td>x</table>"),
        ("adoption", b"<p><b>one<i>two</b>three</i>four"),
        ("raw_foreign", b"<!doctype html><script>if(a<b){x='&amp;'}</script><svg><![CDATA[a<b&c]]></svg>"),
        ("bom", b"\xef\xbb\xbf<p>\xc3\xa9\r\nx"),
        ("replacement", b"<meta charset=utf-8><p>a\xffb\xe2A"),
        ("windows1252", b"<meta charset=windows-1252><p>\x80\r\nx"),
        ("restart", b"<p>" + b"a" * 1025 + b"</p><meta charset=utf-8><p>\xc3\xa9"),
        ("malformed", b"<p a='x' a=y><!bogus>text<unclosed"),
    ]
    result = {
        "date": "2026-10-30", "html5lib": version("html5lib"), "lxml": version("lxml"),
        "claim": "bounded normalized token envelopes and observable native tree mutations",
        "not_established": ["all-state lexical categorization and malformed-attribute boundaries",
                            "general charset and decoder equivalence beyond selected encodings",
                            "complete text-slot lineage through buffering and reparenting",
                            "canonical projection mapping", "whole-corpus qualification"],
        "cases": [run_case(name, raw) for name, raw in cases],
    }
    output = Path(__file__).with_name("result.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"outcome": "passed", "cases": len(cases), "result": str(output),
                      "scope": result["claim"]}))


if __name__ == "__main__":
    main()
