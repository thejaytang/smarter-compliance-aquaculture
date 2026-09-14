"""Isolated experiment only: HTTP JSON allocator churn versus reused workers.

Does not instantiate Application, open project databases, or restart any service.
Each variant runs in a fresh child process on an ephemeral loopback port.
"""
from concurrent.futures import ThreadPoolExecutor
import gc
import ctypes
from http.server import HTTPServer, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import tracemalloc
from urllib.request import Request, urlopen


def child(variant):
    from local_workbench.server import Handler
    payload={'id':'isolated-synthetic','blocks':[{'id':'table','type':'table','table':{'rows':[[f'R{r}C{c}' for c in range(30)] for r in range(20000)]}}]}
    wire=json.dumps(payload,ensure_ascii=False).encode()
    if variant.endswith('fresh'): del payload
    gc.collect()
    tracemalloc.start(1)
    initial_objects=len(gc.get_objects())
    initial_alloc=tracemalloc.get_traced_memory()[0]
    class ExperimentalHandler(Handler):
        def do_GET(self):
            if self.path=='/stats':
                current,peak=tracemalloc.get_traced_memory()
                data=dict(pid=os.getpid(),traced_current=current,traced_peak=peak,objects_delta=len(gc.get_objects())-initial_objects,
                          initial_traced=initial_alloc,threads=threading.active_count(),gc_counts=gc.get_count(),gc_collections=gc.get_stats(),rss_bytes=rss(os.getpid()))
                return self.send(200,data)
            if self.path=='/collect':
                collected=gc.collect()
                return self.send(200,{'collected':collected})
            if variant.endswith('bytes'):
                return self.send(200,wire,'application/octet-stream')
            data=json.loads(wire) if variant.endswith('fresh') else payload
            return self.send(200,data)
    class ReusedWorkers(HTTPServer):
        def __init__(self,*args,**kwargs):
            self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='isolated_http')
            super().__init__(*args,**kwargs)
        def process_request(self,request,address):
            self.pool.submit(self.process_one,request,address)
        def process_one(self,request,address):
            try: self.finish_request(request,address)
            except Exception: self.handle_error(request,address)
            finally: self.shutdown_request(request)
    server_type=ReusedWorkers if variant.startswith('pool') else ThreadingHTTPServer
    server=server_type(('127.0.0.1',0),ExperimentalHandler)
    print(json.dumps({'port':server.server_port,'pid':os.getpid(),'payload_bytes':len(wire),'variant':variant}),flush=True)
    server.serve_forever(poll_interval=.05)


def get(url):
    with urlopen(Request(url,headers={'Connection':'close'}),timeout=30) as response:
        if '/stats' in url or '/collect' in url: return json.load(response)
        total=0
        while chunk:=response.read(256*1024): total+=len(chunk)
        return total


def rss(pid):
    class TaskInfo(ctypes.Structure):
        _fields_=[('virtual_size',ctypes.c_uint64),('resident_size',ctypes.c_uint64),('other_time',ctypes.c_uint64*4),('counters',ctypes.c_int32*12)]
    info=TaskInfo();library=ctypes.CDLL('/usr/lib/libproc.dylib')
    count=library.proc_pidinfo(pid,4,0,ctypes.byref(info),ctypes.sizeof(info))
    if count!=ctypes.sizeof(info): raise RuntimeError('Current process RSS unavailable')
    return info.resident_size


def run(output,variants=('threaded-fresh','pool-fresh','threaded-fixed','threaded-bytes')):
    reports=[]
    for variant in variants:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--child',variant],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            info=json.loads(process.stdout.readline());base=f"http://127.0.0.1:{info['port']}";series=[]
            def sample(reads):
                point={'reads':reads,**get(base+'/stats')};series.append(point)
                print(variant,reads,'rssMB',round(point['rss_bytes']/1e6,2),'tracedMB',round(point['traced_current']/1e6,3),flush=True)
            sample(0);durations=[]
            for n in range(1,101):
                start=time.perf_counter();received=get(base+'/payload');durations.append(time.perf_counter()-start)
                assert received==info['payload_bytes']
                if n%10==0: sample(n)
            collected=get(base+'/collect');sample(101)
            reports.append({**info,'series':series,'gc_after100':collected,'seconds':durations})
            Path(output).write_text(json.dumps({'scope':'100 sequential synthetic 600000-cell responses per fresh isolated server; existing Handler.send, new-thread versus reused-worker control; no business databases','variants':reports},indent=2))
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
    print('Complete:',output,flush=True)


if __name__=='__main__':
    if sys.argv[1:2]==['--child']: child(sys.argv[2])
    else: run(sys.argv[1],sys.argv[2].split(',')) if len(sys.argv)>2 else run(sys.argv[1])
