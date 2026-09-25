"""Named, version-bound processing completion for the three editable panes."""
from copy import deepcopy
from datetime import datetime
import re
import uuid

from backend.shared.identities import named
from backend.shared.records import now
from backend.system3.requirements import Requirements, leaves, RELATIONS
from backend.system3.interpretations import Interpretations, KEYS, CARD_FIELDS, review_ready
from backend.system3.check_design import concept_issues, logic_fields
from local_workbench.collaboration import fingerprint


STAGES = ('content', 'requirements', 'interpretation')


def validate_confirmation(record):
    if not isinstance(record, dict) or set(record) != {'id', 'material_id', 'stage', 'signature', 'complete', 'actor', 'at'}:
        raise ValueError('Invalid processing confirmation record.')
    if (str(uuid.UUID(record['id'])) != record['id'] or record['stage'] not in STAGES
            or type(record['complete']) is not bool or not re.fullmatch('[a-f0-9]{64}', record['signature'])
            or not isinstance(record['material_id'], str) or not record['material_id']):
        raise ValueError('Invalid processing confirmation identity or signature.')
    named(record['actor'])
    if datetime.fromisoformat(record['at']).tzinfo is None:
        raise ValueError('Processing confirmation needs an explicit timestamp timezone.')


def progress_version(stages):
    return fingerprint([stages[s]['confirmation']['id'] if stages[s]['confirmation'] else None for s in STAGES])


