"""Verify a bound original once per transfer, then stream from the same descriptor."""
import hashlib
import os
from pathlib import Path
import re
from urllib.parse import quote

def stream_original(handler, original, allowed_root):
    path = Path(original['path']).resolve()
    allowed = Path(allowed_root).resolve()
    if path.parent != allowed or not re.fullmatch(r'[0-9a-f]{64}\.(pdf|html|htm|xlsx|xls)', path.name):
        raise ValueError('Original is outside the bound material store.')
    if path.name.split('.')[0] != original['sha256']:
        raise ValueError('Original binding does not match its content identity.')
    with path.open('rb') as source:
        before = os.fstat(source.fileno())
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
        after = os.fstat(source.fileno())
        if digest != original['sha256'] or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Original transfer integrity failure.')
        size = before.st_size; start = 0; end = size-1; status = 200
        is_pdf = original['file_format'].lower().lstrip('.') == 'pdf'
        range_header = handler.headers.get('Range') if is_pdf else None
        invalid = False
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
            if not match or not any(match.groups()): invalid = True
            else:
                first, last = match.groups()
                if first:
                    start = int(first); end = min(int(last), size-1) if last else size-1
                else:
                    count = int(last); start = max(0, size-count)
                    if count == 0: invalid = True
                invalid = invalid or start >= size or start > end
            status = 416 if invalid else 206
        length = 0 if invalid else max(0, end-start+1)
        handler.send_response(status)
        headers = {'Content-Type': 'application/pdf' if is_pdf else 'application/octet-stream',
            'Content-Length': str(length), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'ETag': '"'+digest+'"',
            'Content-Disposition': ('inline' if is_pdf else 'attachment')+"; filename*=UTF-8''"+quote(original['filename']),
            'Content-Security-Policy': "default-src 'none'; object-src 'self'; frame-ancestors 'self'"}
        if is_pdf: headers['Accept-Ranges'] = 'bytes'
        if status == 206: headers['Content-Range'] = f'bytes {start}-{end}/{size}'
        if status == 416: headers['Content-Range'] = f'bytes */{size}'
        for key, value in headers.items(): handler.send_header(key, value)
        handler.end_headers()
        source.seek(start)
        remaining = length
        while remaining:
            chunk = source.read(min(256*1024, remaining))
            if not chunk: raise OSError('Original became unavailable during transfer.')
            try: handler.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError): return
            remaining -= len(chunk)
