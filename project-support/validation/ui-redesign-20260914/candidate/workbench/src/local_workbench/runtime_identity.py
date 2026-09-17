"""Runtime evidence distinguishes the parent snapshot from freshly invoked workers."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os

PACKAGE=Path(__file__).resolve().parent

def source_manifest():
    return {str(p.relative_to(PACKAGE)):sha256(p.read_bytes()).hexdigest()
            for p in sorted(PACKAGE.glob('*.py'))}

STARTED_AT=datetime.now(timezone.utc).isoformat()
STARTUP_SOURCES=source_manifest()

def describe(app):
    current=source_manifest()
    ui={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(getattr(app,'ui_root',app.root/'ui').glob('*')) if p.is_file()}
    return dict(schema='workbench-runtime-evidence/1',pid=os.getpid(),parent_imported_at=STARTED_AT,
        parent_startup_sources=STARTUP_SOURCES,
        parent_startup_fingerprint=sha256(json.dumps(STARTUP_SOURCES,sort_keys=True).encode()).hexdigest(),
        parent_source_changes=[p for p in sorted(set(current)|set(STARTUP_SOURCES)) if current.get(p)!=STARTUP_SOURCES.get(p)],
        current_ui_fingerprint=sha256(json.dumps(ui,sort_keys=True).encode()).hexdigest(),
        ui_loading='Files served on request; browser must reload to consume changed modules.',
        workers='System1 and System2 are new project-environment subprocesses per call; parent startup snapshot does not identify later worker code.',
        system1_root=str(app.adapter.root),system1_config=str(app.adapter.config),
        system2_root=str(app.system2.root),system2_runtime=str(app.system2.runtime),
        boundary='Startup source-file snapshot, not proof of all code paths or quality. Running source changes require a controlled reload for parent delivery.')
