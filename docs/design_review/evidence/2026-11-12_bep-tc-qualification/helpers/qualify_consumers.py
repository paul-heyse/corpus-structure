"""One retained BEP/TC consumer campaign and source-view/family account.

Reuse the prepared BEP verifier, native readers and offline owner. Only an exact
binding is accepted. The additional matrix consumes the saved manifest metadata;
no second layer read, NLP, reference access or result selection occurs.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

from sqlalchemy import BigInteger, Boolean, Text, and_, bindparam, case, cast, column, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.characterization import characterization_profiles
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

EVIDENCE = Path(__file__).resolve().parents[2]
VERIFIER = EVIDENCE / '2026-11-11_bep-whole-book/verify_consumers.py'
spec = spec_from_file_location('bep_retained_consumer_verifier', VERIFIER)
assert spec and spec.loader
verifier = module_from_spec(spec)
spec.loader.exec_module(verifier)

PLACEMENT_LIMITS = dict(
    source_views=316, metadata_row_bytes=1024**2, metadata_total_bytes=16 * 1024**2,
    reference_values=500_000, reference_chars=2048, region_rows=500_000,
    region_wire_bytes=64 * 1024**2, output_bytes=32 * 1024**2,
)


def _projected_native_refs(sources):
    return func.jsonb_path_query_array(
        sources.c.projection, '$.pieces[*] ? (@.kind == "native_text").item_ref',
        type_=JSONB,
    )


def _source_placement_rows(conn, sources, source_ids):
    if len(source_ids) != PLACEMENT_LIMITS['source_views'] or len(set(source_ids)) != len(source_ids):
        raise ValueError('placement context requires exactly316 distinct captured source IDs')
    metadata = func.jsonb_build_object(
        'selected_items', sources.c.projection['items'],
        'native_text_refs', _projected_native_refs(sources),
        'native_text_piece_count', func.jsonb_array_length(func.jsonb_path_query_array(
            sources.c.projection, '$.pieces[*] ? (@.kind == "native_text")', type_=JSONB,
        )), type_=JSONB,
    )
    size = func.octet_length(cast(metadata, Text()))
    total_size = func.sum(size).over()
    # Do not transfer oversized JSON, or the projection's text or full pieces.
    rows = conn.execute(select(
        sources.c.id, sources.c.projection_digest, sources.c.native_build_id,
        sources.c.native_revision_id, sources.c.membership,
        size.label('metadata_bytes'), total_size.label('total_metadata_bytes'),
        case((and_(size <= PLACEMENT_LIMITS['metadata_row_bytes'],
                    total_size <= PLACEMENT_LIMITS['metadata_total_bytes']), metadata),
             else_=None).label('placement_metadata'),
    ).where(sources.c.id.in_(source_ids)).order_by(sources.c.id)
      .limit(PLACEMENT_LIMITS['source_views'] + 1)).mappings().all()
    if {row['id'] for row in rows} != set(source_ids):
        raise ValueError('placement source population differs from the exact captured IDs')
    if any(row['placement_metadata'] is None for row in rows):
        raise ValueError('placement metadata exceeds explicit byte bounds; nothing was truncated')
    return rows


def page_source_view_context(conn, source_rows, facts):
    """Observed native placements, independently of NLP selection/examination."""
    views, reference_values = {}, 0
    for row in source_rows:
        metadata = row['placement_metadata']
        items, text_refs = metadata['selected_items'], metadata['native_text_refs']
        if not isinstance(items, list) or not isinstance(text_refs, list):
            raise ValueError('native placement metadata requires item/ref arrays')
        reference_values += len(items) + len(text_refs)
        if reference_values > PLACEMENT_LIMITS['reference_values']:
            raise ValueError('placement reference bound exceeded; nothing was truncated')
        valid_items = {ref for ref in items if isinstance(ref, str) and ref}
        valid_text = {ref for ref in text_refs if isinstance(ref, str) and ref}
        if any(len(ref) > PLACEMENT_LIMITS['reference_chars'] for ref in valid_items | valid_text):
            raise ValueError('native reference exceeds placement character bound')
        views[row['id']] = dict(
            source_view_id=row['id'], projection_digest=row['projection_digest'],
            native_build_id=row['native_build_id'], native_revision_id=row['native_revision_id'],
            membership=row['membership'], selected_item_refs=valid_items,
            projected_native_text_refs=valid_text, located_item_refs=set(), located_text_refs=set(),
            selected_native_pages=set(), projected_native_text_pages=set(),
            selected_item_ref_values=len(items), selected_unique_item_refs=len(valid_items),
            missing_selected_item_ref_values=sum(not isinstance(ref, str) or not ref for ref in items),
            projected_native_text_piece_count=metadata['native_text_piece_count'],
            missing_native_text_piece_item_refs=(metadata['native_text_piece_count'] - len(text_refs)
                + sum(not isinstance(ref, str) or not ref for ref in text_refs)),
            projected_text_refs_outside_selected_items=sorted(valid_text - valid_items),
        )
    regions = table('kb.pdf_record_region')
    # The already bounded metadata supplies exact pointer keys before the region
    # join. One typed JSONB parameter avoids per-pointer bind parameters and any
    # view-by-document-region scan or repeated projection/piece interpretation.
    reference_rows = [
        dict(source_view_id=identity, product_id=view['native_build_id'],
             revision_id=view['native_revision_id'], pointer=pointer,
             selected_item=pointer in view['selected_item_refs'],
             projected_native_text=pointer in view['projected_native_text_refs'])
        for identity, view in sorted(views.items())
        for pointer in sorted(view['selected_item_refs'] | view['projected_native_text_refs'])
    ]
    selected = func.jsonb_to_recordset(bindparam('placement_refs', type_=JSONB)).table_valued(
        column('source_view_id', BigInteger()), column('product_id', Text()),
        column('revision_id', Text()), column('pointer', Text()),
        column('selected_item', Boolean()), column('projected_native_text', Boolean()),
    ).render_derived(name='selected_pointers', with_types=True)
    parameters = dict(placement_refs=reference_rows)
    placement = select(
        selected.c.source_view_id, regions.c.pointer, regions.c.region_index,
        regions.c.page_no, selected.c.selected_item, selected.c.projected_native_text,
    ).select_from(selected.join(regions, and_(
        regions.c.product_id == selected.c.product_id,
        regions.c.revision_id == selected.c.revision_id,
        regions.c.pointer == selected.c.pointer,
    )))
    bounded = placement.subquery()
    count, wire_bytes = conn.execute(select(
        func.count(), func.coalesce(func.sum(func.octet_length(bounded.c.pointer) + 96), 0),
    ).select_from(bounded), parameters).one()
    if count > PLACEMENT_LIMITS['region_rows'] or wire_bytes > PLACEMENT_LIMITS['region_wire_bytes']:
        raise ValueError('native placement rows/bytes exceed bounds; nothing was truncated')
    page_views = defaultdict(lambda: dict(selected=set(), projected=set(), selected_regions=0, projected_regions=0))
    rows = conn.execute(placement.order_by(selected.c.source_view_id, regions.c.pointer, regions.c.region_index)
                        .limit(PLACEMENT_LIMITS['region_rows'] + 1), parameters).mappings()
    seen = 0
    for row in rows:
        seen += 1
        if seen > PLACEMENT_LIMITS['region_rows']:
            raise ValueError('native placement row bound exceeded; nothing was truncated')
        view, page = views[row['source_view_id']], row['page_no']
        for flag, refs, pages, page_key, count_key in (
            ('selected_item', 'located_item_refs', 'selected_native_pages', 'selected', 'selected_regions'),
            ('projected_native_text', 'located_text_refs', 'projected_native_text_pages', 'projected', 'projected_regions'),
        ):
            if row[flag]:
                view[refs].add(row['pointer'])
                view[pages].add(page)
                page_views[page][page_key].add(row['source_view_id'])
                page_views[page][count_key] += 1
    if seen != count:
        raise ValueError('native placement inventory changed during its bounded read')
    health = facts['original_native_health']
    start, end = health.get('page_start'), health.get('page_end')
    exact_range = (type(start) is int and type(end) is int and end >= start
                   and end - start + 1 == facts['binding']['native_pages'] == 518)
    health_pages = set(range(start, end + 1)) if exact_range else set()

    def page_row(page):
        entry = page_views[page]
        return dict(page_no=page, selected_native_occurrence_source_view_ids=sorted(entry['selected']),
                    projected_native_text_pointer_placement_source_view_ids=sorted(entry['projected']),
                    selected_native_region_rows=entry['selected_regions'],
                    projected_native_text_region_rows=entry['projected_regions'])

    by_view = []
    for identity, view in sorted(views.items()):
        selected_refs, text_refs = view.pop('selected_item_refs'), view.pop('projected_native_text_refs')
        view['unlocated_selected_item_refs'] = sorted(selected_refs - view.pop('located_item_refs'))
        view['unlocated_projected_native_text_refs'] = sorted(text_refs - view.pop('located_text_refs'))
        view['selected_native_pages'] = sorted(view['selected_native_pages'])
        view['projected_native_text_pointer_placement_pages'] = sorted(view.pop('projected_native_text_pages'))
        by_view.append(view)
    context = dict(
        binding=facts['binding'], availability='available' if exact_range else 'unavailable_health_page_range',
        health_page_start=start, health_page_end=end, expected_health_pages=facts['binding']['native_pages'],
        page_numbering='Exact stored page_no matched to health page_start..page_end; no offset conversion.',
        placement_authority=dict(
            sources='kb.source_view', regions='kb.pdf_record_region',
            join='native_build_id=product_id AND native_revision_id=revision_id AND exact pointer',
            selected_native_occurrences='projection.items references',
            projected_native_text='projection.pieces item_ref where kind=native_text',
        ),
        projected_native_text_placement_basis='Native-pointer regions only; shared, table or multipage pointers do not locate individual projected characters on those pages.',
        family_account=dict(path='source-view-family-account.jsonl', source_view_key='source_view_id', family_key='family'),
        source_view_count=len(views), native_region_rows=seen, metadata_reference_values=reference_values,
        health_pages_with_selected_native_placements=sum(bool(page_views[p]['selected']) for p in health_pages),
        health_pages_with_projected_native_text_pointer_placements=sum(bool(page_views[p]['projected']) for p in health_pages),
        pages=[page_row(page) for page in sorted(health_pages)],
        placements_outside_health_range=[page_row(page) for page in sorted(page_views.keys() - health_pages)],
        source_views=by_view, limits=PLACEMENT_LIMITS,
        interpretation_limits=[
            'No native placements is not evidence of a blank or semantically empty page.',
            'Native locations do not establish recognition or projected-text completeness.',
            'A selected native occurrence without projected native text is not examined NLP input.',
            'View membership is direct/descendants, not page membership or per-page family completeness.',
            'Family examination remains attributed by the separate exact view/projection selectors.',
            'Unlocated refs can be structural items without their own regions; no descendant placement is inferred.',
        ],
    )
    if len(verifier.canonical_bytes(context)) > PLACEMENT_LIMITS['output_bytes']:
        raise ValueError('page/source-view context exceeds output bound; nothing was truncated')
    return context


def family_account(root):
    facts = json.loads((root / 'native-facts.json').read_bytes())
    manifests = json.loads((root / 'active-layer-manifests.json').read_bytes())
    bound = facts['binding']
    sources = table('kb.source_view')
    with open_runtime_engine(Settings(), 'bep-tc-family-account', purpose='read') as engine, read_snapshot(engine) as conn:
        source_rows = _source_placement_rows(conn, sources, facts['source_view_ids'])
        rows = [(row['id'], row['projection_digest']) for row in source_rows]
        projections = dict(rows)
        page_context = page_source_view_context(conn, source_rows, facts)
        required = set(characterization_profiles(open_release(conn, facts['release_id']))['full_characterization'])
    owners = defaultdict(set)
    for identity, digest in rows:
        owners[digest].add(identity)
    scopes = defaultdict(list)
    observed = set()
    for manifest in manifests:
        declared = set(manifest['source_view_ids'])
        if not declared <= projections.keys():
            raise ValueError('manifest scope escapes captured source population')
        for coverage in manifest['coverage']:
            family = coverage['family']
            observed.add(family)
            for field in ('eligible', 'examined', 'unexamined'):
                for selector in coverage.get(field, []):
                    if len(owners[selector['projection']] & declared) != 1:
                        raise ValueError('coverage selector has no unique captured projection owner')
            for identity in declared:
                scopes[identity, family].append(dict(
                    layer=manifest['reference'], operation=manifest['operation'],
                    outcome=coverage['outcome'], availability=coverage['availability'],
                    reason=coverage.get('reason'),
                    **{field: [s for s in coverage.get(field, []) if s['projection'] == projections[identity]] for field in ('eligible', 'examined', 'unexamined')},
                ))
    totals = Counter()
    missing, incomplete = [], []
    # This is deliberately a retained report artifact, not a CLI scratch export.
    path = root / 'account/raw/source-view-family-account.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        for identity in sorted(projections):
            for family in sorted(required | observed):
                records = scopes[identity, family]
                attributed = [r for r in records if any(r[f] for f in ('eligible', 'examined', 'unexamined'))]
                state = ('not_recorded' if family in required else 'not_selected_for_view') if not records else 'declared_without_attributed_selectors' if not attributed else 'complete_or_empty' if all(r['outcome'] in {'complete', 'empty'} for r in attributed) else 'incomplete'
                row = dict(source_view_id=identity, family=family, required_family=family in required, state=state, operations=records)
                stream.write(verifier.canonical_bytes(row) + b'\n')
                totals[state] += 1
                if family in required and not records:
                    missing.append(dict(source_view_id=identity, family=family))
                elif family in required and state != 'complete_or_empty':
                    incomplete.append(dict(source_view_id=identity, family=family, state=state))
    verifier.write(root, 'primary-coverage.json', dict(
        binding=bound, required_families=sorted(required), observed_families=sorted(observed),
        required_scope_pairs=316 * len(required), scope_states=dict(totals),
        missing_scope_pairs=missing, incomplete_scope_pairs=incomplete,
        original_native_health=facts['original_native_health'],
        page_placement_context='account/raw/page-source-view-placement.json',
        outcome='passed' if not missing and not incomplete else 'partial',
        limit='Execution attribution only. Grammar-relative examined empty is not unrestricted absence or semantic correctness; inherited source limits remain.',
    ))
    verifier.write(root, 'account/raw/page-source-view-placement.json', page_context)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'live', 'replay'))
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--export-max-bytes', type=int, default=8 * 1024**3)
    parser.add_argument('--max-coverage-pages', type=int, default=1000)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--request-name', action='append')
    args = parser.parse_args()
    bound, pin = verifier.binding(args.binding)
    if args.action == 'prepare':
        verifier.prepare(Settings(), bound, pin, args.output, args.export_max_bytes)
        family_account(args.output)
        return True
    if args.action == 'live':
        return asyncio.run(verifier.live(Settings(), bound, args.output, args.max_coverage_pages))
    if not args.bundle or not args.manifest_sha256:
        parser.error('replay requires bundle and independently retained manifest digest')
    return verifier.replay(bound, args.output, args.bundle, args.manifest_sha256, args.request_name)


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
