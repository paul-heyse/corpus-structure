"""Bounded qualifier witnesses over one retained annotation block."""

from dataclasses import replace
from functools import lru_cache

from spacy.matcher import Matcher
from spacy.tokens import Token
from spacy.vocab import Vocab

from corpus_structure.ingest.annotation_views import AnnotationView

from .predicate_frames import FrameCue, LocatedFrameSpan, PredicateFrameResult

_SYMBOL = object()


@lru_cache(maxsize=4)
def _qualifier_patterns(vocab: Vocab) -> Matcher:
    matcher = Matcher(vocab, validate=True)
    for name, words in (
        (
            "variance",
            (
                "let",
                _SYMBOL,
                "and",
                _SYMBOL,
                "be",
                "random",
                "variables",
                "with",
                "positive",
                "variance",
                ".",
            ),
        ),
        (
            "correlation",
            ("the", "correlation", "of", _SYMBOL, "and", _SYMBOL, "is", "defined", "as"),
        ),
        (
            "parameters",
            ("with", "parameters", _SYMBOL, "and", _SYMBOL, "is", "defined", "as", "follows", ":"),
        ),
        (
            "population",
            (
                "counting",
                "the",
                "waiting",
                "time",
                "of",
                "all",
                "customers",
                ",",
                "even",
                "those",
                "that",
                "do",
                "not",
                "have",
                "to",
                "wait",
                "at",
                "all",
            ),
        ),
    ):
        matcher.add(
            name,
            [
                [
                    {"IS_ALPHA": True, "LENGTH": 1} if word is _SYMBOL else {"LOWER": word}
                    for word in words
                ]
            ],
        )
    return matcher


def _arc(child: Token, parent: Token, dependency: str) -> bool:
    return child.head.i == parent.i and child.dep_ == dependency


def _one_piece(view: AnnotationView, start: int, end: int) -> bool:
    rows = view.product.tokens[start:end]
    if not rows:
        return False
    piece = rows[0].piece_indices
    return len(piece) == 1 and all(row.piece_indices == piece for row in rows)


def _unquoted_sentence(view: AnnotationView, start: int, end: int) -> bool:
    rows = view.product.tokens
    sentence = rows[start].sentence
    return (
        sentence is not None
        and rows[end - 1].sentence == sentence
        and not any(token.is_quote for token in view.doc[start].sent)
    )


def _span(view: AnnotationView, start: int, end: int) -> LocatedFrameSpan:
    rows = view.product.tokens
    indices = tuple(token.i for token in view.doc[start:end] if not token.is_space)
    return LocatedFrameSpan(indices, ((rows[indices[0]].start, rows[indices[-1]].end),))


def _cue(
    view: AnnotationView,
    kind: str,
    variant: str,
    start: int,
    end: int,
    marker: int,
    origin: int,
    component: int,
    host: int | None,
) -> FrameCue:
    return FrameCue(
        view.product.block_id,
        view.product.dependency_digest,
        kind,
        variant,
        _span(view, start, end),
        _span(view, marker, marker + 1),
        "located" if host is not None else "unresolved",
        () if host is None else (host,),
        origin,
        component,
    )


