"""Versioned dormant boundary; no semantic fields or processor are invented."""
from __future__ import annotations

from copy import deepcopy

from ..contracts.hashing import digest

CONTRACT_VERSION = 'material-processor/1'
SOURCE_IDENTITY = ('source_id', 'snapshot_id', 'content_hash')


def input_hash(material_id, source, revision, scope, blocks):
    """Bind content, ordered dependencies and the requested original range."""
    return digest({'material_id':material_id, 'source':{key:source[key] for key in SOURCE_IDENTITY},
                   'input_revision':revision, 'scope':sorted(scope), 'blocks':blocks})


def capability():
    return {'contract_version': CONTRACT_VERSION, 'connected': False, 'state': 'unavailable',
            'operations': [], 'schema_versions': [], 'reason': 'Requirement structure and processor pending'}


def input_envelope(material, *, request_id, scope_ids=None, schema_version=None):
    """Future adapter input can use only explicitly human-confirmed dependency closure."""
    confirmation = material.get('confirmation')
    if not confirmation or confirmation['content_revision'] != material['content_revision'] or material.get('source_stale'):
        raise ValueError('confirmed_current_content_required')
    selected = set(scope_ids if scope_ids is not None else [s['id'] for s in material['scope']])
    checked = set(confirmation['checked_scope'])
    if not selected or not selected <= checked:
        raise ValueError('confirmed_scope_required')
    by_id = {b['id']: b for b in material['blocks']}
    ids = {b['id'] for b in material['blocks'] if any(r['scope_id'] in selected for r in b['source_refs'])}
    pending = list(ids)
    while pending:
        block = by_id[pending.pop()]
        for dep in [*block.get('dependencies', []), *([block['parent_id']] if block.get('parent_id') else [])]:
            if dep not in by_id:
                raise ValueError('unresolved_dependency')
            if not all(r['scope_id'] in checked for r in by_id[dep]['source_refs']):
                raise ValueError('dependency_scope_not_confirmed')
            if dep not in ids:
                ids.add(dep)
                pending.append(dep)
    blocks = deepcopy([b for b in material['blocks'] if b['id'] in ids])
    return {'contract_version': CONTRACT_VERSION, 'request_id': request_id, 'material_id': material['id'],
            'source': deepcopy(material['source']), 'input_revision': material['content_revision'],
            'confirmed_by': confirmation['actor'], 'scope': sorted(selected), 'blocks': blocks,
            'input_hash': input_hash(material['id'],material['source'],material['content_revision'],selected,blocks),
            'requested_schema_version': schema_version,
            'human_adoption_required': True}


def process(envelope):
    """A real request returns unavailable, never a fabricated successful candidate."""
    return {'contract_version': CONTRACT_VERSION, 'state': 'unavailable',
            'request_id': envelope.get('request_id'), 'input_revision': envelope.get('input_revision'),
            'material_id': envelope['material_id'], 'source': deepcopy(envelope['source']),
            'input_hash': envelope['input_hash'], 'scope': deepcopy(envelope.get('scope',[])),
            'processor_version': None, 'schema_version': None, 'candidate_payload': None,
            'evidence_mappings': [], 'warnings': [], 'unresolved_coverage': envelope.get('scope', []),
            'error': capability()['reason'], 'human_adoption_required': True}


def validate_output(envelope, output):
    """Generic future output/adoption guards preserve unknown payloads verbatim."""
    if output.get('contract_version') != CONTRACT_VERSION:
        raise ValueError('unsupported_processor_contract')
    identity_keys = ('request_id','material_id','input_revision','input_hash')
    if (any(key not in envelope or key not in output or output[key] != envelope[key] for key in identity_keys)
            or not envelope.get('material_id') or not envelope.get('input_hash')
            or not isinstance(envelope.get('source'),dict) or not isinstance(output.get('source'),dict)
            or any(not envelope.get('source',{}).get(key)
                   or output.get('source',{}).get(key) != envelope['source'][key] for key in SOURCE_IDENTITY)
            or output.get('scope') != envelope.get('scope')):
        raise ValueError('processor_input_identity_mismatch')
    if output.get('state') not in ('empty', 'partial', 'failed', 'unavailable', 'candidate'):
        raise ValueError('invalid_processor_state')
    if output.get('human_adoption_required') is not True or output.get('human_confirmed'):
        raise ValueError('processor_cannot_confirm_human_values')
    return output
