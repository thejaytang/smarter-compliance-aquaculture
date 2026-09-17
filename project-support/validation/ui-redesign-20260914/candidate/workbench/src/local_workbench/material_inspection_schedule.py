"""Opt-in coordinator weekly inspection dispatch; never called by navigation.

The owning collaboration journal retains frozen batches and task receipts.
Nothing changes the System2 archive or enables a schedule by importing this module.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import uuid
from zoneinfo import ZoneInfo

from .collaboration import COORDINATOR, named
from .material_queue import MaterialQueue
from .platform_support import exclusive_lock


class MaterialInspectionSchedule:
    def __init__(self, collaboration):
        self.c = collaboration
        self.queue = MaterialQueue(collaboration)

    def run_due(self, settings=None, clock=None):
        settings = settings or {}
        if settings.get('enabled') is not True:
            return {'status': 'disabled', 'enabled': False}
        self.c.coordinator(COORDINATOR)
        if set(settings) - {'enabled', 'timezone', 'sample_size', 'assignee'}:
            raise ValueError('Unsupported material inspection schedule settings.')
        count = settings.get('sample_size')
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError('Configure an explicit weekly sample size from 1 to 100.')
        zone = ZoneInfo(settings['timezone'])
        assignee = named(settings['assignee'])
        instant = clock() if clock else datetime.now(timezone.utc)
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            raise ValueError('The inspection clock must return a timezone-aware datetime.')
        local = instant.astimezone(zone)
        year, week, _ = local.isocalendar()
        batch_id = f'material-weekly-{year}-W{week:02}'
        # One owner dispatch at a time, including separate service instances.
        with exclusive_lock(self.c.root / 'material-inspection-schedule.lock'), self.c.lock:
            batch = self.c.get('material_inspection_batch', batch_id)
            if batch and batch['status'] == 'complete':
                return deepcopy(batch)
            if not batch:
                archives = self.queue.archives()
                ranked = sorted(archives.values(), key=lambda m: sha256((batch_id + ':' + m['id']).encode()).hexdigest())
                selected = ranked[:count]
                batch = {'id': batch_id, 'status': 'dispatching', 'at': instant.isoformat(),
                    'timezone': settings['timezone'], 'iso_week': f'{year}-W{week:02}',
                    'requested_count': count, 'eligible_count': len(ranked),
                    'selection': 'Deterministic weekly hash order over latest confirmed archives; full retained original scope.',
                    'assignee': assignee, 'items': [
                        {'material_id': m['id'], 'archive_revision': m['revision'],
                         'request_id': str(uuid.uuid5(uuid.NAMESPACE_URL, batch_id + ':' + m['id'])),
                         'status': 'pending'} for m in selected]}
                # Freeze selection before dispatch so crashes cannot substitute versions.
                self.c.put('material_inspection_batch', batch_id, batch)
            for item in batch['items']:
                if item['status'] != 'pending':
                    continue
                receipt = self.c.get('inspection_receipt', item['request_id'])
                if receipt:
                    item.update(status='created', task_id=receipt['inspection']['id'])
                else:
                    archive = self.queue.archives().get(item['material_id'])
                    if not archive or archive['revision'] != item['archive_revision']:
                        item.update(status='skipped', reason='The frozen archived revision is no longer the latest archive.')
                    else:
                        existing = next((t for t in self.queue.tasks(item['material_id'])
                            if t['archive_revision'] == item['archive_revision'] and t['status'] in ('pending', 'finding_open')), None)
                        if existing:
                            item.update(status='already_pending', task_id=existing['id'])
                        else:
                            material = self.c.app.system2.call('material_read', material_id=item['material_id'], revision=item['archive_revision'])
                            scope = [s['id'] for s in material.get('scope', [])]
                            if not scope:
                                item.update(status='skipped', reason='The confirmed archive has no retained original scope.')
                            else:
                                receipt = self.queue.create(COORDINATOR, {
                                    'request_id': item['request_id'], 'material_id': item['material_id'],
                                    'archive_revision': item['archive_revision'], 'scope': scope,
                                    'assignee': batch['assignee'], 'reason': f'Weekly archive inspection {batch["iso_week"]}.'})
                                item.update(status='created', task_id=receipt['inspection']['id'])
                self.c.put('material_inspection_batch', batch_id, batch)
            batch['status'] = 'complete'
            batch['completed_at'] = instant.isoformat()
            batch['selected_count'] = len(batch['items'])
            self.c.put('material_inspection_batch', batch_id, batch)
            return deepcopy(batch)
