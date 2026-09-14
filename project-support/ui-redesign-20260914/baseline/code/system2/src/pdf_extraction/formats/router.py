from io import BytesIO
from pathlib import PurePosixPath
import re
import zipfile

class FormatError(ValueError):
    pass

def route_format(path: str, declared: str, raw: bytes) -> str:
    suffix = PurePosixPath(path).suffix.lower().lstrip('.')
    normal = {'htm':'html', 'html':'html', 'pdf':'pdf', 'xlsx':'excel', 'xls':'excel'}
    kind = normal.get(suffix)
    if kind is None:
        raise FormatError('unsupported_suffix')
    registered = declared.lower().lstrip('.')
    if normal.get(registered) != kind or (kind == 'excel' and registered != suffix):
        raise FormatError('registered_format_mismatch')
    head = raw[:8192].lstrip(b'\xef\xbb\xbf \t\r\n')
    if kind == 'pdf' and not head.startswith(b'%PDF-'):
        raise FormatError('pdf_signature_mismatch')
    if kind == 'html' and (head.startswith((b'%PDF-', b'PK\x03\x04')) or not re.search(br'<(?:!doctype\s+html|html|head|body|div)\b', head, re.I)):
        raise FormatError('html_signature_mismatch')
    if suffix == 'xlsx':
        try:
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                if not {'[Content_Types].xml','xl/workbook.xml'} <= set(archive.namelist()):
                    raise FormatError('xlsx_container_mismatch')
        except zipfile.BadZipFile as exc:
            raise FormatError('xlsx_container_mismatch') from exc
    if suffix == 'xls' and not raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise FormatError('xls_signature_mismatch')
    return kind
