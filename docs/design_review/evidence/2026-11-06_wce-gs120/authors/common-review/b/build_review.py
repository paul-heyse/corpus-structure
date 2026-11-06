"""Build reviewer B's explicitly authored assessments; no other reviews are inputs."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FRAME = ROOT / 'authors/c/source-adjudication/common-source-cases.json'
FRAME_SHA = '850142fe59133abe0f221c142709f15579bb974e407536ee2c04cf33dbc58f15'
raw = FRAME.read_bytes()
assert hashlib.sha256(raw).hexdigest() == FRAME_SHA
frame = json.loads(raw)

# Each role and relation is assessed in its input order. These are explicit B
# decisions, not copied input judgments or a default-agreement operation.
# S=supported, U=unsupported, A=ambiguous, N=unassessed.
ROWS = {
1: ('SSSS', 'SS', 'Finite nonempty discrete experiment with equally likely outcomes; the assignment concerns each omega in S.',
    'The source explicitly says we say uniformly distributed and assigns mass 1/n. The content describes equiprobability; it does not independently specify a continuous uniform density.',
    [('finite_uniform_definition','S','term,content,context'),('finite_nonempty_domain','S','condition,mass'),('same_finite_mass_assignment_on_continuous_or_countably_infinite_space','U','context')]),
2: ('SSS', 'SS', 'Geometric service-time example under its modeling assumption; exponential-family attribution is expressly stated.',
    'The explanation concerns remaining service time conditional on prior service. It names the memoryless property and says the exponential distribution also obeys it. This does not state that all actual service times are memoryless.',
    [('conditional_remaining_time_explanation','S','explanation'),('exponential_property_attribution','S','other_family,term,context'),('universal_actual_service_property','U','context')]),
3: ('SS', 'SU', 'Binomial distribution formula as projected, with visibly damaged right-hand content.',
    'The displayed right side is a matrix-like object containing n and p^k q^(n-k). The source locates it as a formula for b(n,p,k), but this fragment cannot be accepted as a mathematically complete binomial definition. The missing or intended coefficient is unresolved without another source representation.',
    [('formula_subject_and_projection_association','S','head,tail,context'),('mathematically_complete_definition','U','tail'),('intended_repair_of_coefficient','A','tail')]),
4: ('SSSS', 'S', 'Approximate binomial simulation using a normal variate, in the stated relatively-large-n context.',
    'Both inequalities and the reject-and-resample action are stated. Acceptance uses a strict upper bound, while rejection also uses a strict upper comparison: equality at the upper boundary is not assigned by either sentence. Do not silently replace either inequality.',
    [('acceptance_and_rejection_text','S','accept,reject,action'),('normal_parameter_mapping','S','parameters,context'),('action_at_upper_equality','A','accept,reject'),('exact_binomial_sampler_guarantee','U','context')]),
5: ('SSSSSS', 'SS', 'Table 5.1, row j=0, separately identified Poisson and binomial columns.',
    'Native cells put the two equal strings .9048 in distinct columns below their respective parameterized headers. Equality of rounded values does not merge the cells or their distributions.',
    [('poisson_header_value_binding','S','poisson_header,poisson_value,row'),('binomial_header_value_binding','S','binomial_header,binomial_value,row'),('independent_evidence_from_equal_strings','U','poisson_value,binomial_value')]),
6: ('SSSSSS', 'SSS', 'Textual legend and Figure 5.3 reference; no original graphic inspection.',
    'The body explicitly maps observed frequencies to squares and predicted frequencies to dots; the figure number matches its caption. This establishes what the text says about the legend, not pixel-level validation of marks or measured agreement.',
    [('textual_legend_direction','S','observed,squares,predicted,dots,context'),('figure_number_link','S','body_reference,caption'),('graphic_marks_and_fit','N','caption')]),
7: ('SSSS', 'US', 'Finite population of N balls, k red, sample of n without replacement; notation is local to this text.',
    'X counts red balls; the hypergeometric distribution is the law of that count. A distribution does not itself perform the counting, so the proposed counts_under_condition edge with term as head is too literal. The notation h(N,k,n,x) denotes P(X=x) as stated.',
    [('named_distribution_of_count','S','term,content,condition,context'),('distribution_itself_counts','U','term,content'),('local_notation_denotes_probability','S','notation,probability,context')]),
8: ('SSS', 'S', 'Benford first-digit distribution for integer digits k=1 through 9.',
    'The displayed equality has f(k) on the left and the logarithmic difference on the right. The displaced domain sentence follows in the same passage. The source restricts the discussion to first digits, not arbitrary digit positions or every real-life dataset.',
    [('directed_defining_equality','S','head,tail,context'),('digit_domain','S','condition'),('universal_dataset_fit','U','context')]),
9: ('SSSS', 'SU', 'Exercise 2: repeatedly remove and record one random number from S until S is empty.',
    'The source states the full repeated process yields a permutation, and asks whether X is uniform. One execution of the anchored removal action does not produce the full permutation; the proposed produces edge needs the repeated-process scope rather than a single action endpoint.',
    [('loop_and_terminal_condition','S','action,terminal,context'),('full_process_permutation_result','S','context,result'),('single_removal_produces_permutation','U','action,result'),('answer_to_uniformity_question','N','question')]),
10: ('SSSSS', 'SSS', 'Reported Poisson simulation recipe only; its parameterization is not certified correct.',
    'The text says same exponential parameter lambda, stop at a subtotal exceeding lambda, and return n. Earlier it associates exponential waiting times through time t with Poisson parameter lambda*t. These claims are individually stated but leave the requested lambda scale inconsistent or unresolved; no silent rate/threshold repair is justified.',
    [('literal_recipe_and_return','S','target,driver,threshold,return,context'),('earlier_lambda_t_mapping','S','earlier_parameter'),('correct_target_scale','A','driver,threshold,earlier_parameter')]),
11: ('SSSS', 'SS', 'Theorem 5.1: continuous X, Y=phi(X), strict monotonicity on the range of X; inverse evaluated on its applicable range.',
    'The increasing and decreasing branches have distinct CDF formulas. Neither monotonicity phrase alone licenses the equality for arbitrary unrelated X and Y; the enclosing theorem supplies the transformation and continuous-variable assumptions.',
    [('increasing_branch','S','increasing,increasing_formula,context'),('decreasing_branch','S','decreasing,decreasing_formula,context'),('unconditional_transform_formula','U','context')]),
12: ('SSSSS', 'SS', 'Speed or radial density from mutually independent normal components in the source model; n=3 Maxwell, n=2 Rayleigh.',
    'The names are attached to different dimensions of the same radial-speed construction, not to any arbitrary density in those dimensions. The nearby dart example uses standard normal coordinates; no unseen general parameter formula is inferred from the short naming anchors.',
    [('Maxwell_dimension_in_model','S','Maxwell,dimension3,context'),('Rayleigh_dimension_in_model','S','Rayleigh,dimension2,rayleigh_context'),('arbitrary_dimension_only_definition','U','dimension3,dimension2')]),
13: ('SSSSSS', 'SSS', 'Calculus class data Table 5.8 versus expected data Table 5.9, Female/A cell in each.',
    'Native cell coordinates establish Female as column and A as row in both tables. Captions distinguish collected data and expected data. 44.3 is the expected counterpart for the same category as observed 37, not a second observation or a probability.',
    [('observed_and_expected_header_bindings','S','observed_column,observed_row,observed_value,expected_column,expected_row,expected_value'),('category_counterpart_direction','S','expected_value,observed_value'),('values_are_probabilities','U','expected_value,observed_value')]),
14: ('SSSS', 'SS', 'Bearing-shaft exercise: normally modeled diameters with stated sigma and buyer specification in cm.',
    'The spread parameter .002 and the half-width .003 serve different roles. The full acceptance specification is 1.000 plus or minus .003 cm. The passage asks for a rejection fraction and a revised sigma; it does not supply those numerical answers.',
    [('parameter_and_tolerance_roles','S','spread,tolerance,context'),('tolerance_unit','S','tolerance,unit'),('numerical_rejection_answer','N','question')]),
15: ('SSSSS', 'SA', 'Table 5.10 F row and adjacent projected score-boundary text; no original pixels.',
    'The damaged cell maps to F by same-row structure. An adjacent standalone text item contains the intact minus sign, but proximity and matching symbols alone do not establish that it is a duplicate representation of precisely that table cell. Treat it as a candidate, not an authorized replacement.',
    [('projected_F_row_mapping','S','damaged,grade,column,grade_column'),('parallel_representation_identity','A','intact,damaged'),('intended_boundary_repair','A','intact,damaged')]),
16: ('SSSS', 'S', 'Definition 6.1 for a numerically-valued discrete random variable with the stated distribution.',
    'The expected-value sum is defined subject to absolute convergence. Failure of absolute convergence is expressly called absence of an expected value. Mean is a synonym in this context; condition removal would materially change the definition.',
    [('expectation_definition','S','term,formula,context'),('absolute_convergence_requirement','S','condition,failure_context'),('failure_state','S','failure,failure_context')]),
17: ('SSSSS', 'SS', 'The displayed coin-toss example HHHTTTTHT; maximal constant blocks in that example.',
    'The first three heads are called a run. The first two tosses are excluded because the third agrees with them, giving explicit maximality evidence. This is an explanatory example rather than a freestanding formal definition of every possible run domain.',
    [('run_example','S','sequence,block,term,context'),('nonmaximal_exclusion','S','excluded_block,explanation,context'),('general_formal_definition_claim','U','context')]),
18: ('SSSSSSS', 'SS', 'Dice-game frequency table, outcome 1 under the n=100 grouped columns.',
    'The n=100 group spans the count and relative-frequency columns containing 17 and .17. n=10000 heads a separate group. Count and relative frequency are different measures, even when numerically related.',
    [('nested_header_bindings','S','group,count_header,relative_header,outcome,count,relative'),('separate_group','S','other_group'),('relative_frequency_is_observation_count','U','relative,count')]),
19: ('SSS', 'S', 'Theorem 6.2: X and Y have finite expected values; its additive generalization has the corresponding hypotheses.',
    'The source explicitly says mutual independence was not needed. This is a non-requirement claim, not a claim that X and Y are independent, and not permission to omit finite-expectation hypotheses.',
    [('linearity','S','linearity,condition_context'),('independence_not_required','S','independence,not_needed,context'),('actual_independence_assertion','U','context')]),
20: ('SSSSS', 'SS', 'Roulette option (b), bet in prison state P1, outcomes on the next turn.',
    'Red returns the existing stake without winnings; black or zero loses it. These are conditional transitions within this option, not rules for every prison variant or statements of payout probabilities.',
    [('red_returns_stake','S','state,red,return,context'),('black_or_zero_loses_stake','S','state,black_zero,loss,context'),('return_equals_net_win','U','return,context')]),
21: ('SSSS', 'SS', 'Textual citation of Sagan with marker 1 and its bibliographic note.',
    'The marker and surname connect the body citation to the note. The note states H. Sagan as author of Markov Chains in Monte Carlo. This is bibliographic attribution; the cited paper itself was not consulted.',
    [('body_to_note_link','S','body_reference,note'),('title_to_author_attribution','S','title,author,note'),('external_paper_content','N','note')]),
22: ('SSSS', 'SSS', 'Exercise (d), expected winnings h(S,C) under the optimal guessing strategy referenced in (b); recurrence is a statement to show.',
    'The exercise supplies a recurrence, boundary assignments, and requests a program. It does not report a completed proof or program output. The rational expression cannot simply be evaluated at S=C=0; boundary assignments must remain separate from the recursive step.',
    [('exercise_asserted_recurrence','S','head,tail,context'),('separate_boundary_assignments','S','boundary'),('requested_computation','S','action,head'),('supplied_proof_or_computed_value','N','context,action')]),
23: ('SSSS', 'SS', 'Definition 6.3 for a numerically-valued X with expected value mu=E(X).',
    'Variance is given as the expected squared deviation, and standard deviation as its square root. The source identifies notation D(X), sigma, and sigma squared in the adjacent sentence; these statements do not establish finite variance for all distributions with a mean.',
    [('variance_definition','S','variance,variance_formula,context'),('standard_deviation_definition','S','deviation,root,deviation_context'),('universal_finite_variance','U','context')]),
24: ('SSSSSS', 'SS', 'Variance-computation table, first outcome row x=1.',
    'The row of x, m(x), and squared deviation functions acts semantically as column headings despite native false header flags. The first data row gives mass 1/6 and squared deviation 25/4; the latter is not a probability.',
    [('semantic_header_bindings','S','outcome_header,mass_header,deviation_header,outcome,mass,deviation'),('squared_deviation_measure','S','deviation_header,deviation'),('native_false_flags_imply_no_headers','U','outcome_header,mass_header,deviation_header')]),
25: ('SSSS', 'SS', 'Theorem 6.9 independent trials with common stated mean and variance; proof identifies A_n with S_n/n.',
    'The theorem display loses the denominator, but its proof explicitly gives V(A_n)=sigma squared/n through a chain of equalities. This supports the proof relation and a parallel claim location; it does not make the damaged literal display intact.',
    [('damaged_theorem_display','S','damaged'),('intact_proof_equality','S','head,tail,proof_context,conditions'),('parallel_claim_location','S','damaged,proof_context'),('damaged_literal_contains_denominator_n','U','damaged')]),
26: ('SSS', 'SS', 'Covariance exercise: the displayed implications and requested counterexample are tasks; covariance expectations must exist for numeric interpretations.',
    'The exercise asks to prove independence implies zero covariance and to give a dependent zero-covariance example. It therefore supports the stated implication direction and warns against its converse. It does not supply a particular counterexample or prove existence of all moments for arbitrary random variables.',
    [('exercise_forward_implication','S','independence,zero,context'),('converse_not_guaranteed_in_exercise','S','zero,not_independent,context'),('supplied_counterexample','N','not_independent,context'),('unqualified_all_random_variables_have_covariance','U','context')]),
27: ('SSSSS', 'SS', 'Local stable-queue discussion with traffic intensity below 1 and finite expected length/wait; waiting-time population includes zero waits.',
    'The name labels N=lambda*T. The scope note includes all customers, even zero-wait customers. The local numerical rates 1 and 1.1 have no physical time unit stated in the quoted rate anchor. The condition anchor is material and needs its own typed role.',
    [('named_law','S','name,equation,context'),('zero_wait_customer_inclusion','S','scope,included,context'),('stable_finite_local_scope','S','condition'),('local_rates_have_minutes_unit','U','rates')]),
28: ('SSSSS', 'SS', 'Definition 7.1 for two independent integer-valued variables and their distribution functions.',
    'The definition gives convolution notation and a projected sum with an extraneous numerical tail. The earlier intact probability sum provides separate nearby support for the sum construction, but no repair of the damaged literal projection is performed.',
    [('definition_and_local_notation','S','term,conditions,notation,context'),('display_association','S','term,damaged_display'),('earlier_sum_formula','S','earlier_intact_formula'),('meaning_of_extraneous_tail','A','damaged_display')]),
29: ('SSSSSS', 'SSA', 'Example 7.5 normal convolution and subsequent proof for two independent standard normals; general parameter typography unresolved.',
    'The source asserts normal closure and additive means. The input words call sigma1 and sigma2 variances, whereas the output uses squared sigma symbols with broken typography. Do not silently reinterpret the input as standard deviations or certify a general variance formula. The proof is explicitly restricted to the standard-normal case.',
    [('normal_family_closure','S','inputs,output,context'),('mean_mapping','S','inputs,output_mean,context'),('general_variance_mapping','A','input_variance_words,output_variance_words'),('proof_scope','S','proof_scope')]),
30: ('SSSS', 'SSS', 'Bank exercise: individual service time is modeled exponential with mean 2 minutes; X is total for 10 customers.',
    'The requested event is total time above 22 minutes. The source excerpt supplies neither the numerical tail probability nor an explicit independence assumption between customer service times. It does not give a new definition of the exponential family.',
    [('individual_mean_and_units','S','individual,mean,context'),('ten_customer_aggregation','S','aggregate,individual,context'),('requested_tail_event','S','aggregate,threshold'),('numerical_answer_or_explicit_independence','N','context')]),
31: ('SSSS', 'SSS', 'Sum of squares of n independent normal variables each with mean 0 and standard deviation 1.',
    'The text expressly names the resulting gamma density chi-squared, gives lambda=1/2 and beta=n/2, and assigns n degrees of freedom. These parameters belong to this text\'s gamma convention; they do not license a rate/scale conversion for another convention.',
    [('construction_definition','S','term,construction,context'),('gamma_parameters','S','term,gamma_parameters'),('degrees_of_freedom','S','term,degrees'),('other_gamma_convention_mapping','N','gamma_parameters')]),
32: ('SSSSSS', 'SSSS', 'Figure 7.5 textual experiment: 60 die rolls, then calculation of V, repeated 1000 times by DieTest.',
    'The body attributes both roll and replication work to DieTest and links to the caption. Replication includes calculating V, not just rolling 60 times. The graph label supports the hierarchy; no pixels, executable program, or numerical goodness of fit were verified.',
    [('roll_replication_hierarchy','S','inner,outer,label,context'),('program_attribution','S','program,inner,outer,context'),('figure_reference_link','S','body_reference,caption'),('graphic_fit_and_executable_behavior','N','caption,program')]),
}

STATUS = {'S':'supported','U':'unsupported','A':'ambiguous','N':'unassessed'}
CASES = []
for number, c in enumerate(frame['cases'], 1):
    rs, es, scope, reason, facets = ROWS[number]
    assert len(rs) == len(c['expected']['roles'])
    assert len(es) == len(c['expected']['relations'])
    anchors = c['anchors']
    roles = []
    for proposed, status in zip(c['expected']['roles'], rs, strict=True):
        roles.append({**proposed, 'judgment':STATUS[status], 'evidence':[proposed['anchor']],
                      'scope':scope, 'reason':reason})
    relations = []
    for proposed, status in zip(c['expected']['relations'], es, strict=True):
        relation = {k:v for k,v in proposed.items() if k != 'judgment'}
        relation.setdefault('conditions', [])
        evidence = list(dict.fromkeys([relation['head'], relation['tail'],
            *relation['conditions'], *(['context'] if 'context' in anchors else [])]))
        relations.append({**relation, 'judgment':STATUS[status], 'evidence':evidence,
                          'scope':scope, 'reason':reason})
    facet_rows = [{'facet':f, 'judgment':STATUS[s], 'evidence':refs.split(','),
                   'reason':reason} for f,s,refs in facets]
    CASES.append({'id':c['id'], 'facet':c['facet'], 'source_packet':c['source_packet'],
        'source_view_id':c['source_view_id'], 'passage_id':c['passage_id'], 'pages':c['pages'],
        'anchors':anchors, 'scope':scope, 'reason':reason,
        'role_judgments':roles, 'relation_judgments':relations,
        'facet_judgments':facet_rows, 'corrections':[], 'missing_facets':[]})

def correction(n, kind, head, tail, conditions, judgment, reason):
    CASES[n-1]['corrections'].append({'type':kind,'head':head,'tail':tail,
        'conditions':conditions,'judgment':judgment,'scope':CASES[n-1]['scope'],
        'evidence':list(dict.fromkeys([head,tail,*conditions])), 'reason':reason})

correction(7,'describes_count_under_sampling_condition','term','content',['condition','context'],
    'supported','Use the distribution as a law of the red-ball count; X, not its law, performs the counting. Context retains N,k,n and the population composition.')
correction(9,'repeated_process_produces','context','result',['terminal'],'supported',
    'The context endpoint denotes the complete repeat-until-empty process; the action endpoint alone denotes one removal.')
correction(11,'licenses_formula','increasing','increasing_formula',['context'],'supported',
    'Preserve continuous X and Y=phi(X), not strict increase alone.')
correction(11,'licenses_formula','decreasing','decreasing_formula',['context'],'supported',
    'The same transformation assumptions apply to the decreasing branch.')
correction(22,'exercise_asserts_recursion','head','tail',['context'],'supported',
    'This is an assertion to show in an exercise, with separate base assignments, not a supplied proof.')
correction(27,'names_relation','name','equation',['condition'],'supported',
    'Keep the local stable, finite-expectation queue scope with the named equation.')
correction(29,'variance_parameter_mapping','input_variance_words','output_variance_words',[],
    'ambiguous','Do not choose a variance/standard-deviation normalization from inconsistent typography.')

MISSING = {
1:[('assignment_domain','supported',['context','condition','mass'],'The mass assignment is over the finite nonempty sample space S; not every distribution of a transformed X is thereby uniform.')],
2:[('geometric_service_model_context','supported',['context','explanation'],'The named property is explanatory in the service-time example, not an empirical universal.')],
4:[('large_n_approximation','supported',['context','parameters'],'Retain the source relatively-large-n qualification and approximate rather than exact simulation claim.')],
6:[('original_graphic','unassessed',['caption'],'Textual legend support does not inspect the graphic.')],
7:[('probability_target_role','supported',['probability','notation'],'P(X=x) is the probability target of the local denotes relation.')],
9:[('uniformity_answer','unassessed',['question'],'This source asks the question and does not answer it here.')],
10:[('boundary_count_inequality','supported',['context','threshold','return'],'Nearby source says S_n <= lambda < S_(n+1). Count-return text is literal; the intended lambda parameter remains unresolved.')],
12:[('radial_construction_conditions','supported',['context','rayleigh_context'],'Independent normal components and speed/distance construction are material, not dimension alone.')],
13:[('row_header_value_bindings','supported',['observed_row','observed_value','expected_row','expected_value'],'A also labels both selected cells; column header bindings alone omit a material axis.')],
14:[('revised_sigma_question','supported',['context','spread'],'The context also requests a sigma giving at most one percent rejection; no answer is supplied.')],
15:[('original_representation_identity','unassessed',['damaged','intact'],'Original graphic not inspected, so do not promote the candidate identity or repair to settled.')],
16:[('mean_synonym','supported',['failure_context','term'],'The source also calls expected value the mean and denotes it by mu.')],
19:[('finite_expectation_hypothesis','supported',['condition_context'],'Finite expected values remain required even though independence is unnecessary.')],
20:[('next_turn_and_no_winnings','supported',['context','red','return'],'The return occurs on the next turn and gives stake back without any win.')],
22:[('recurrence_domain','ambiguous',['head','tail','boundary'],'The denominator S+C requires a nonzero total in the recursive step; exact recursion domain is not explicitly typed in these anchors. Do not recurse blindly at the supplied boundary states.')],
23:[('mean_hypothesis','supported',['context'],'Definition begins with mu=E(X); finite variance is not guaranteed by the anchor.')],
25:[('average_identity','supported',['proof_context'],'The proof explicitly relates A_n to S_n/n; condition text alone ends before that definition.')],
26:[('covariance_definition','supported',['context'],'The source defines Cov(X,Y)=E((X-E(X))(Y-E(Y))) and notes Cov(X,X)=V(X). This definition is not typed in the proposed roles.')],
27:[('stability_condition_role','supported',['condition'],'The existing condition anchor should be typed as local stability/finite-expectation scope; a physical rate time unit remains unstated locally.')],
28:[('formula_tail_quality','ambiguous',['damaged_display'],'Extraneous 0.1.2 tail is preserved rather than interpreted as formula content.')],
29:[('independent_standard_normal_proof','supported',['proof_scope','context'],'Only the special-case proof is locally promised; do not promote it to a repaired general parameter derivation.')],
30:[('independence_of_customer_times','unassessed',['context'],'No explicit independence is supplied in the exercise excerpt; do not append it as observed source content.')],
31:[('gamma_convention','unassessed',['gamma_parameters'],'Exact conversion to another gamma parameter convention is outside this anchored assessment.')],
32:[('calculate_V_inside_each_replication','supported',['context'],'The experiment includes calculating V after its 60 rolls; the inner roll anchor is only one component.')],
}
for n, rows in MISSING.items():
    CASES[n-1]['missing_facets'] = [{'facet':f,'judgment':s,'evidence':ev,'reason':why}
                                   for f,s,ev,why in rows]

CASES[6]['additional_role_judgments'] = [{'role':'probability_target','anchor':'probability',
    'judgment':'supported','evidence':['notation','probability','context'],
    'scope':CASES[6]['scope'],'reason':'The denotes edge has a probability expression as its target.'}]
CASES[26]['additional_role_judgments'] = [{'role':'local_stability_and_finiteness_condition',
    'anchor':'condition','judgment':'supported','evidence':['condition'],
    'scope':CASES[26]['scope'],'reason':'Retain the explicit condition that traffic intensity is below 1 and expected queue length is finite.'}]

packets = {}
for key, entry in frame['source_packets'].items():
    path = ROOT / entry['path']; b = path.read_bytes(); packet = json.loads(b)
    digest = hashlib.sha256(b).hexdigest(); assert digest == entry['sha256']
    packets[key] = {**entry,'verified_sha256':digest,
        'protocol':packet['protocol'],'source_pdf':packet['source_pdf'],
        'source_pdf_sha256':packet['source_pdf_sha256'],
        'parent_pdf_sha256':packet['parent_pdf_sha256'],
        'parent_physical_pages':packet['parent_physical_pages'], 'page_map':packet['page_map']}

review = {
    'protocol':'gs120-independent-common-source-review-b-1', 'reviewer':'B',
    'date':'2026-11-06','status':'complete_32_case_independent_source_assessment',
    'input_frame':{'path':'authors/c/source-adjudication/common-source-cases.json','sha256':FRAME_SHA},
    'exposure_disclosure':{
        'not_fully_blinded':True,
        'observed_C_material':'Initial metadata display exposed C-authored coverage, coordinate contract, source packet metadata and remaining_gaps (including their judgments). The first case display exposed case 001 source_state, reason and missing_facets. The initial cases 001-008 display included expected fields without stripping embedded judgments; case 003 relation judgments were explicitly observed. Later case displays selected question-frame fields and removed embedded relation judgments. Large early source displays were truncated; selected anchors and relevant source context were subsequently displayed in bounded batches.',
        'other_reviews_or_outputs':'No A review, other author inventory, prediction, producer output, tests, status, plans, database, PDF pixels, or outside source consulted.',
        'independent_method':'All 32 roles/relations/facets assessed from literal neutral packet passages and selected surrounding text/native table structure. C typed fields were question frames, never answer authority; source anchors were locations, not semantic votes.',
    },
    'coverage':{'case_count':32,'selection':'all cases in frozen common frame; selective source assessment, not census',
        'source_packets':12,'unassessed':'Original graphics/PDF pixels, missing or unselected projections, external cited works, executable simulations and unseen answers. Omission is not absence.',
        'judgment_semantics':'supported means source supports scoped assertion; exercise assertions do not establish completed proof. unsupported rejects the specified claim, ambiguous preserves unresolved interpretation, unassessed means not settled by this review.'},
    'source_packets':packets,
    'cases':CASES,
    'disagreements':[
        {'case_id':'GS120-COMMON-003','facet':'mathematically_complete_definition','B_judgment':'unsupported','reason':'The visible damaged RHS cannot serve as a complete definition; intended reconstruction remains ambiguous.'},
        {'case_id':'GS120-COMMON-007','facet':'counts_under_condition','B_judgment':'unsupported','reason':'Typed distribution head is a law, not the counting random variable; correction supplied.'},
        {'case_id':'GS120-COMMON-009','facet':'produces','B_judgment':'unsupported','reason':'One removal action is not the full repeated process producing the permutation; correction supplied.'}
    ],
    'limits':'This review records B\'s judgments. It does not claim consensus, independent evidence from repeated quotations, full blinding, complete source understanding, or semantic capture of the full chapter.'
}
(OUT/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(f'Wrote {len(CASES)} cases to {OUT / "review.json"}')
