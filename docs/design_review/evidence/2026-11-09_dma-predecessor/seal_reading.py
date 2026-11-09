"""Serialize explicit author decisions from a protected source packet using released identities."""

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)


def anchor_for(pin, projection, location):
    pointer, *parts = location
    if not parts:
        anchor = dict(pin=pin, space="native", pointer=pointer, precision="item")
    else:
        literal, *occurrence = parts
        if not literal:
            raise ValueError("an exact role requires nonempty source text")
        matches = []
        for piece in projection["pieces"]:
            if piece.get("kind") != "native_text" or piece.get("item_ref") != pointer:
                continue
            snippet = projection["text"][piece["start"] : piece["end"]]
            offset = snippet.find(literal)
            while offset >= 0:
                matches.append(piece["start"] + offset)
                offset = snippet.find(literal, offset + 1)
        if not matches or (len(matches) > 1 and not occurrence):
            raise ValueError(
                f"exact role location is missing or ambiguous: {location!r}"
            )
        start = matches[occurrence[0] if occurrence else 0]
        anchor = dict(
            pin=pin,
            space="selected_projection",
            pointer=pointer,
            precision="exact",
            start=start,
            end=start + len(literal),
            source_piece=literal,
        )
    return dict(anchor, anchor_id=anchor_identity(anchor))


def seal_record(source, decision):
    frame = source["source_frame"]["evaluation_frame"]
    pin = frame["pin"]
    [view] = source["source_frame"]["source_views"]
    projection = view["projection"]
    anchors, evidence, fields = {}, [], []
    primary_roles = set(decision["occurrence_roles"])
    primary_anchors = []
    for role, role_decision in decision["fields"].items():
        role_anchors = [
            anchor_for(pin, projection, loc) for loc in role_decision["locations"]
        ]
        anchor_ids = [anchor["anchor_id"] for anchor in role_anchors]
        anchors.update(zip(anchor_ids, role_anchors, strict=True))
        if role in primary_roles:
            primary_anchors.extend(anchor_ids)
        kind, state = role_decision["kind"], role_decision["state"]
        field = dict(
            role=role,
            kind=kind,
            state=state,
            meaning_changing=role_decision["meaning_changing"],
            evidence_status="available",
        )
        if state != "present":
            usage = "context"
            field["reason"] = role_decision["reason"]
        elif kind == "literal":
            usage = "literal"
            texts = [anchor["source_piece"] for anchor in role_anchors]
            if len(texts) == 1:
                field.update(value=dict(kind="text", text=texts[0]), original=texts[0])
            else:
                field.update(
                    value=dict(kind="text_sequence", items=texts), original_pieces=texts
                )
        elif kind == "native":
            usage = "native"
            [anchor] = role_anchors
            field["value"] = dict(kind="native_location", pointer=anchor["pointer"])
        elif kind == "classified":
            usage = "classification_cue"
            field["value"] = role_decision["value"]
            field["policy"] = frame["guideline_version"]
        else:
            raise ValueError(f"author decision uses unsupported field kind: {kind!r}")
        entry = dict(role=role, ordering="ordered", usage=usage, anchors=anchor_ids)
        entry["set_id"] = evidence_set_identity(entry)
        evidence.append(entry)
        field["evidence_sets"] = [entry["set_id"]]
        fields.append(field)
    record = dict(
        contract=decision["contract"],
        family=decision["family"],
        standing="accepted",
        pin=pin,
        occurrence_recipe="source-anchor-membership-1",
        occurrence_anchors=list(dict.fromkeys(primary_anchors)),
        fields=fields,
        anchors=list(anchors.values()),
        evidence_sets=evidence,
        policy_version=frame["reference_policy_version"],
    )
    record["record_id"] = record_identity(source["release_id"], record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("packet", type=Path)
    cli.add_argument("reading", type=Path)
    cli.add_argument("authored", type=Path)
    cli.add_argument("--frame-output", type=Path)
    args = cli.parse_args()
    packet = json.loads(args.packet.read_bytes())
    source = packet.get("source", packet)
    frame = source["source_frame"]["evaluation_frame"]
    decisions = json.loads(args.reading.read_bytes())
    if source["unit_id"] != decisions["unit_id"]:
        raise ValueError("author decisions differ from the protected source unit")
    records = [
        seal_record(source, decision) for decision in decisions.get("records", ())
    ]
    authored = dict(
        protocol="source-record-reference-1",
        release_id=source["release_id"],
        unit_ref=source["unit_ref"],
        guideline=source["guideline"],
        reference_policy_version=frame["reference_policy_version"],
        prediction_policy_version=frame["prediction_policy_version"],
        reason=decisions["reason"],
        records=records,
    )
    if "adjudication_passes" in packet:
        authors = {
            entry["pass_id"]: json.loads(entry["authored"])
            for entry in packet["authors"]
        }
        for origin in decisions.get("adopt", ()):
            authored["records"].append(
                authors[origin["pass_id"]]["records"][origin["record_index"]]
            )
        authored["adjudication_passes"] = packet["adjudication_passes"]
    with args.authored.open("x", encoding="utf-8") as stream:
        json.dump(authored, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if args.frame_output is not None:
        with args.frame_output.open("x", encoding="utf-8") as stream:
            json.dump(source["source_frame"], stream, ensure_ascii=False, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
