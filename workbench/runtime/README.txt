LOCAL RUNTIME SUPPORT
settings: private configuration and API credentials
state: local sessions, tasks, request/recovery journal and service identity
backups: consistent migration/recovery evidence
logs: execution/error diagnostics
cache: rebuildable intermediate dependencies and files
Only this README belongs in the application Git product. Runtime contents never enter business Collaboration or downstream deliveries. Preserve settings and recovery state during updates; do not treat the entire folder as disposable cache. See ../../ENVIRONMENT.md.
