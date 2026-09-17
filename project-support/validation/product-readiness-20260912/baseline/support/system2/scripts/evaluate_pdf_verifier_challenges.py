"""Replay frozen development controls; never report independent accuracy.

Use the component environment and PYTHONPATH=src. Inputs are local, frozen
original-line observations and deliberately mutated output records. This is not
a source transcription/reference evaluator or a production acceptance writer.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from pdf_extraction.verification import source_comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    original_hash = sha256(args.original.read_bytes()).hexdigest()
    case_bytes = args.cases.read_bytes()
    fixture = json.loads(case_bytes)
    if fixture.get('schema') not in {'verifier-diagnostic-challenges/1', 'verifier-spatial-challenges/1'}:
        raise ValueError('unsupported_challenge_schema')
    reports = []
    identities = set()
    started = time.monotonic()
    for case in fixture['cases']:
        if case['id'] in identities or case['expected'] not in {'clean_control', 'difference', 'localized_abstention'}:
            raise ValueError('invalid_challenge_identity_or_expectation')
        identities.add(case['id'])
        if case['page']['source_sha256'] != original_hash:
            raise ValueError('challenge_source_mismatch')
        result = source_comparison.compare(case['page'], case['records'])
        reports.append(dict(id=case['id'], expected=case['expected'], **result))
    errors = [r for r in reports if r['expected'] == 'difference']
    controls = [r for r in reports if r['expected'] == 'clean_control']
    abstentions = [r for r in reports if r['expected'] == 'localized_abstention']
    localized = lambda result: any(u.get('record_id') and u.get('bbox') for u in result['unverified'])
    report = dict(schema='verifier-diagnostic-result/1',
                  evidence_class='seeded_development_controls_not_independent_acceptance',
                  source_sha256=original_hash, cases_sha256=sha256(case_bytes).hexdigest(),
                  comparator_sha256=sha256(Path(source_comparison.__file__).read_bytes()).hexdigest(),
                  elapsed_seconds=round(time.monotonic()-started, 6),
                  summary=dict(seeded_error_cases=len(errors), detected=sum(bool(r['findings']) for r in errors),
                               clean_controls=len(controls), controls_with_findings=sum(bool(r['findings']) for r in controls),
                               controls_with_localized_abstention=sum(localized(r) for r in controls),
                               localized_abstention_cases=len(abstentions), localized_abstentions=sum(localized(r) for r in abstentions)),
                  independent_precision=None, independent_recall=None, acceptance='not_assessed', cases=reports)
    if sha256(args.original.read_bytes()).hexdigest() != original_hash:
        raise ValueError('original_changed_during_challenge_run')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(report['summary'], acceptance='not_assessed', output=str(args.output))))


if __name__ == '__main__':
    main()
