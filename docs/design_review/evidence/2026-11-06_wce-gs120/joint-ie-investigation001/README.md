# I01 joint decoding investigation

**Tested2026-11-06; candidate coherence only, semantic benefit not established.**
The actual GLiNER2.5 baseline now exposes invalid combinations as well as missing content:
149 retained definition windows contain2,143 term proposals,117 content proposals and22 proposed
attachments;16 windows contain an attachment. Rejected combinations remain in raw reports.
This settles the entry condition for the planned I01 investigation; it does not establish correct roles.

`probe.py` selects the first three original windows with returned relations, without consulting
reference labels, and invokes the installed gliner2==2.1.0 `JointIE` facade over the same pinned
`fastino/gliner2.5-base-v1` boundary model. Inputs and raw independent outputs are retained in
`inputs.json`; `result.json` retains the exact schema, candidate/beam limits, effective model and
all joint outputs. Every selected entity quote was checked against consumed text. This is a
bounded diagnostic on exposed source, not an independently representative or calibrated trial.

Passed command:

```
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/joint-ie-investigation001/probe.py
```

The three feasible results retain18/24/25 entities and7/10/0 relations. Typed graph coherence
succeeds, but it does not repair this schema's semantic role problem: outputs include
`binomial distribution -> Section 5.2` and `p -> normal density function` under the declared
“term is defined or explained by” relation. Such an edge is not independently justified as a
definition attachment by graph consistency. No semantic capture gain or complete-record benefit
is claimed. Other schema/candidate settings were not tested.

**Disposition:** do not activate this JointIE configuration as a definition producer. Preserve
current source/model/named outputs and the capability as a focused future challenger after the
role/content selection question is improved. JointIE's graph machinery can add value where the
candidate meanings are appropriate; this probe does not establish that prerequisite here.

Primary API grounding: installed `gliner2/joint_ie/{engine,schema,result}.py`; upstream
[tutorial](https://github.com/fastino-ai/gliner2/blob/main/tutorial/15-joint_ie.md).
The retained case/schema/model bytes govern this observed result, rather than current-master examples.
