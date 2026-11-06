"""Serialize manually authored source judgments; verify their neutral-source anchors."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXTRA_READ = {
    211: [(69, f'#/texts/{n}') for n in [65,68,194]],
    221: [(101, '#/texts/65'), (101, '#/texts/66')],
    231: [(89, f'#/texts/{n}') for n in [43,45,46,112]],
    251: [(92, f'#/texts/{n}') for n in [121,150,152,153]],
    261: [(76, f'#/texts/{n}') for n in [79,80]] +
        [(77, f'#/texts/{n}') for n in [90,108,112,115,116,117,118]],
    271: [(100, f'#/texts/{n}') for n in [97,98,99,128,140,155,156,157,164]],
    301: [(75, f'#/texts/{n}') for n in range(203,211)],
}


def packet(first, specs, inspected=None):
    path = ROOT / 'source-packets' / f'grinstead-snell-physical{first}-{first+9}.json'
    raw = path.read_bytes()
    doc = json.loads(raw)
    views = {v['native_view']['id']: v for v in doc['views']}
    cases = []
    regions = {vid: set() for vid in views}
    native_only_read = {vid: [] for vid in views}
    def anchor(vid, ref, cell=None):
        v = views[vid]
        piece = next(p for p in v['native_context']['pieces'] if p.get('item_ref') == ref and p.get('cell_index') == cell)
        item = next(i for i in v['native_context']['items'] if i['self_ref'] == ref)
        text = item['data']['table_cells'][cell]['text'] if cell is not None else item['text']
        a, b = piece['start'], piece['end']
        assert v['passage']['text'][a:b] == text, (vid, ref, cell)
        regions[vid].add((ref, cell))
        pages = sorted({p['page_no'] for p in item.get('prov', [])})
        maps = [m for m in doc['page_map'] if m['excerpt_physical_page'] in pages]
        assert maps, (vid, ref)
        result = {'quote': text, 'source_packet': str(path.relative_to(ROOT)),
            'view_id': vid, 'passage_id': v['passage']['passage_id'],
            'passage': {k: z for k, z in v['passage'].items() if k != 'text'},
            'source': v['source'], 'native_view': v['native_view'],
            'pointer': ref + (f'/data/table_cells/{cell}/text' if cell is not None else '/text'),
            'coordinate_space': 'passage.text Unicode code points, zero-based half-open',
            'start': a, 'end': b, 'native_piece': piece,
            'native_provenance': item.get('prov', []), 'page_map': maps,
            'native_parent': item.get('parent')}
        if cell is not None:
            result['native_cell'] = item['data']['table_cells'][cell]
        return result
    for n, spec in enumerate(specs, 1):
        facet, expected, refs, state, judgment, reason, missing = spec
        evidence = [anchor(*r) for r in refs]
        page = min(m['parent_physical_page'] for e in evidence for m in e['page_map'])
        cases.append({'id': f'B-{first}-{n:03d}', 'facet': facet,
            'expected_roles_relationships': expected, 'evidence': evidence,
            'source_state': state, 'judgment': judgment, 'reason': reason,
            'missing_facets': missing})
    for r in inspected or []:
        anchor(*r)
    for r in EXTRA_READ.get(first, []):
        vid, ref = r
        if any(p.get('item_ref') == ref and p.get('source_field') == 'text' for p in views[vid]['native_context']['pieces']):
            anchor(*r)
        else:
            item = next(i for i in views[vid]['native_context']['items'] if i['self_ref'] == ref)
            native_only_read[vid].append({'item_ref': ref, 'text': item.get('text'),
                'native_provenance': item.get('prov', []), 'projection_state': 'no matching native projection piece; inspected native context only'})
    # These are the exact selection rules used in the author's source-reading
    # calls. They inventory read regions; they do not generate semantic cases.
    for vid, v in views.items():
        by_page = {}
        for item in v['native_context']['items']:
            if item.get('prov'):
                by_page.setdefault(item['prov'][0]['page_no'], []).append(item)
        for items in by_page.values():
            candidates = [i for i in items if i.get('label') in
                (['text'] if first == 191 else ['text', 'list_item'])
                and len(i.get('text', '')) > (170 if first == 191 else 130)]
            selected = candidates[:2]
            selected += [i for i in items if i.get('label') == 'section_header']
            if first != 191:
                selected += [i for i in items if i.get('label') == 'formula'
                    and len(i.get('text', '')) < 350][:1]
            if first in [241, 251, 281, 291, 301]:
                selected += [i for i in items if i.get('label') == 'caption']
            for item in selected:
                if any(p.get('item_ref') == item['self_ref'] and p.get('source_field') == 'text'
                    for p in v['native_context']['pieces']):
                    anchor(vid, item['self_ref'])
                elif not any(x['item_ref'] == item['self_ref'] for x in native_only_read[vid]):
                    native_only_read[vid].append({'item_ref': item['self_ref'], 'text': item.get('text'),
                        'native_provenance': item.get('prov', []), 'projection_state': 'no matching native projection piece; inspected native context only'})
    coverage = []
    for vid, v in views.items():
        regs = []
        for ref, cell in sorted(regions[vid], key=str):
            p = next(p for p in v['native_context']['pieces'] if p.get('item_ref') == ref and p.get('cell_index') == cell)
            regs.append({'item_ref': ref, 'cell_index': cell, 'start': p['start'], 'end': p['end']})
        coverage.append({'view_id': vid, 'inspected_regions': regs,
            'native_context_only_inspected': native_only_read[vid],
            'scope': 'Listed native text/cell pieces were read as source candidates; only cases carry semantic judgments. Other projection pieces uninspected unless covered by an additional inspected range.',
            'visual_regions': 'uninspected: original PDF images, plots, layout and symbols outside quoted native projection'})
    if first == 191:
        v = views[97]
        a, b = len(v['passage']['text'])-9500, len(v['passage']['text'])
        coverage[1]['additional_inspected_ranges'] = [{
            'coordinate_space': 'passage.text Unicode code points, zero-based half-open',
            'start': a, 'end': b,
            'native_piece_intersections': [p for p in v['native_context']['pieces'] if p['end'] > a and p['start'] < b],
            'scope': 'Tail excerpt read directly, including damaged formula suffix, table values and graphic labels. No repaired formula or complete visual judgment follows.'}]
    present = set()
    for v in views.values():
        refs = {p.get('item_ref') for p in v['native_context']['pieces']}
        for i in v['native_context']['items']:
            if i['self_ref'] in refs:
                present.update(p['page_no'] for p in i.get('prov', []))
    represented = {m['parent_physical_page'] for m in doc['page_map'] if m['excerpt_physical_page'] in present}
    page_coverage = []
    for m in doc['page_map']:
        assessed = [c['id'] for c in cases if any(m['parent_physical_page'] == z['parent_physical_page'] for e in c['evidence'] for z in e['page_map'])]
        read_regions = []
        for vid, refs in regions.items():
            for ref, cell in refs:
                item = next(i for i in views[vid]['native_context']['items'] if i['self_ref'] == ref)
                if m['excerpt_physical_page'] in {p['page_no'] for p in item.get('prov', [])}:
                    read_regions.append({'view_id': vid, 'item_ref': ref, 'cell_index': cell})
        page_coverage.append({'parent_physical_page': m['parent_physical_page'],
            'projection_presence': 'present' if m['parent_physical_page'] in represented else 'absent',
            'cases': assessed, 'inspected_native_regions': sorted(read_regions,key=str),
            'inspection': 'selective textual inspection; original visuals uninspected' if read_regions else 'uninspected substantive content; projection presence only'})
    result = {'protocol': 'gs120-source-author-1', 'author': 'B',
        'input_sha256': hashlib.sha256(raw).hexdigest(), 'input_file': str(path.relative_to(ROOT)),
        'source_pdf': doc['source_pdf'], 'source_pdf_sha256': doc['source_pdf_sha256'],
        'parent_pdf_sha256': doc['parent_pdf_sha256'],
        'parent_physical_pages': doc['parent_physical_pages'],
        'inventory_scope': 'Independent selective source inventory, not a census. No producer outputs or other authors consulted.',
        'coverage': {'views': coverage, 'pages': page_coverage}, 'cases': cases,
        'remaining_gaps': ['All unlisted native pieces remain uninspected; listed cases do not exhaust the packet.',
            'Original PDF visual regions, diagrams, graphs, and visual-only equations have not been inspected.',
            'Damaged or fragmented formula projections are not reconstructed from isolated characters; no semantic inference from converter success status.',
            'Unsupported/unstated judgments apply only to the quoted source scope; absence from this selective inventory is not absence from the book.']}
    (OUT / f'packet-{first}-{first+9}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(f'{first}-{first+9}: {len(cases)} manually authored cases, all {sum(len(c["evidence"]) for c in cases)} evidence anchors exact and native-bound')


S = 'stated'
J = 'supported'

packet(191, [
('definition / equal-likelihood and finite support', ['random variable X represents experiment outcomes', 'equally likely outcomes → X uniformly distributed', 'finite sample space S has size n with 0 < n < ∞', 'each ω in S → mass 1/n'], [(97,'#/texts/5')], S,J,'The prose explicitly binds the definition, support condition, and mass.',[]),
('algorithm / binomial simulation prerequisites and approximation domain', ['n independent 0–1 variables with probability p of 1 → sum simulates X', 'method → n random generator calls', 'relatively large n (say at least 30) → normal approximation', 'Y normal with µ=np and σ=√npq; accepted range −1/2 ≤ Y < n+1/2'],[(97,'#/texts/15')],S,J,'Prerequisites and approximation are explicit; terminal rounding expression is outside this quote.',['Complete rounding expression and rejection handling are not assessed.']),
('directed parameter effect / geometric distribution', ['p decreases → larger T more likely', 'T=1 → most probable value', 'Figure 5.1 cases p=.5 and p=.2'],[(97,'#/texts/48')],S,J,'The paragraph states direction and modal value; plot pixels remain uninspected.',[]),
('algorithm / geometric stopping rule and work qualification', ['draw numbers in [0,1) sequentially', 'entry does not exceed p → stop', 'small p → average 1/p steps', 'alternative method → claimed runtime independent of p'],[(97,'#/texts/53')],S,J,'The procedural stopping condition and qualified comparison are stated.',['Alternative inequality and derivation not assessed.']),
('example / queue arrival model and tail event', ['small time unit → 0 or 1 new customers', 'arrival probability p; no arrival q=1−p', 'T is time to next arrival → geometric distribution', 'no arrival for next k units ↔ event T>k'],[(97,'#/texts/62')],S,J,'The example declares assumptions, roles, and event mapping.',[]),
('transformation / negative-binomial generation', ['X → sum of k geometric outcomes with parameter p', 'coin tossing simulation compared with generally faster sum method'],[(97,'#/texts/79')],S,J,'The paragraph explicitly links the distributions and algorithm; no missing displayed sum is guessed.',['Displayed generating expression not assessed.']),
('model qualification / constant rate and interval independence', ['rate λ → average number of occurrences per minute', 'constant λ required within modelled interval', 'five-minute interval → about 5λ occurrences', 'different time periods may use different rates', 'non-overlapping intervals → independent occurrence counts'],[(97,'#/texts/102'),(97,'#/texts/103')],S,J,'Two contiguous source pieces independently state distinct modelling assumptions and units.',[]),
('parameter determination / Bernoulli subdivision', ['interval length t → average λt occurrences', 'n subintervals with occurrence probability p → expected np occurrences', 'equate the two expectations to choose p'],[(97,'#/texts/107')],S,J,'The prose supplies expected-count roles; the display equation itself is outside the evidence.',['Displayed algebra not assessed.']),
('table / paired distribution columns and row j=0', ['table columns Poisson λ=.1 and binomial n=100 p=.001', 'row key j=0', 'each paired probability value .9048', 'cell coordinates preserve header/data distinction', 'probabilities are dimensionless; no physical unit stated'],[(97,'#/tables/0',0),(97,'#/tables/0',1),(97,'#/tables/0',6),(97,'#/tables/0',7),(97,'#/tables/0',8),(97,'#/tables/0',9)],S,J,'Native cell row/column offsets bind the matching first row and column headers.',['Other rows and any table notes are not assessed.']),
('example / spatial count approximation', ['400 bombs and hit probability 1/100 → Bernoulli n=400,p=1/100', 'λ=np=4 → Poisson approximation', 'expected number of squares with j hits → 100·p(j)'],[(97,'#/texts/129'),(97,'#/texts/130')],S,J,'The scenario and parameter roles are explicit. The flattened inline p(j) formula is not reconstructed.',['Exact inline probability expression remains unresolved as projected.']),
('graphic / caption does not establish mark semantics', ['Figure 5.3 identifies flying bomb hits', 'caption alone does not establish coordinates, numerical mark values, or agreement quality'],[(97,'#/texts/138')],'unresolved','unassessed','Only projection caption/graphic-associated text is assessed; original graphic is unread.',['Original graphic, numerical marks, and axis/legend alignment require visual inspection.']),
], inspected=[(96,'#/texts/0')])

packet(201, [
('definition / hypergeometric sampling without replacement', ['N balls, k red and N−k blue', 'choose n balls without replacement', 'X counts sampled red balls', 'h(N,k,n,x) denotes P(X=x)'],[(105,'#/texts/3')],S,J,'The definition binds population, category size, draw count, count variable, and notation.',[]),
('model / marginals fixed and independence assumed', ['row sums t11,t12 and column sums t21,t22 → marginals', 'sij → cell entry; n → data-set size', 'independence model → urn with Democratic and Republican marginals', 'draw t11 balls without replacement → female category'],[(105,'#/texts/16')],S,J,'This is a declared model construction, not an unconditional claim about the observed people.',[]),
('action / tail probability leads to hypothesis rejection in example', ['expected female Democrats 18; observed 24', 'tail cases a=24 through 28 → probability .000395', 'example conclusion → reject independence hypothesis'],[(105,'#/texts/24')],S,J,'The direction, aggregation range, reported probability and decision are stated; no symmetric or universal test rule is inferred.',[]),
('scope qualification / Benford scale invariance explanation', ['many real-life data sets → nonuniform leading digits', 'digit 1 most likely; decreasing distribution', 'Benford fits in many cases', 'scale invariance offered as a possible explanation'],[(106,'#/texts/29')],S,J,'Qualifiers many, appears and possibly must remain attached; this is not a claim about every data set.',[]),
('formula / first-digit Benford mass', ['scope restricted to first digit', 'f(k)=log10(k+1)−log10(k)'],[(106,'#/texts/45'),(106,'#/texts/46')],S,J,'The equation is intact in the projection and prose supplies first-digit scope.',['Digit domain is not in these two pieces.']),
('exercise / removal state machine', ['positive integer n → S={1,…,n}', 'remove a number at random and write it down', 'repeat until S empty', 'X denotes resulting permutation', 'uniformity is posed as a question'],[(107,'#/texts/62')],S,J,'The procedure is stated; the exercise does not state its answer.',[]),
('exercise / mark–recapture observations', ['first sample 100 trout → tag and return', 'one month later sample 100', '10 in second sample have tags'],[(107,'#/texts/77')],S,J,'These are scenario data and actions, not a supplied population estimate.',['Estimator, independence and mixing assumptions not supplied in this paragraph.']),
('scope / change of time units in Poisson count', ['Y Poisson with parameter λt', 'Martian basic time interval t Earth minutes → reinterpretation of rate/count interval'],[(107,'#/texts/88')],S,J,'The statement and hint distinguish time-unit transformation from a changed physical process.',[]),
('exercise / equal landing chances and empty-block event', ['10000 leaflets over 2000 blocks', 'each leaflet equally likely on each block', 'target event → a particular block receives none'],[(107,'#/texts/104')],S,J,'The target probability is requested, not answered.',['Numerical answer not stated.']),
('exercise / observed counts versus Poisson prediction', ['576 areas and 537 hits', 'observed squares for 0,1,2,3,4,≥5 hits → 229,211,93,35,7,1', 'assume purely random hits', 'compute expected squares and compare with observations'],[(108,'#/texts/115')],S,J,'Explicit observed values, assumption and requested comparison remain distinct.',[]),
('exercise / independent Poisson sum', ['north count X mean m and west count Y mean m-bar', 'independence precondition', 'requested conclusion → X+Y Poisson with mean m+m-bar'],[(108,'#/texts/126')],S,J,'This is an exercise proposition conditional on independence; no proof is supplied here.',[]),
])

packet(211, [
('definition / bounded uniform density', ['U chooses a real number at random from [a,b]', 'f(ω)=1/(b−a) for a≤ω≤b, zero otherwise'],[(69,'#/texts/43'),(69,'#/texts/44')],S,J,'Intact piecewise formula and prose agree on the support.',['Nondegeneracy a<b is not explicit in these quotes.']),
('property / memorylessness named across two families', ['exponential density and geometric distribution → share memoryless property', 'P(T>r+s | T>r)=P(T>s)', 'property linked to Example 5.1'],[(69,'#/texts/66'),(69,'#/texts/67')],S,J,'This piece states the shared property name.',[]),
('model / interarrival sequence and rate interpretation', ['Xi are independent exponential random variables with parameter λ', 'Xi denotes time between ith and (i+1)st emissions', 'λ → reciprocal average time between emissions', 'Y counts emissions in interval length t; Sn sums interarrival times'],[(69,'#/texts/75'),(69,'#/texts/76')],S,J,'The source distinguishes continuous waiting times, discrete counts, and measurable parameter interpretation.',[]),
('derivation / projected exponential cumulative probability chain', ['Y=−log(rnd)/λ appears inside a displayed chain', 'chain ends at 1−exp(−λy)'],[(69,'#/texts/92')],'unresolved','ambiguous','The projection contains prose leakage in a formula piece; terminal expression is readable but the entire display is not clean.',['Clean mathematical display, parameter/domain conditions and surrounding algorithm declaration are not established by this piece.']),
('qualification / queue stability interpretation', ['λ<µ → average interarrival time greater than service time', 'λ>µ → arrivals faster than service', 'N(t) appears to grow without limit in latter case'],[(69,'#/texts/144')],S,J,'Source uses observational language appears and reasonable to expect; neither is promoted to a proved stability theorem.',[]),
('definition / customer system time includes service', ['Wi → time ith customer remains in system', 'system time includes waiting plus service', 'Figure 5.8 case λ=1,µ=1.1'],[(69,'#/texts/145')],S,J,'The parenthetical disambiguates waiting-only time from total system time.',[]),
('theorem / strictly increasing transformation of CDF', ['X continuous', 'φ strictly increasing on range of X', 'Y=φ(X)', 'FY(y)=FX(φ inverse(y))'],[(69,'#/texts/151'),(69,'#/texts/152')],S,J,'Hypotheses and intact identity are separate anchored pieces in one theorem.',[]),
('qualification / nonmonotone transformation depends on structure', ['φ neither strictly increasing nor decreasing → more complicated treatment', 'Y=X² used as example', 'express P(Y≤y) using events for X; form depends on φ'],[(69,'#/texts/168'),(69,'#/texts/172')],S,J,'The exception prevents extending the increasing-function formula without conditions.',['The fragmented inline typography and complete squared-variable derivation are not assessed.']),
('inverse transform / CDF strictness and uniform driver', ['F strictly increasing where 0<F(y)<1', 'U uniform on [0,1]', 'Y=F inverse(U) → has cumulative distribution F(y)'],[(69,'#/texts/190'),(69,'#/texts/191'),(69,'#/texts/192')],S,J,'The corollary supplies input conditions and transformation.',[]),
])

packet(221, [
('example / independent normal coordinates and radial target', ['dart x,y independent normal with µ=0,σ=1', 'target → distribution of distance from origin', 'n=3 particle speed density → called Maxwell'],[(101,'#/texts/60'),(101,'#/texts/61')],S,J,'The setup and three-dimensional naming statement are explicit.',['No unquoted radial derivation is inferred.']),
('table / two gender-by-grade grids preserve row and column bindings', ['Female and Male are column headers', 'A is row header', 'first grid A/Female=37 and A/Male=56', 'second grid A/Female=44.3 and A/Male=48.7'],[(101,'#/tables/0',0),(101,'#/tables/0',1),(101,'#/tables/0',2),(101,'#/tables/0',3),(101,'#/tables/0',4),(101,'#/tables/1',0),(101,'#/tables/1',1),(101,'#/tables/1',2),(101,'#/tables/1',3),(101,'#/tables/1',4)],S,J,'Native row/column coordinates and header flags establish local cell roles; counts and decimal-valued cells remain distinct.',['Captions/observed-versus-expected designation and full marginals not assessed here.']),
('model / independence testing and equivalent urn construction', ['319 balls in two colors → females/males', 'draw 93 without replacement → grade A; then 123 → grade B', 'four mutually exclusive sets', 'alternative color scheme by grade → same final independence decision'],[(102,'#/texts/72')],S,J,'The example explicitly describes alternative constructions and invariant decision.',['Calculation establishing that invariance not in this quote.']),
('explanation / standardized discrepancy metric', ['Oi observed and Ei expected cell values', 'same absolute difference more surprising at smaller expected count', 'sum squared differences divided by expected cell value', 'index i=1,…,8'],[(102,'#/texts/78'),(102,'#/texts/79')],S,J,'Explanation and intact equation bind numerator, denominator and index domain.',[]),
('decision rule / chi-square upper-tail threshold', ['v0 exceeded 5% of time', 'v≥v0 → reject independence', 'present example v0=7.815 → do not reject', 'observed statistic v=4.13 and 3 degrees of freedom'],[(102,'#/texts/98'),(102,'#/texts/99')],S,J,'The example preserves the distinction between being larger than many values and meeting rejection threshold.',[]),
('example / Cauchy mirror geometry and units', ['mirror axis one foot from wall', 'φ uniform between −π/2 and π/2', 'X → wall-hit displacement described relative to closest wall point', 'B fixed positive; X≥B iff tan(φ)≥B iff φ≥arctan(B)'],[(103,'#/texts/102'),(103,'#/texts/103')],S,J,'Geometry, unit, input support and event equivalence are explicit.',['Signed-distance convention outside these paragraphs remains unassessed.']),
('qualification / Cauchy averages exception', ['law of large numbers stated as applying in many cases', 'Cauchy sample average does not approach a specific number'],[(103,'#/texts/113')],S,J,'The counterexample is stated with its family qualification; it does not assert universal convergence.',[]),
('exercise / simulated sample compared with target density', ['generate 1000 random outcomes from Exercise 7 distribution', 'plot bar graph', 'compare empirical density with target cumulative-distribution density'],[(104,'#/texts/130')],S,J,'The actions and comparison target are specified; no results are supplied.',['Exercise 7 target and simulated observations not assessed.']),
('exercise / affine CDF transformation cases', ['Y=X+b; Z=aX; W=aX+b', 'a,b arbitrary constants', 'a>0,a=0,a<0 require different arguments'],[(104,'#/texts/159')],S,J,'The hint explicitly separates sign and degenerate scale cases; no solution is stated.',[]),
('exercise / tolerance and rejection specification', ['diameter normal µ=1,σ=.002', 'buyer tolerance 1.000±.003 cm', 'requested rejected fraction', 'reduce σ to make rejection no greater than one percent'],[(104,'#/texts/178')],S,J,'The paragraph binds physical unit, tolerance limits, parameter intervention and target rate.',['Numerical answer and required σ are not stated.']),
])

packet(231, [
('scope / numerical-valued variables for descriptive quantities', ['expected value and variance considered in these sections', 'both apply only to numerically-valued random variables', 'numerical values are assumed for all variables in scope'],[(89,'#/texts/27')],S,J,'The section-level assumption must travel with subsequent definitions.',[]),
('definition / expectation existence condition', ['discrete numerical X with sample space Ω and mass m(x)', 'mean denotes expected value E(X), abbreviated µ', 'absolute convergence required', 'failure of absolute convergence → X has no expected value'],[(89,'#/texts/42'),(89,'#/texts/44')],S,J,'Prose states the existence condition without repairing the formula projection.',['The adjacent display has leaked prose and is not used for an exact symbolic definition.']),
('table / nested sample-size headers and relative frequency', ['n=100 and n=10000 are grouping column headers', 'Winning identifies outcome column', 'Frequency and Relative Frequency distinguish measure types', 'outcome 1 has frequency 17 and relative frequency .17 under n=100; 1681 and .1681 under n=10000'],[(89,'#/tables/0',0),(89,'#/tables/0',1),(89,'#/tables/0',2),(89,'#/tables/0',3),(89,'#/tables/0',4),(89,'#/tables/0',5),(89,'#/tables/0',6),(89,'#/tables/0',7),(89,'#/tables/0',8),(89,'#/tables/0',9),(89,'#/tables/0',10),(89,'#/tables/0',11)],S,J,'Cell row/column offsets preserve multi-level header group and data alignment.',['Other outcomes and simulation provenance not assessed.']),
('qualification / divergent expectation in St Petersburg example', ['displayed sum is divergent', 'Y has no expectation', 'example named St Petersburg Paradox', 'unlimited willingness-to-pay suggestion contrasted with likely practical answer'],[(89,'#/texts/60')],S,J,'The conclusion follows explicitly from the referenced divergent sum; no damaged payment exponent is guessed.',['Exact payout expression and series are not assessed.']),
('example / waiting time outcomes and physical experiment', ['T time to first Bernoulli success; support positive integers', 'fair coin first heads expected 2 tosses', 'die first six expected 6 rolls'],[(89,'#/texts/65'),(89,'#/texts/74')],S,J,'Support and two numerical interpretation examples are explicit.',[]),
('definition / run maximality', ['HHHTTTTHT → first three heads form one run', 'next four tails, next head, next tail are other runs', 'first two tosses do not form a run because third agrees'],[(89,'#/texts/90')],S,J,'The negative example establishes the maximality condition of a run.',[]),
('theorem / expectation of a function without regrouping', ['X discrete with Ω,m(x); φ:Ω→R', 'E(φ(X)) equals sum over x of φ(x)m(x)', 'absolute convergence condition'],[(89,'#/texts/99'),(89,'#/texts/100'),(89,'#/texts/101')],S,J,'Declaration, intact formula and convergence proviso are independently anchored.',[]),
('theorem / finite-mean additivity', ['X,Y finite expected values', 'E(X+Y)=E(X)+E(Y)'],[(89,'#/texts/110'),(89,'#/texts/111')],S,J,'The displayed identity is scoped by its finite-expectation hypothesis.',[]),
('qualification / independence unnecessary for finite-sum expectation', ['finite sum → sum of individual expectations', 'mutual independence was not needed', 'property called First Fundamental Mystery of Probability'],[(89,'#/texts/132'),(89,'#/texts/133')],S,J,'The source explicitly excludes independence as a required hypothesis while limiting this extension to finite sums.',[]),
], inspected=[(88,'#/texts/24')])

packet(241, [
('theorem / Bernoulli expected success count', ['Sn counts successes in n Bernoulli trials with per-trial success probability p', 'E(Sn)=np'],[(78,'#/texts/3'),(78,'#/texts/4')],S,J,'The theorem and intact identity bind count, trials and parameter.',[]),
('limit / Poisson expectation assertion versus motivating guess', ['binomial limit n→∞ with np=λ', 'each approximating binomial has mean λ', 'Poisson mean λ asserted, proof left to Exercise 21'],[(79,'#/texts/11')],S,J,'The paragraph distinguishes the motivating guess from the asserted result and deferred proof.',[]),
('qualification / product expectation requires independence in general', ['E(XY)=E(X)E(Y) is not generally true', 'independence makes the identity hold'],[(80,'#/texts/13')],S,J,'The direct warning excludes using expectation additivity as product factorization.',[]),
('counterexample / dependent complementary indicators', ['single coin toss X=1 heads,0 tails', 'Y=1−X', 'both means 1/2', 'XY=0 on every outcome → E(XY)=0 differs from product of means'],[(80,'#/texts/32')],S,J,'The example supplies an explicit negative relationship with computed quantities.',[]),
('indicator / record probability by symmetry', ['Xj indicates year j sets a snowfall record', 'first year necessarily a record', 'symmetry gives E(Xj)=1/j', 'Sn counts records among first n years'],[(81,'#/texts/35')],S,J,'The source states the symmetry premise rather than independently establishing meteorological assumptions.',['Tie handling and empirical weather stationarity are not stated in the quote.']),
('formula / harmonic record expectation', ['E(Sn)=1+1/2+…+1/n', 'ten-year exact harmonic sum reported as 2.9290 versus approximation 2.9298'],[(81,'#/texts/38'),(81,'#/texts/44')],S,J,'The formula and prose distinguish exact finite-sum value from approximation.',[]),
('state machine / craps entry and terminal conditions', ['first roll 7 or 11 → win', 'first roll 2,3,12 → lose', 'otherwise r becomes point', 'continue until r or 7; r first → win,7 first → lose'],[(82,'#/texts/46')],S,J,'The game has separate first-roll and point-established transitions.',[]),
('graphic / craps tree caption only', ['Figure 6.1 identifies a tree measure for craps', 'caption alone does not establish branch probabilities'],[(82,'#/texts/51')],'unresolved','unassessed','Original tree diagram is unread; no character assembly is used.',['Visual branches and probability alignment uninspected.']),
('expectation / repeated game scaling', ['player expected gain in n plays → −n(.0141)', 'small expected loss per play may aggregate to large casino profit'],[(82,'#/texts/107')],S,J,'The statement is expected gain, not a guarantee for a particular run.',[]),
('declaration / roulette payoff and slot counts', ['38 slots including 0 and 00', '18 red,18 black,2 green', 'one-dollar red bet → +1 on red,−1 otherwise'],[(83,'#/texts/109')],S,J,'The slot/color and payoff mappings are explicit.',[]),
('scope / Monte Carlo and Las Vegas expected bets', ['Monte Carlo bets have different expectations', 'Las Vegas almost all bets share expected value −2/38≈−.0526'],[(83,'#/texts/172')],S,J,'The almost-all qualifier and geographic comparison are retained.',[]),
('definition / conditioning event and partition hypotheses', ['conditional expectation given event F introduced', 'Theorem 6.5 assumes pairwise-disjoint F1,…,Fr covering Ω'],[(84,'#/texts/174'),(84,'#/texts/177')],S,J,'The event and partition conditions are explicit.',['Condition P(F)>0 and complete displayed identities are not assessed; damaged display not repaired.']),
('state / two-stage craps roll accounting', ['X first roll', 'S number of second-stage rolls, sometimes zero', 'T total rolls =S+1', 'first-stage terminal sums 2,3,7,11,12', 'otherwise second stage stops at point or 7'],[(84,'#/texts/184')],S,J,'The state split and counted quantities disambiguate total rolls from additional rolls.',[]),
('conditional example / point four wait', ['point j=4 → success parameter 3/36+6/36=1/4', 'additional-roll S geometric', 'E(S)=4 and E(T|X=4)=5'],[(84,'#/texts/186')],S,J,'The example explicitly adds the first roll after computing remaining wait.',[]),
('definition / fair game and history conditioning', ['next expected fortune equals current fortune → fair game', 'fair game also called martingale'],[(85,'#/texts/195'),(85,'#/texts/194')],S,J,'The equation conditions on past fortunes, not merely an unconditional mean.',[]),
('strategy / finite horizon exposes final holding loss', ['buy at V,sell at V+1,repeat after price returns to V', 'finite trading days', 'last held interval may fail to reach V+1 → only loss route', 'stock model ±1 dollar with equal probability'],[(86,'#/texts/202')],S,J,'The finite horizon qualification prevents inferring guaranteed unit profits.',[]),
('distinction / positive-win probability versus expectation', ['20-day winnings mean zero', 'probability ahead about .610', 'claim conditional on simple random model being correct'],[(86,'#/texts/217')],S,J,'Probability of positive profit and mean profit are distinct quantities.',[]),
('interpretation / expectation as gamble value historically', ['frequency interpretation motivated by law of large numbers', 'historical expectation used as appropriate gamble value before formal definition'],[(87,'#/texts/219')],S,J,'The paragraph describes two interpretations and a historical relationship.',[]),
])

packet(251, [
('exercise / payoff by card parity', ['deck numbered 2 through 10', 'draw at random', 'odd → +1 dollar; even → −1 dollar', 'expected winnings requested'],[(92,'#/texts/69')],S,J,'Support, sampling and payoff rule are explicit; no answer supplied.',[]),
('exercise / bounded family stopping rule', ['children until first boy or third child, whichever first', 'each child boy probability 1/2', 'requested expected boys and girls'],[(92,'#/texts/80')],S,J,'Both stopping conditions must remain attached to the requested expectations.',['Independence across births not explicit in quote.']),
('exercise / without-replacement favorable stopping game', ['two gold and three silver balls', 'random sequential draws without replacement', 'gold +1 dollar,silver −1 dollar', 'stop when ahead by one dollar or no gold left', 'favorability is an exercise claim to show'],[(92,'#/texts/90')],S,J,'The state-dependent stop, payoff and depletion rule are explicit.',['Proof and computed expectation not supplied.']),
('exercise / utility differs from money payoff', ['utility of n dollars =√n', 'write expected utility and show finite value', 'repeat for log(n) utility'],[(92,'#/texts/103')],S,J,'The exercise changes the evaluated quantity through a utility transformation; no monetary expectation conclusion is inferred.',['Underlying game and exact expected utility not assessed.']),
('exercise / simulation repetitions and information condition', ['guessing without information → repeat at least 1000 experiments', 'estimate expected correct answers', 'compare simulation with theoretical expectation'],[(92,'#/texts/115')],S,J,'Required actions distinguish empirical estimate from theoretical target.',['Full guessing setup and theoretical value are not supplied in this quote.']),
('recursion / ESP expectation and boundary states', ['S stars,C circles; h(S,C) expected winnings using optimal guessing strategy', 'h(S,C)=S/(S+C) h(S−1,C)+C/(S+C) h(S,C−1)+max(S,C)/(S+C)', 'boundary h(0,0)=h(−1,0)=h(0,−1)=0', 'program computes h(10,10) and compares with simulation'],[(92,'#/texts/118'),(92,'#/texts/119'),(92,'#/texts/120')],S,J,'The recurrence, parameter roles, boundary values and computational action are explicit.',['Detailed optimal strategy in part (b) is not assessed.']),
('exercise / milk-tea experiment balance', ['eight cups total', 'four milk first and four tea first', 'test whether subject can distinguish order', 'no-information random guessing expected correct answers requested'],[(92,'#/texts/155'),(92,'#/texts/156')],S,J,'Balanced source categories, tested capability and no-information condition are explicit.',['No result, observed score or significance calculation stated in these pieces.']),
])

packet(261, [
('definition / variance around mean and standard deviation', ['µ=E(X)', 'V(X)=E((X−µ)²)', 'D(X)=√V(X)', 'σ denotes standard deviation; σ² denotes variance'],[(76,'#/texts/72'),(76,'#/texts/73'),(76,'#/texts/78')],S,J,'The definition and naming distinguish squared spread from its square root.',[]),
('table / header roles inferred from content despite absent native header flags', ['first row x,m(x),(x−7/2)² are semantic column headings', 'row x=1 → mass 1/6,squared deviation 25/4', 'row x=2 → mass 1/6,squared deviation 9/4'],[(76,'#/tables/0',0),(76,'#/tables/0',1),(76,'#/tables/0',2),(76,'#/tables/0',3),(76,'#/tables/0',4),(76,'#/tables/0',5),(76,'#/tables/0',6),(76,'#/tables/0',7),(76,'#/tables/0',8)],S,J,'Native cells establish coordinates even though column_header flags are false; semantic header reading rests on the quoted labels, not the flags.',['Remaining rows and original table visual layout uninspected.']),
('identity / alternative variance calculation', ['X with mean µ', 'V(X)=E(X²)−µ²'],[(77,'#/texts/91'),(77,'#/texts/92')],S,J,'The theorem declaration binds the mean in the intact identity.',[]),
('transformation / scale and shift affect variance differently', ['c constant', 'V(cX)=c²V(X)', 'V(X+c)=V(X)'],[(77,'#/texts/105'),(77,'#/texts/106'),(77,'#/texts/107')],S,J,'The distinct squared-scale and invariant-shift rules are explicit.',[]),
('counterexample / dependent summands defeat variance additivity', ['Y=−X with V(X)≠0', 'V(X)+V(Y)=2V(X)', 'X+Y=0 → variance zero', 'independent X,Y → V(X+Y)=V(X)+V(Y)'],[(77,'#/texts/111'),(77,'#/texts/113'),(77,'#/texts/114')],S,J,'The negative example and qualified positive theorem are both directly stated.',[]),
('asymptotic qualification / finite variance independent trials', ['independent trials and individual finite variances → standard deviation of average tends to zero', 'large n → average usually near its mean µ', 'precise law of large numbers deferred to Chapter 8'],[(77,'#/texts/144')],S,J,'The prose states conditions and informal versus later precise treatment.',[]),
('example / die averages fixed mean and shrinking variance', ['Xi die outcome mean 7/2,variance 35/12', 'Sn sum,An=Sn/n average', 'E(An)=7/2,V(An)=(35/12)/n', 'n grows → mean constant,variance tends zero'],[(77,'#/texts/176')],S,J,'The roles and limiting direction are explicit.',[]),
('parameter effect / geometric waiting-time variance', ['first heads waiting-count variance 2', 'first six waiting-count variance 30', 'decreasing p → rapidly increasing variance and distribution spread'],[(77,'#/texts/187'),(77,'#/texts/203')],S,J,'The waiting-count experiment and numerical variances are explicit.',['General symbolic q/p² derivation not assessed.']),
])

packet(271, [
('limit / Poisson variance motivation versus proof task', ['binomial variance npq', 'n→∞,p→0,np fixed λ and q→1 → npq→λ', 'Poisson variance λ offered as guess; Exercise 29 asks demonstration'],[(98,'#/texts/3')],S,J,'The statement keeps limit-based motivation separate from the deferred proof.',[]),
('exercise / three-point support and requested descriptive quantities', ['S={−1,0,1}', 'choose a number at random; X is chosen number', 'find mean,variance,standard deviation'],[(99,'#/texts/5')],S,J,'The support and target quantities are explicit; no numerical answer is given.',[]),
('unit transformation / Fahrenheit to Celsius', ['C=(5/9)(F−32)', 'requested mean and variance after Celsius conversion'],[(99,'#/texts/22')],S,J,'The exercise specifies an affine unit conversion; scaling variance and mean differently is not worked out here.',['Input Fahrenheit distribution and computed outputs unassessed.']),
('exercise / hats indicators and total', ['Xi indicates ith person gets own hat in random return', 'Sn sums Xi and counts all correct returns'],[(99,'#/texts/39')],S,J,'Individual event indicators and aggregate count have distinct roles.',['Displayed claims after show that are outside the quote.']),
('definition / unbiased estimator and denominator correction', ['replace 1/n by 1/(n−1) in s²', 'E(s²)=σ²', 's² estimates unknown σ²', 'estimator average equals estimand → unbiased'],[(99,'#/texts/61')],S,J,'The correction, equality and terminology are explicit; full sample-variance definition is elsewhere.',[]),
('definition / covariance and implication direction', ['Cov(X,Y)=E((X−E(X))(Y−E(Y)))', 'Cov(X,X)=V(X)', 'independence → covariance zero', 'converse fails; example requested'],[(99,'#/texts/74')],S,J,'The exercise states both the definition and non-equivalence of zero covariance and independence.',[]),
('definition / continuous expectation integral', ['X real-valued with density f(x)', 'µ=E(X)=integral x f(x) over real line'],[(100,'#/texts/94'),(100,'#/texts/95'),(100,'#/texts/96')],S,J,'Variable, density and formula are intact and anchored.',['Existence proviso is split among nearby pieces; not established by these quotes.']),
('example / disk radius differs from uniform radius', ['Z point chosen uniformly in unit disk', 'X distance to center', 'density of X stated as f(x)=2x'],[(100,'#/texts/112')],S,J,'Uniform area sampling is not conflated with uniform radial density.',['Density support and expectation result are not in this quote.']),
('theorem / expectation through continuous transformation', ['X real-valued; φ continuous', 'E(φ(X))=integral φ(x) fX(x) over real line', 'provided integral exists'],[(100,'#/texts/125'),(100,'#/texts/126'),(100,'#/texts/127')],'unresolved','ambiguous','The equation and existence qualification are clear; source describes φ:R→R and a domain [a,b] in the same sentence.',['That domain wording is retained as source ambiguity rather than silently reconciled.']),
('example / independent squared coordinates factor expectation', ['uniform unit-square point Z=(X,Y)', 'A=X²,B=Y² independent by cited theorem', 'E(AB)=E(A)E(B)=1/9'],[(100,'#/texts/142'),(100,'#/texts/144')],S,J,'Definitions, cited independence and resulting product expectation are explicit.',[]),
('identity / continuous variance integral about mean', ['X real-valued with mean µ', 'σ²=integral (x−µ)² f(x) over real line'],[(100,'#/texts/162'),(100,'#/texts/163')],S,J,'The theorem and intact integral bind squared deviation to density.',[]),
])

packet(281, [
('corollary / common-mean independent trials sum and average', ['Xi independent trials with E(Xi)=µ,V(Xi)=σ²', 'Sn=sum Xi;An=Sn/n', 'E(Sn)=nµ,E(An)=µ', 'V(Sn)=nσ²,V(An)=σ²/n'],[(93,'#/texts/38'),(93,'#/texts/39'),(93,'#/texts/40')],S,J,'The declaration and intact displays bind the shared moments, sum and average.',[]),
('transformation / standardized sum', ['Sn*=(Sn−nµ)/√(nσ²)', 'E(Sn*)=0,V(Sn*)=1', 'Sn* called standardized version of Sn'],[(93,'#/texts/41'),(93,'#/texts/42'),(93,'#/texts/43')],S,J,'The centering, scaling and resultant moments are directly stated.',['Positive σ² required by denominator is not explicit in these pieces.']),
('definition / arrival rate and service duration', ['X time between arrivals with exponential density λexp(−λt)', 'E(X)=1/λ', 'λ reciprocal expected interarrival time → arrival rate', 'service time includes time at head of line until leaving'],[(94,'#/texts/45'),(94,'#/texts/46'),(94,'#/texts/47')],S,J,'The source defines arrival rate via reciprocal waiting time and separately defines service duration.',[]),
('definition / traffic intensity and critical regimes', ['ρ=arrival rate×average service time=λ/µ=(1/µ)/(1/λ)', 'ρ<1 → queue performs reasonably', 'ρ>1 → queue grows indefinitely', 'ρ=1 → large queue with recurring empty times'],[(94,'#/texts/57'),(94,'#/texts/58')],S,J,'The formula binds the ratios and the prose distinguishes all three regimes.',[]),
('distribution / equilibrium queue length', ['queue length in equilibrium → geometric distribution', 'sj=(1−ρ)ρ^j for j=0,1,2,…'],[(94,'#/texts/85'),(94,'#/texts/86')],S,J,'The equilibrium qualifier and zero-based support differ from first-success waiting times.',['ρ<1 precondition appears elsewhere and is not present in these two pieces.']),
('unit / numeric queue rates lack explicit time-unit label locally', ['arrival rate 1,service rate 1.1,traffic intensity 10/11', 'a claim that these are per-minute rates is not established by this paragraph'],[(94,'#/texts/92')],'unstated','unsupported','The numerical rates are stated without a time-unit label in this quoted scope.',['Physical time unit is unstated in this paragraph; wider source not claimed absent.']),
('graphic / waiting-time distribution caption', ['Figure 6.9 identifies distribution of queue waiting times', 'caption alone cannot establish bin ranges, frequencies, or plotted values'],[(94,'#/texts/99')],'unresolved','unassessed','Original plot is uninspected.',['Axes, plotted marks and quantitative comparison uninspected.']),
('exercise / light-bulb lifetime units and parameter', ['T lifetime measured in hours', 'density stated λ² t exp(−λt)', 'λ=.05', 'expected lifetime and variance requested'],[(95,'#/texts/122')],S,J,'Units, density role and parameter are explicitly declared.',['No numerical answer or support condition supplied here.']),
('exercise / mean squared deviation objective', ['φ(a)=E((X−a)²)'],[(95,'#/texts/141')],S,J,'The intact formula declares an expected squared-deviation quantity.',['The exercise hypotheses and minimizer conclusion are not assessed.']),
('optimization / garage location and absolute distance', ['road length 100 miles', 'X breakdown location measured from Hangtown', 'b garage position', 'minimize E(|X−b|)', 'compare uniform breakdown model with density 2x/10000'],[(95,'#/texts/156')],S,J,'Physical interval, decision variable, target and alternative source distribution are explicit.',['No optimizing position is stated.']),
('exercise / renewal simulation comparison', ['specify density fX and time t', 'simulate N(t)/t', 'repeat 500 times and plot bar graph', 'estimate E(N(t)/t) and compare with 1/E(X)', 'specified t=100 for subsequent density cases'],[(95,'#/texts/172')],S,J,'The action sequence and empirical/theoretical comparison are explicit.',['Definitions of N(t),X and two subsequent density cases are outside this quote.']),
('concept / conditional expectation and regression to mean', ['ask E(X given Y)', 'father height to son expected height used as example', 'tall fathers → less-tall sons on average', 'effect called regression on mean', 'conditional density introduced as next step'],[(95,'#/texts/199')],S,J,'The prose describes conditional averages rather than a deterministic prediction for each individual.',['Complete conditional density formula and model assumptions not assessed.']),
])

packet(291, [
('scope / independent integer-valued sums and zero extension', ['chapter determines sum distribution from constituent distributions', 'this section discrete, next continuous', 'variables restricted to integer values', 'distribution functions extended as zero to other integers'],[(91,'#/texts/31'),(91,'#/texts/32')],S,J,'The domain restriction and zero-extension convention are explicit.',[]),
('definition / convolution hypotheses; formula contamination', ['independent integer-valued X,Y with mass functions m1,m2', 'convolution called distribution m3=m1*m2'],[(91,'#/texts/42'),(91,'#/texts/43')],'unresolved','ambiguous','The prose declaration is clear; the projected display appends stray 0 . 1 . 2 tokens after the summation.',['Clean full equation needs visual inspection; no stray symbols are silently removed.']),
('algorithm / convolution routine and finite support', ['routine takes densities p,q and returns convolution r', 'use it to obtain Sn density for n independent variables with common p', 'implementation scope qualified to finitely many possible values'],[(91,'#/texts/60')],S,J,'The source gives algorithm composition and a finite-support limitation, not a universal implementation.',[]),
('graphic / die-sum distributions caption', ['Figure 7.1 identifies density of Sn for n die rolls', 'no branch/curve numerical values recoverable from caption alone'],[(91,'#/texts/72')],'unresolved','unassessed','Original plots remain unread.',['Axes, curve identities and actual shape uninspected.']),
('closure / binomial family under convolution', ['binomial(m,p) convolved with binomial(n,p) → binomial(m+n,p)', 'common p required', 'sequential coin experiment gives explanation'],[(91,'#/texts/128')],S,J,'The shared success parameter and summed trial counts are explicit.',[]),
('model / arrivals count versus failures before success', ['per minute 0 or 1 arrival with probabilities q=1−p and p', 'Cr counts customers in first r minutes', 'Tr counts failures before rth Bernoulli success'],[(91,'#/texts/148')],S,J,'Count over a fixed duration and waiting failures until target success are distinguished.',[]),
('exercise / loaded-dice parameter constraints', ['faces 2,3,4,5 probability 1/6+r', 'faces 1,6 probability 1/6−2r', '0<r<.02', 'program finds winning probability and favorable r values for craps'],[(91,'#/texts/168')],S,J,'The asymmetric face groups, bounded parameter and requested action are explicit.',['No favorable r interval supplied.']),
('definition / continuous convolution symmetric integration forms', ['(f*g)(z)=integral f(z−y)g(y)dy', 'same value =integral g(z−x)f(x)dx', 'both integrals over whole real line'],[(91,'#/texts/173')],S,J,'The display is intact and preserves dummy variables and shifted arguments.',[]),
('example / independent uniform sum target', ['two independent numbers uniformly drawn from [0,1]', 'target → density of their sum'],[(91,'#/texts/181')],S,J,'The setup and requested derived density are explicit.',['Piecewise triangular density result is not assessed.']),
], inspected=[(90,'#/texts/28')])

packet(301, [
('closure / normal-convolution variance notation damaged', ['convolution of two normal densities is normal', 'means add', 'example proves standard-normal special case', 'general case referred elsewhere'],[(70,'#/texts/34')],'unresolved','ambiguous','Prose first calls σ1 and σ2 variances, then gives variance using flattened squared subscripts; general variance-parameter formula is not safely resolved from this piece.',['Exact general variance notation requires visual inspection; no correction guessed.']),
('density / Cauchy sum at scale two', ['two Cauchy inputs with parameter a=1', 'sum Z has density 2/[π(4+z²)]'],[(71,'#/texts/43'),(71,'#/texts/50')],S,J,'The input family/parameter and intact output display are anchored.',['Independence is supplied by the section header and surrounding context, not these two quotes.']),
('qualification / averaging Cauchy measurements', ['average of two Cauchy variables again Cauchy', 'measurement errors with this density → average not expected to be more accurate than individual measurements'],[(71,'#/texts/56')],S,J,'The consequence is conditional on the Cauchy error model; no empirical claim about actual instruments is implied.',[]),
('transformation / squared radius and radius have different densities', ['independent standard-normal X,Y locate P', 'target squared distance from origin', 'R² gamma with λ=1/2,β=1', 'radius R density r exp(−r²/2) for r≥0,zero otherwise'],[(72,'#/texts/58'),(72,'#/texts/67'),(72,'#/texts/69')],S,J,'The setup, gamma square and piecewise radius density remain distinct.',[]),
('definition / chi-square through standard-normal squares', ['sum squares of n independent normals with mean0,standard deviation1', 'gamma λ=1/2,β=n/2', 'called chi-squared with n degrees of freedom'],[(73,'#/texts/72')],S,J,'Independence, standardization, gamma parameters and degrees of freedom are all explicit.',[]),
('scope / finite category grouping for goodness of fit', ['compare experimental data with theoretical discrete distribution', 'finite outcome set; group countably many outcomes into finitely many sets', 'repeat experiment to obtain data'],[(73,'#/texts/73')],S,J,'The finite-category scope and grouping transformation are declared.',[]),
('approximation / chi-square statistic distribution and decision', ['moderate or large n → V approximately chi-squared with ν−1 degrees of freedom', 'ν number of outcomes', 'very large V relative to density → tend to reject model'],[(73,'#/texts/80')],S,J,'The sample-size qualification, approximation and nonabsolute decision wording are retained.',[]),
('statistic / fairness of die by expected cell counts', ['fair die model → uniform integers1…6', 'n rolls → expected count n/6 per type', 'oi observed count for face i', 'V=sum i=1…6 of (oi−n/6)²/(n/6)'],[(73,'#/texts/81'),(73,'#/texts/82')],S,J,'The prose and intact formula distinguish observations, expectation and standardized discrepancy.',[]),
('graphic / die simulation caption only', ['Figure 7.5 caption identifies rolling a fair die', 'caption does not establish plotted empirical histogram or fit'],[(73,'#/texts/100')],'unresolved','unassessed','The original graphic and numerical marks are uninspected.',['Plot bins, mark values, sample size and observed comparison not assessed here.']),
('sum / independent common-density trials', ['X1,…,Xn independent with same density', 'Sn=sum Xi', 'density fSn is n-fold convolution of input densities'],[(74,'#/texts/140'),(74,'#/texts/141'),(74,'#/texts/142')],S,J,'The hypotheses and intact formula preserve common-density and independence scope.',[]),
('density / normal sum displayed variance scale', ['fSn(x)=1/√(2πn) exp(−x²/(2n))'],[(74,'#/texts/172')],S,J,'The displayed density is intact.',['Input standard-normal declarations outside the anchor not assessed.']),
('derivation actions / independent continuous sum', ['joint density fX(x)fY(y) because X,Y independent', 'integrate over region X+Y≤z → CDF of Z', 'differentiate with respect to z → density'],[(75,'#/texts/179')],S,J,'The hint specifies causal derivation steps and independence precondition.',[]),
('exercise / shifted uniform input density', ['fX=fY=1/2 for 3≤x≤5', 'zero otherwise'],[(75,'#/texts/202')],S,J,'The intact piecewise expression binds value and support.',['The summed-density answer is not supplied in this piece.']),
('exercise / service total and minutes', ['single-customer service time exponential with mean2 minutes', 'X total service time for 10 customers', 'requested estimate P(X>22 minutes)'],[(75,'#/texts/232')],S,J,'Time units, count and exceedance threshold are explicit.',['Independence of customer service times and probability answer not stated in this paragraph.']),
])
