"""Controlled batch CLI: no downloads, directory scan, UI, or business-state writes."""
import argparse
from hashlib import sha256
import json
import os
import tempfile
from pathlib import Path
from ..contracts.source import Snapshot, ParseResult
from ..intake.registry import read_registry, build_manifest, read_snapshot
from ..formats.router import route_format
from ..formats.html import parse_html
from ..formats.excel import parse_excel

def write_json(path: Path, value) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    # Publish a complete file exclusively; never replace an existing artifact.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def run_item(source: Snapshot, source_root: Path, output: Path, html_config: dict,
             pdf_config=None, page_indices=None) -> ParseResult:
    if output.resolve().is_relative_to(source_root.resolve()):
        raise ValueError('output_must_be_outside_source_root')
    output.mkdir(parents=True, exist_ok=False)
    kind = 'unknown'
    try:
        raw = read_snapshot(source, source_root)
        kind = route_format(source.relative_path, source.file_format, raw)
        if kind == 'html':
            canonical = parse_html(raw, source, html_config)
            path = output / 'canonical.json'
            write_json(path, canonical.model_dump())
            verification = None
            verification_path = None
            if canonical.schema_version == 'html-document/2':
                from ..verification.html import verify_html
                verification = verify_html(raw, canonical)
                verification['canonical_artifact_sha256'] = sha256(path.read_bytes()).hexdigest()
                verification_path = output / 'verification.json'
                write_json(verification_path, verification)
            passed = verification is None or verification['status'] == 'passed'
            result = ParseResult(source=source, format=kind, status='review_required' if passed else 'failed',
                                 canonical_path='canonical.json', canonical_sha256=sha256(path.read_bytes()).hexdigest(),
                                 canonical_schema_version=canonical.schema_version,
                                 verification_path='verification.json' if verification_path else None,
                                 verification_sha256=sha256(verification_path.read_bytes()).hexdigest() if verification_path else None,
                                 reason_codes=['uncalibrated_template_extraction', *canonical.issues] if passed else ['html_source_verification_failed', *verification['errors']])
        elif kind == 'excel':
            if source.file_format.lower().lstrip('.') == 'xls':
                result = ParseResult(source=source, format=kind, status='not_implemented',
                                     reason_codes=['excel_legacy_xls_not_supported'])
            else:
                from ..verification.excel import verify_excel
                canonical = parse_excel(raw, source)
                path = output / 'canonical.json'
                write_json(path, canonical.model_dump())
                verification = verify_excel(raw, canonical)
                verification['canonical_artifact_sha256'] = sha256(path.read_bytes()).hexdigest()
                verification_path = output / 'verification.json'
                write_json(verification_path, verification)
                passed = verification['status'] == 'passed'
                result = ParseResult(source=source, format=kind, status='review_required' if passed else 'failed',
                    canonical_path='canonical.json', canonical_sha256=sha256(path.read_bytes()).hexdigest(),
                    canonical_schema_version=canonical.schema_version, verification_path='verification.json',
                    verification_sha256=sha256(verification_path.read_bytes()).hexdigest(),
                    reason_codes=['uncalibrated_spreadsheet_extraction', *canonical.issues] if passed
                        else ['excel_source_verification_failed', *verification['errors']])
        elif pdf_config is None or not page_indices:
            result = ParseResult(source=source, format=kind, status='blocked',
                                 reason_codes=['pdf_explicit_config_and_window_required'])
        else:
            from ..formats.pdf import parse_pdf
            result = parse_pdf(source, source_root, output, pdf_config, page_indices)
    except Exception as exc:
        result = ParseResult(source=source, format=kind, status='failed',
                             reason_codes=[type(exc).__name__ + ':' + str(exc)])
    if (result.status=='review_required' and result.canonical_schema_version in ('html-document/2','excel-document/1')
        and result.canonical_path and result.verification_path):
        try:
            from .source_records import emit_records
            mapping=emit_records(output/result.canonical_path,output/result.verification_path,output)
            if mapping['status']=='failed':
                result=result.model_copy(update={'status':'failed','reason_codes':[*result.reason_codes,'source_record_mapping_verification_failed']})
        except Exception as exc:
            result=result.model_copy(update={'status':'failed','reason_codes':[*result.reason_codes,'source_record_mapping_failed:'+type(exc).__name__+':'+str(exc)]})
    write_json(output / 'result.json', result.model_dump())
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    authority = parser.add_mutually_exclusive_group(required=True)
    authority.add_argument('--system1', type=Path, help='System1 workspace; use its read-only authority bridge')
    authority.add_argument('--registry', type=Path, help='Offline compatibility: requires valid cached selection')
    parser.add_argument('--system1-config', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--source-id', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--html-config', type=Path, default=None)
    parser.add_argument('--pdf-config', type=Path)
    parser.add_argument('--pdf-pages', help='Explicit zero-based comma-separated indices, maximum 4')
    args = parser.parse_args()
    if args.registry and (not args.source_root or args.system1_config):
        parser.error('--registry requires --source-root and cannot use --system1-config')
    if args.system1 and args.source_root:
        parser.error('--system1 reads the source root from System1 configuration')
    handoff = None
    if args.system1:
        from ..intake.system1 import read_system1
        handoff = read_system1(args.system1, args.system1_config)
        args.source_root = handoff.source_root
    if args.output.resolve().is_relative_to(args.source_root.resolve()):
        parser.error('output_must_be_outside_source_root')
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    manifest = {'rejected': []}
    try:
        if handoff:
            handoff.assert_current()
            records, digest = handoff.records, handoff.registry_sha256
            evidence = dict(handoff.evidence, sources={sid: value for sid, value in handoff.evidence['sources'].items()
                                                     if sid in args.source_id})
            write_json(args.output / 'system1-handoff.json', evidence)
        else:
            records, digest = read_registry(args.registry)
        manifest = build_manifest(records, digest, args.source_root, set(args.source_id))
        if handoff:
            manifest['selection_authority'] = {'path': 'system1-handoff.json',
                'sha256': sha256((args.output / 'system1-handoff.json').read_bytes()).hexdigest()}
        write_json(args.output / 'manifest.json', manifest)
        config = json.loads(args.html_config.read_text()) if args.html_config else {
            'template':'auto', 'encoding':'utf-8-sig',
            }
        pdf_config, pages = None, None
        if args.pdf_config:
            from ..config import AppConfig
            pdf_config = AppConfig.from_yaml(args.pdf_config)
        if args.pdf_pages:
            pages = {int(v) for v in args.pdf_pages.split(',')}
        for item in manifest['items']:
            results.append(run_item(Snapshot(**item), args.source_root, args.output / item['snapshot_id'],
                                    config, pdf_config, pages).model_dump())
        if handoff:
            handoff.assert_current()
    except Exception as exc:
        write_json(args.output / 'batch.json', {'status':'failed', 'results':results,
                   'rejected':manifest['rejected'], 'reason_codes':[type(exc).__name__ + ':' + str(exc)]})
        return 1
    failed = bool(manifest['rejected']) or any(r['status'] != 'review_required' for r in results)
    write_json(args.output / 'batch.json', {'status':'completed_with_issues' if failed else 'completed',
                                         'results':results, 'rejected':manifest['rejected']})
    return int(failed)

if __name__ == '__main__':
    raise SystemExit(main())
