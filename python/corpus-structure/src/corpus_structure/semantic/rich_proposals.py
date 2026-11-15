"""Source-scoped rich proposals with separate typed members and retained placement meaning."""
from __future__ import annotations

from .data_operation_json import json_bytes, json_loads
from .data_operation_identity import decode_semantic_value
from .identity import canonical_bytes

FAMILIES=(
    ("entities","entity","DdoRichEntityProposal"),
    ("statements","statement","DdoRichStatementProposal"),
    ("claims","claim","DdoRichClaimProposal"),
    ("identity_exclusions","identity_exclusion","DdoRichIdentityExclusionProposal"),
    ("alternatives","alternative","DdoRichAlternativeProposal"),
    ("unsupported","unsupported","DdoRichUnsupportedProposal"),
)


def located_rich_proposals(prepared,model,packet,located):
    """Project actual located semantic values, without retaining the old batch facade.

    Coverage describes the supplied response, never absence in the original document.
    Equal local IDs in different families remain different proposal occurrences.
    """
    pin=packet["source_pin"]
    context=dict(subject=pin["subject"],subject_definition=pin["subject_definition"],
                 original_source=pin["original_source"],analyzed_scope=decode_semantic_value(json_loads(pin["analyzed_scope_meaning"])))
    contracts={(identity.owner,identity.domain):identity.key for identity in model.identities}
    names={kind.name:kind.semantic_id for kind in model.kinds}
    located_values=located.stored.model_dump(mode="python",exclude_unset=True)
    members=[];coverage=[]
    for family,tag,class_name in FAMILIES:
        values=located_values.get(family,())
        for value in values:
            if tag=="alternative":
                value={**{key:child for key,child in value.items() if key!="members"},"claims":[{"member_id":"claim:"+local} for local in value["members"]]}
            body=prepared.validate_json(class_name,json_bytes(dict(value,proposal_type=tag,standing="private_proposed"))).model_dump(mode="python",exclude_unset=True)
            members.append(dict(member_id=tag+":"+value["id"],kind_contract=contracts[names[class_name],"kind"],context=context,body=body))
        issues=tuple(issue for issue in located.issues if issue.path.startswith(family+"["))
        coverage.append(dict(family=family,scope="supplied-authored-response",outcome="partial" if issues else "produced" if values else "empty",count=len(values),
                             **(dict(reason="; ".join(sorted({issue.code for issue in issues}))) if issues else {})))
    from dataclasses import asdict
    from .observations import source_value
    result=dict(version="source-rich-proposals-1",unit_ref=packet["unit_ref"],source_pin=pin,
        standing="private_proposed",members=members,coverage=coverage,
        issues=source_value([asdict(issue) for issue in located.issues]),known_reference_standing=packet["known_reference_standing"])
    return read_rich_proposals(prepared,result)


def read_rich_proposals(prepared,value):
    """Read the current private member collection; batch-shaped predecessors are refused."""
    checked=prepared.validate_json("DdoLocatedExternalExtraction",json_bytes(value)).model_dump(mode="python",exclude_unset=True)
    if checked["standing"]!="private_proposed":
        raise ValueError("rich source proposals do not grant accepted standing")
    ids=set()
    for member in checked["members"]:
        if member["member_id"] in ids: raise ValueError("rich proposal repeats member identity")
        ids.add(member["member_id"])
        body=member["body"]
        if member["member_id"]!=body["proposal_type"]+":"+body["id"]:
            raise ValueError("rich member address differs from its source-local proposal")
    for member in checked["members"]:
        if member["body"]["proposal_type"]=="alternative" and any(ref["member_id"] not in ids or not ref["member_id"].startswith("claim:") for ref in member["body"]["claims"]):
            raise ValueError("rich alternative names an unavailable claim proposal")
    expected={family:tag for family,tag,_ in FAMILIES}
    coverage={row["family"]:row for row in checked["coverage"]}
    if len(coverage)!=len(checked["coverage"]) or set(coverage)!=set(expected):
        raise ValueError("rich proposal coverage must name every supplied response family once")
    for family,tag in expected.items():
        count=sum(member["body"]["proposal_type"]==tag for member in checked["members"])
        report=coverage[family]
        if report["count"]!=count or (report["outcome"]=="empty" and count) or (report["outcome"]=="produced" and not count):
            raise ValueError("rich coverage cardinality differs from its actual proposal members")
        if report["outcome"]=="partial" and not report.get("reason"):
            raise ValueError("partial rich proposal coverage requires its actual placement reason")
    return checked