class MaterialProgress:
    def __init__(self, collaboration):
        self.c = collaboration

    def inspect(self, actor, material_id, view='personal', revision=None):
        actor = named(actor)
        with self.c.lock:
            if view == 'archive':
                from local_workbench.material_queue import MaterialQueue
                archived = MaterialQueue(self.c).read_archive(actor, material_id, revision)
                record = self.c.get('material_archive_progress', material_id + ':' + str(archived['revision']))
                if record:
                    return dict(record['progress'], historical=True, revision=archived['revision'])
                # An older archive has no declarations under this newer workflow.
                return dict(material_id=material_id, revision=archived['revision'], historical=True,
                            completed=0, archive_ready=False, stages={s: dict(complete=False, confirmation=None,
                            problems=['This historical archive predates the three-stage processing declarations.']) for s in STAGES})
            if view not in ('personal', 'master'):
                raise ValueError('Unknown processing progress view.')
            material = self.c.read_material(actor, material_id, view=view)
            requirements = Requirements(self.c)
            with self.c.db() as db:
                sessions = [requirements.load(db, actor, s['id']) for s in requirements.listing(actor, material_id)['sessions']]
            for session in sessions:
                session['stale'] = requirements.stale(session, material)
            signatures = {}
            problems = {key: [] for key in STAGES}
            if (not material.get('blocks') or material.get('source_stale') or material.get('source_check_error')
                    or material.get('source_issues') or any(not i.get('resolved') for i in material.get('issues', []))):
                problems['content'].append('Review the content and resolve source or content issues.')
            if (set(material.get('checked_scope', [])) != {s['id'] for s in material['scope']}
                    or material.get('association_review_required', True)):
                problems['content'].append('Check every original range and the structural associations, then Save.')
            if any(c['status'] in ('running', 'ready', 'partial') for c in material.get('candidates', [])):
                problems['content'].append('Resolve the pending extraction candidates.')
            signatures['content'] = fingerprint({k: material.get(k) for k in
                ('source', 'scope', 'blocks', 'issues', 'checked_scope', 'association_review_required')})
            for session in sessions:
                if session.get('stale'):
                    problems['requirements'].append('A Requirement entry refers to changed source content.')
                    continue
                proposed = deepcopy(session)
                proposed['phase'] = 'fields'
                try:
                    with self.c.db() as db:
                        for identity in proposed['units']:
                            requirements.edit(db, actor, proposed, {'action': 'done', 'unit_id': identity})
                        requirements.validate(db, actor, proposed)
                except ValueError as error:
                    problems['requirements'].append(str(error))
            signatures['requirements'] = fingerprint([signatures['content'], [(s['id'], s['revision']) for s in sessions]])
            interpretations = Interpretations(self.c)
            documents = []
            bound_material = material if view == 'personal' else self.c.read_material(actor, material_id)
            if any(bound_material.get(k) != material.get(k) for k in ('source', 'blocks', 'issues')):
                problems['interpretation'].append('The saved interpretation context differs from the master material. Reconcile the source content first.')
            materials = {material_id: bound_material}
            for session in sessions:
                children = {i for u in session['units'].values() for field in RELATIONS for i in leaves(u.get(field))}
                roots = leaves(session['roots']) if session.get('roots') else [i for i in session['units'] if i not in children]
                for identity in roots:
                    try:
                        doc = interpretations._read(actor, identity, _materials=materials)
                        documents.append([identity, doc['revision'], doc.get('context', {}).get('fingerprint'), doc.get('catalog', {}).get('revision')])
                        if (not doc['revision'] or doc.get('stale') or doc.get('context_error')
                                or doc.get('mapping_issues') or concept_issues(doc['check_design'])
                                or not all(doc['card_review_status'].get(k) for k in CARD_FIELDS)
                                or any(not review_ready(logic_fields(doc['fields'], doc['check_design'])[k]) for k in KEYS)):
                            problems['interpretation'].append('Complete and approve all three cards and resolve their review questions for every Requirement.')
                    except ValueError as error:
                        documents.append([identity, 'unavailable'])
                        problems['interpretation'].append(str(error))
            signatures['interpretation'] = fingerprint([signatures['requirements'], documents])
            records = self.c.all('material_progress_confirmation')
            records += [r['value'] for r in self.c.all('sync_shared_record')
                        if r.get('key', '').startswith('history:material_progress_confirmation:')]
            stored = {}
            for record in sorted(records, key=lambda r: (r['at'], r['id'])):
                if record['material_id'] == material_id:
                    stored[record['stage']] = record
            stages = {}
            for stage in STAGES:
                record = stored.get(stage)
                stages[stage] = dict(complete=bool(record and record['complete'] and record['signature'] == signatures[stage] and not problems[stage]),
                                     signature=signatures[stage], problems=list(dict.fromkeys(problems[stage])), confirmation=record)
            return dict(material_id=material_id, revision=material['revision'], stages=stages,
                        version=progress_version(stages),
                        completed=sum(s['complete'] for s in stages.values()), archive_ready=all(s['complete'] for s in stages.values()))

    def confirm(self, actor, request):
        actor = named(actor)
        if set(request) != {'material_id', 'expected_revision', 'expected_progress', 'stage', 'signature', 'request_id', 'complete'}:
            raise ValueError('Use the current page completion controls.')
        if request['stage'] not in STAGES or type(request['complete']) is not bool:
            raise ValueError('Choose a processing stage and explicit completion decision.')
        rid = str(uuid.UUID(request['request_id']))
        with self.c.lock:
            self.c.claim_request('material-progress', rid, fingerprint(request), actor)
            prior = self.c.get('material_progress_receipt', rid)
            if prior:
                return prior
            state = self.inspect(actor, request['material_id'])
            stage = state['stages'][request['stage']]
            if (state['revision'] != request['expected_revision'] or stage['signature'] != request['signature']
                    or state['version'] != request['expected_progress']):
                return dict(status='conflict', error='Saved work changed. Refresh processing progress and review again.')
            if request['complete'] and stage['problems']:
                raise ValueError(' '.join(stage['problems']))
            records = []
            affected = [request['stage']] if request['complete'] else STAGES[STAGES.index(request['stage']):]
            timestamp = now()
            for target in affected:
                identity = rid if target == request['stage'] else str(uuid.uuid5(uuid.UUID(rid), target))
                record = dict(id=identity, material_id=request['material_id'], stage=target,
                              signature=state['stages'][target]['signature'], complete=request['complete'], actor=actor, at=timestamp)
                records.append(('material_progress_confirmation', identity, record))
                state['stages'][target].update(complete=request['complete'], confirmation=record)
            state['completed'] = sum(s['complete'] for s in state['stages'].values())
            state['archive_ready'] = state['completed'] == len(STAGES)
            state['version'] = progress_version(state['stages'])
            response = dict(status='applied', progress=state)
            self.c.put_many([*records, ('material_progress_receipt', rid, response)])
            return response

    def require_complete(self, actor, material_id, view='personal'):
        state = self.inspect(actor, material_id, view)
        if not state['archive_ready']:
            raise ValueError('Confirm completion at the bottom of content, Requirements and interpretation before Archive.')
        return state
