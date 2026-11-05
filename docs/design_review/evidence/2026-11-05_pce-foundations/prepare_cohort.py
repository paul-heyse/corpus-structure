"""Freeze a source-only development cohort; never consult predictions or labels."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parent

def rank(value):
    return sha256(("pce-source-first-1:"+value).encode()).hexdigest()

def main():
    cases=[]; inputs=[]
    for unit in (1,2):
        path=ROOT/"raw"/f"source-only-unit-{unit}-002.json"
        data=json.loads(path.read_bytes())
        inputs.append(dict(path=path.name,sha256=sha256(path.read_bytes()).hexdigest()))
        pin=data["source_frame"]["evaluation_frame"]["pin"]
        items=data["native_contexts"][0]["native_items"]
        texts=sorted((key for key,val in items.items() if key.startswith("#/texts/") and val.get("text")),key=rank)[:4]
        for key in texts:
            cases.append(dict(case_id=f"unit{unit}:{key}",unit=unit,pin=pin,native_pointer=key,kind="text",source=items[key],questions=["located terms and contextual roles", "explicit definition or alias cue and attachment"],scope="this complete text item only; linked source context is supporting evidence"))
        tables=sorted((key for key in items if key.startswith("#/tables/")),key=rank)[:1]
        for key in tables:
            table=items[key]
            cells=table.get("data",{}).get("table_cells",[])
            eligible=[i for i,c in enumerate(cells) if not c.get("column_header") and not c.get("row_header")]
            selected=sorted(eligible,key=lambda i:rank(f"{key}/data/table_cells/{i}"))[:16]
            cases.append(dict(case_id=f"unit{unit}:{key}",unit=unit,pin=pin,native_pointer=key,kind="table",source=table,selected_cells=selected,questions=["cell value", "governing header", "row label", "applicable unit", "applicable note"],scope="selected cells and their governing source context only"))
    result=dict(protocol="pce-source-selection-1",partition="feature_fit",purpose="development refinement",selection="sha256 canonical native pointer ordering; <=4 text items and <=1 table/view; <=16 nonheader cells/table",inputs=inputs,cases=cases,limits="finite purposive development cases; no population accuracy or corpus completeness claim")
    with (ROOT/"raw"/"source-cohort-001.json").open("x") as out:json.dump(result,out,ensure_ascii=False,indent=2)
    print(json.dumps(dict(cases=len(cases),texts=sum(c["kind"]=="text" for c in cases),selected_cells=sum(len(c.get("selected_cells",[])) for c in cases))))
if __name__=="__main__":main()
