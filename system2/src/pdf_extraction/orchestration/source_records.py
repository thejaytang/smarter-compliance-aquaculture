"""Generate version-bound record projections from already verified Canonical artifacts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from ..contracts.excel import ExcelDocument
from ..contracts.html import HtmlDocument
from ..domains.requirements.source_records import map_source_records
from ..domains.requirements.source_content import map_content_records
from ..verification.source_records import verify_source_records


def emit_records(canonical_path: Path, verification_path: Path, output: Path, *, schema_version='source-records/2'):
    from .source_batch import write_json
    raw=canonical_path.read_bytes();proof=verification_path.read_bytes()
    data=json.loads(raw);verification=json.loads(proof);digest=sha256(raw).hexdigest();proof_digest=sha256(proof).hexdigest()
    models={'html-document/2':HtmlDocument,'excel-document/1':ExcelDocument}
    if data.get('schema_version') not in models:raise ValueError('record_mapping_canonical_not_supported')
    document=models[data['schema_version']].model_validate(data)
    if (verification.get('status')!='passed' or verification.get('canonical_artifact_sha256')!=digest
        or verification.get('source_sha256')!=document.source.content_hash):
        raise ValueError('record_mapping_requires_matching_passed_source_verification')
    mappers={'source-records/1':map_source_records,'source-records/2':map_content_records}
    if schema_version not in mappers:raise ValueError('record_mapping_schema_not_supported')
    mapping=mappers[schema_version](document,digest,proof_digest)
    check=verify_source_records(document,mapping,digest,proof_digest)
    target=output/'source-records.json';write_json(target,mapping.model_dump())
    check['source_records_sha256']=sha256(target.read_bytes()).hexdigest()
    verification_target=output/'source-records-verification.json';write_json(verification_target,check)
    result={'schema_version':'source-records-result/1',
        'status':mapping.status if check['status']=='passed' else 'failed',
        'source_records_schema_version':mapping.schema_version,
        'canonical_sha256':digest,'source_verification_sha256':proof_digest,
        'source_records_path':target.name,'source_records_sha256':check['source_records_sha256'],
        'mapping_verification_path':verification_target.name,'mapping_verification_sha256':sha256(verification_target.read_bytes()).hexdigest()}
    write_json(output/'source-records-result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical',required=True,type=Path)
    parser.add_argument('--verification',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--schema-version',choices=['source-records/1','source-records/2'],default='source-records/2')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    from .source_batch import write_json
    try:result=emit_records(args.canonical,args.verification,args.output,schema_version=args.schema_version)
    except Exception as exc:
        write_json(args.output/'failure.json',{'status':'failed','reason':type(exc).__name__+':'+str(exc)})
        return 1
    return int(result['status']=='failed')

if __name__=='__main__':raise SystemExit(main())
