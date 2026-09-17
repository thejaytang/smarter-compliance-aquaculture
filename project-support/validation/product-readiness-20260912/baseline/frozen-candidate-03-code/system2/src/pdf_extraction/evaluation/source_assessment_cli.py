"""Offline, file-bound evaluation; never writes reference labels or Gold."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from .source_assessment import evaluate


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('original','reference','assessment','records','verification','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv)
    read=lambda p:json.loads(p.read_text())
    result=evaluate(read(args.reference),read(args.assessment),read(args.records),read(args.verification),
                    source_sha256=sha256(args.original.read_bytes()).hexdigest())
    content=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    # Final evidence paths are exclusive. No existing reference, original,
    # historical report or other file can be overwritten by this command.
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:handle.write(content)
    print(json.dumps(dict(report=str(args.output),independent_acceptance=result['independent_acceptance'],incomplete=result['incomplete'])))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