def _compound_event(view: AnnotationView, candidate: FrameCue) -> FrameCue | None:
    """Resolve the provisional inner host only when 'then' owns the main predicate."""
    if candidate.variant != "compound_if_then" or len(candidate.hosts) != 2:
        return None
    doc = view.doc
    marker = doc[candidate.basis.tokens[0]]
    if candidate.origin is None or candidate.component is None:
        return None
    first, second = doc[candidate.component], doc[candidate.origin]
    main = second.head
    end = candidate.span.tokens[-1] + 1
    if not marker.i + 2 <= first.i < second.i - 2 < end - 1 < main.i - 1:
        return None
    comma, then = doc[end : end + 2]
    conjunction, second_subject = doc[second.i - 2 : second.i]
    prefix = doc[marker.sent.start : marker.i]
    declared_prefix = len(prefix) == 2 and prefix[0].lower_ == "definition" and prefix[1].like_num
    if (
        marker.lower_ != "if"
        or (len(prefix) and not declared_prefix)
        or main.i not in candidate.hosts
        or second.i not in candidate.hosts
        or main.dep_ != "ROOT"
        or first.lemma_ != "be"
        or second.lemma_ != "be"
        or comma.text != ","
        or then.lower_ != "then"
        or conjunction.lower_ != "and"
        or conjunction.dep_ != "cc"
        or not _arc(marker, first, "mark")
        or not _arc(doc[marker.i + 1], first, "nsubj")
        or not _arc(first, second, "advcl")
        or not _arc(second, main, "ccomp")
        or not _arc(then, main, "advmod")
        or sum(t.lower_ == "then" for t in marker.sent) != 1
        or sum(t.lower_ == "and" and t.dep_ == "cc" for t in doc[first.i + 1 : second.i]) != 1
        or doc[marker.i + 1].text == second_subject.text
        or not _one_piece(view, marker.i, main.i + 1)
        or not _unquoted_sentence(view, marker.i, main.i + 1)
    ):
        return None
    attribute = _arc(conjunction.head, first, "attr")
    if not (
        (
            _arc(second_subject, second, "nsubj")
            and (attribute or conjunction.head in (first, second))
        )
        or (attribute and _arc(second_subject, conjunction.head, "conj"))
    ):
        return None
    return _cue(
        view, "condition", "event_compound_then", marker.i, end, marker.i, main.i, second.i, main.i
    )


def _variance(view: AnnotationView, start: int, end: int, hosts: set[int]) -> FrameCue | None:
    doc = view.doc
    let, a, and_, b, be, _, variables, with_, positive, variance, _ = doc[start:end]
    prefix = doc[let.sent.start : let.i]
    if (
        view.product.kind != "list_item"
        or (len(prefix) and not (len(prefix) == 1 and prefix[0].text.rstrip(".").isdigit()))
        or a.text == b.text
        or let.dep_ != "ROOT"
        or not _unquoted_sentence(view, start, end)
        or not _one_piece(view, start, end)
        or not all(
            (
                _arc(be, let, "ccomp"),
                _arc(a, be, "nsubj"),
                _arc(and_, a, "cc"),
                _arc(b, a, "conj"),
                _arc(variables, be, "attr"),
                _arc(with_, variables, "prep"),
                _arc(variance, with_, "pobj"),
                _arc(positive, variance, "amod"),
            )
        )
    ):
        return None
    host = end + 7 if end + 7 in hosts else None
    return _cue(
        view, "assumption", "adjacent_variance_premise", start, end - 1, start, start, be.i, host
    )


def _correlation_hosts(view: AnnotationView, pairs: dict[int, int]) -> set[int]:
    doc = view.doc
    hosts = set()
    for start, end in pairs.items():
        article, correlation, of, a, and_, b, is_, defined, _ = doc[start:end]
        if start < 11:
            continue
        previous = doc[start - 11]
        if (
            previous.lower_ == "let"
            and article.is_sent_start
            and doc[start - 1].sent.end == article.i
            and (a.text, b.text) == (doc[start - 10].text, doc[start - 8].text)
            and _one_piece(view, start - 11, end)
            and _unquoted_sentence(view, start, end)
            and defined.dep_ == "ROOT"
            and all(
                (
                    _arc(correlation, defined, "nsubjpass"),
                    _arc(of, correlation, "prep"),
                    _arc(a, of, "pobj"),
                    _arc(and_, a, "cc"),
                    _arc(b, a, "conj"),
                    _arc(is_, defined, "auxpass"),
                )
            )
        ):
            hosts.add(defined.i)
    return hosts


