"""One-way, replaceable Excel snapshots of committed source-governance state."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from .governance_store import GovernanceStore, authority_version
from .workbook_guard import excel_appears_open, exclusive_process_lock

SCHEMA = 'system1-source-export/1'
RENDER_VERSION = 5


def paths(config):
    database = config['governance_db']
    return database.with_suffix('.excel.json'), database.with_suffix('.excel-worker.json')


def load(path):
    try: return json.loads(path.read_text())
    except (OSError, ValueError): return {}


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd,'w') as handle:
            json.dump(value,handle);handle.flush();os.fsync(handle.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def status(config):
    marker, worker_path = paths(config)
    meta = load(marker); worker = load(worker_path)
    version = authority_version(config)
    current = meta.get('authority_version') == version and meta.get('schema') == SCHEMA and meta.get('render_version') == RENDER_VERSION and config['workbook'].is_file()
    state = 'current' if current else 'pending'
    if worker.get('status') == 'failed': state = 'failed'
    elif worker.get('status') == 'refreshing': state = 'refreshing'
    return {'status':state,'decisions':'saved','saved_revision':version['revision'],
            'exported_revision':meta.get('revision'),'authority_version':version,
            'exported_authority_version':meta.get('authority_version'),
            'sha256':meta.get('sha256'),'message':worker.get('message','')}


def cached(config):
    marker, _ = paths(config)
    raw = marker.read_bytes();meta = json.loads(raw);data = config['workbook'].read_bytes()
    if sha256(data).hexdigest()!=meta['sha256'] or marker.read_bytes()!=raw:
        raise ValueError('Source Excel snapshot changed or is not ready. Saved decisions are retained; retry after synchronization.')
    return dict(meta,path=str(config['workbook']))


def sync(config):
    import human_operations as h
    import source_updater as u
    from .source_assessment import sync_confidence_sheet
    from openpyxl.styles import Protection
    from openpyxl.workbook.protection import WorkbookProtection
    from .excel_output import prepare_output, normalize_font_order
    marker, worker_path = paths(config)
    with exclusive_process_lock(config['governance_db'].with_suffix('.export.lock')):
        try:
            version = authority_version(config);target = config['workbook']
            meta = load(marker)
            if meta.get('authority_version')==version and meta.get('schema')==SCHEMA and meta.get('render_version')==RENDER_VERSION and target.is_file() and sha256(target.read_bytes()).hexdigest()==meta.get('sha256'):
                atomic_json(worker_path,{'status':'current'})
                return dict(meta,status='current')
            if excel_appears_open(target): raise ValueError('Close the source Excel register to synchronize it. Your decisions are saved in the database.')
            atomic_json(worker_path,{'status':'refreshing'})
            wb = GovernanceStore(config['governance_db']).workbook(config)
            temporary = None
            try:
                if wb._governance_revision != version['revision']: raise ValueError('Governance changed while loading the snapshot; retry is required.')
                ops = wb[h.human_sheet_name(config)]
                h.prepare_human_workbook(wb,ops,h.operation_headers(ops))
                sync_confidence_sheet(wb,config['log_root']/'source-assessments.sqlite')
                prepare_output(wb,config)
                for sheet in wb:
                    for row in sheet:
                        for cell in row: cell.protection=Protection(locked=True)
                    sheet.protection.sheet=True
                    sheet.protection.autoFilter=False
                    sheet.protection.formatRows=False
                    sheet.protection.formatColumns=False
                if wb.security is None: wb.security=WorkbookProtection()
                wb.security.lockStructure=True
                target.parent.mkdir(parents=True,exist_ok=True)
                fd,name = tempfile.mkstemp(prefix='.source-registry-',suffix='.xlsx',dir=target.parent);os.close(fd)
                temporary = Path(name)
                u.save_workbook_atomic(wb,temporary,u.workbook_mtime(temporary))
                normalize_font_order(temporary)
                if authority_version(config)['assessment_sha256'] != version['assessment_sha256']:
                    raise ValueError('Source assessment changed during export; the previous snapshot is retained.')
                if excel_appears_open(target): raise ValueError('Excel opened during synchronization. Saved decisions and the previous snapshot are retained.')
                data = temporary.read_bytes()
                with temporary.open('r+b') as handle: os.fsync(handle.fileno())
                os.replace(temporary,target)
                meta = {'schema':SCHEMA,'render_version':RENDER_VERSION,'revision':version['revision'],'authority_version':version,
                        'sha256':sha256(data).hexdigest(),'generated_at':datetime.now(timezone.utc).isoformat()}
                atomic_json(marker,meta)
                atomic_json(worker_path,{'status':'current'})
                return dict(meta,status='current')
            finally:
                wb.close()
                if temporary is not None: temporary.unlink(missing_ok=True)
        except Exception as exc:
            atomic_json(worker_path,{'status':'failed','message':str(exc),'checked_at':datetime.now(timezone.utc).isoformat()})
            raise
