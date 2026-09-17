"""One import-only observation. Never instantiate a parser or open a PDF."""
import sys, time, json, faulthandler
from pathlib import Path
START=time.monotonic()
faulthandler.enable()
faulthandler.dump_traceback_later(30, repeat=True)
def no_external(event,args):
    if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
        raise RuntimeError('Import-only diagnostic forbids external calls: '+event)
sys.addaudithook(no_external)
print(json.dumps({'stage':'import_start','monotonic':START}),flush=True)
import docling_parse
print(json.dumps({'stage':'top_level_imported','elapsed_seconds':time.monotonic()-START,'file':docling_parse.__file__}),flush=True)
from docling_parse.pdf_parser import DoclingPdfParser
elapsed=time.monotonic()-START
faulthandler.cancel_dump_traceback_later()
print(json.dumps({'stage':'parser_symbol_imported_no_instantiation','elapsed_seconds':elapsed,'module':DoclingPdfParser.__module__,'loaded_paths':{k:getattr(sys.modules.get(k),'__file__',None) for k in ['docling_parse','docling_parse.pdf_parser','docling_core','pandas','numpy','numpy.random._philox','numpy.random._sfc64','cv2']},'parser_instantiated':False,'pdf_opened':False}),flush=True)