def _parameter_pair(view: AnnotationView, start: int, end: int) -> FrameCue | None:
    doc = view.doc
    with_, parameters, a, and_, b, is_, defined, as_, follows, colon = doc[start:end]
    if (
        not start
        or a.text == b.text
        or not _one_piece(view, start - 1, end)
        or not _unquoted_sentence(view, start - 1, end)
    ):
        return None
    nominal = doc[start - 1]
    shared = (
        nominal.pos_ in {"NOUN", "PROPN"}
        and _arc(with_, nominal, "prep")
        and _arc(is_, defined, "auxpass")
        and _arc(as_, follows, "mark")
        and _arc(follows, defined, "advcl")
        and _arc(colon, defined, "punct")
    )
    split_subject = (
        nominal.dep_ == "ROOT"
        and _arc(parameters, a, "compound")
        and _arc(a, with_, "pobj")
        and _arc(and_, nominal, "cc")
        and _arc(b, defined, "nsubjpass")
        and _arc(defined, nominal, "conj")
    )
    attached_nominal = (
        defined.dep_ == "ROOT"
        and _arc(nominal, defined, "nsubjpass")
        and _arc(parameters, with_, "pobj")
        and _arc(a, parameters, "appos")
        and _arc(and_, a, "cc")
        and _arc(b, a, "conj")
    )
    host = defined.i if shared and (split_subject or attached_nominal) else None
    return _cue(
        view,
        "parameterization",
        "nominal_parameter_pair",
        start,
        start + 5,
        start,
        defined.i,
        nominal.i,
        host,
    )


def _population(view: AnnotationView, start: int, end: int) -> FrameCue | None:
    doc = view.doc
    (
        counting,
        _,
        _,
        time,
        of,
        all_,
        customers,
        _,
        even,
        those,
        that,
        do,
        not_,
        have,
        to,
        wait,
        _,
        _,
    ) = doc[start:end]
    if not _one_piece(view, start, end) or not _unquoted_sentence(view, start, end):
        return None
    ending = doc[end : counting.sent.end]
    attached = (
        (not len(ending) or (len(ending) == 1 and ending[0].text == "."))
        and those.dep_ == "appos"
        and (those.head in (customers, time) or _arc(those.head, counting, "nsubj"))
        and all(
            (
                _arc(time, counting, "dobj"),
                _arc(of, time, "prep"),
                _arc(all_, customers, "det"),
                _arc(customers, of, "pobj"),
                _arc(even, those, "advmod"),
                _arc(that, have, "nsubj"),
                _arc(do, have, "aux"),
                _arc(not_, have, "neg"),
                _arc(have, those, "relcl"),
                _arc(to, wait, "aux"),
                _arc(wait, have, "xcomp"),
            )
        )
    )
    return _cue(
        view,
        "population_inclusion",
        "customer_population_inclusion",
        even.i,
        end,
        even.i,
        counting.i,
        customers.i,
        counting.i if attached else None,
    )


def local_qualifier_result(
    view: AnnotationView, result: PredicateFrameResult
) -> PredicateFrameResult:
    """Extend a base frame result while leaving its replay recipe unchanged."""
    if not result.frames:
        return result
    view.check_layout()
    doc = view.doc
    frames = {frame.predicate.tokens[0] for frame in result.frames}
    found: dict[str, dict[int, int]] = {}
    for match, start, end in _qualifier_patterns(doc.vocab)(doc):
        found.setdefault(doc.vocab.strings[match], {})[start] = end
    correlations = _correlation_hosts(view, found.get("correlation", {}))
    candidates = [
        *(
            _variance(view, start, end, correlations)
            for start, end in found.get("variance", {}).items()
        ),
        *(_parameter_pair(view, start, end) for start, end in found.get("parameters", {}).items()),
        *(_population(view, start, end) for start, end in found.get("population", {}).items()),
    ]
    resolved = {}
    for cue in dict.fromkeys(cue for frame in result.frames for cue in frame.cues):
        replacement = _compound_event(view, cue)
        if replacement is not None and replacement.hosts[0] in frames:
            resolved[cue] = replacement
    if not resolved and not any(candidates):
        return result
    assigned: dict[int, list[FrameCue]] = {}
    unresolved = list(result.unresolved_cues)
    for cue in (*resolved.values(), *candidates):
        if cue is None:
            continue
        if cue.hosts and cue.hosts[0] in frames:
            assigned.setdefault(cue.hosts[0], []).append(cue)
        else:
            unresolved.append(replace(cue, hosts=(), status="unresolved"))
    return replace(
        result,
        frames=tuple(
            replace(
                frame,
                cues=tuple(cue for cue in frame.cues if cue not in resolved)
                + tuple(assigned.get(frame.predicate.tokens[0], ())),
            )
            for frame in result.frames
        ),
        unresolved_cues=tuple(unresolved),
    )
