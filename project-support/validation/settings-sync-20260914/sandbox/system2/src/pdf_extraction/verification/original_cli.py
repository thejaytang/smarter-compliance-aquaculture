"""Standalone, read-only source checker with a small normalized-result adapter.

Run with --help. This command never writes workflow decisions or accepts content.
"""
import argparse
import json
from pathlib import Path

from ..contracts.hashing import digest
from .pdf_original import acquire
from .source_comparison import compare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--records',type=Path,required=True,help='JSON list of located output records')
    parser.add_argument('--page',type=int,required=True,help='One-based original PDF page')
    parser.add_argument('--parser-engine',action='append',default=[])
    parser.add_argument('--language',default='eng')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    records=json.loads(args.records.read_text())
    page=acquire(args.original,args.page-1,parser_engines=args.parser_engine,language=args.language)
    result=dict(compare(page,records),schema_version='source-verification/1',original=page,input_sha256=digest(records))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'output':str(args.output),'findings':len(result['findings']),
                      'unverified':len(result['unverified']),'acceptance':'not_assessed'}))


if __name__=='__main__':
    main()
