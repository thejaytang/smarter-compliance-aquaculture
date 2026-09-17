"""Versioned offline JSON/document archives; no database state or extraction effects."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import stat
import unicodedata
import uuid
import zlib
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED, BadZipFile, LargeZipFile

FORMAT = 'aquaculture-offline-collaboration'
VERSION = 1
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_FILES = 2048
_MANIFEST = 'manifest.json'
_DATABASE_SUFFIXES = {'.db','.db3','.sqlite','.sqlite3','.sqlite-wal','.sqlite-shm'}
_RESERVED = re.compile(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', re.I)


def _json(value):
    try:
        return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,RecursionError) as exc:
        raise ValueError('collaboration_package_invalid_json') from exc


def _object_pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value: raise ValueError('collaboration_package_duplicate_json_key')
        value[key]=item
    return value


def _load_json(raw):
    def nonfinite(_): raise ValueError('collaboration_package_nonfinite_json')
    try:
        return json.loads(raw,object_pairs_hook=_object_pairs,parse_constant=nonfinite)
    except (ValueError,UnicodeError,RecursionError) as exc:
        raise ValueError('collaboration_package_invalid_manifest') from exc


def _path(value):
    if not isinstance(value,str) or not value or len(value.encode('utf-8',errors='surrogatepass'))>1024 or any(0xD800<=ord(c)<=0xDFFF for c in value):
        raise ValueError('collaboration_package_invalid_path')
    if value.startswith('/') or '\\' in value or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('collaboration_package_unsafe_path')
    parts=value.split('/')
    if len(parts)>16 or any(p in {'','.','..'} or p[-1:] in {'.',' '} or any(c in p for c in ':<>"|?*') or _RESERVED.match(p) for p in parts):
        raise ValueError('collaboration_package_unsafe_path')
    if str(PurePosixPath(value))!=value:
        raise ValueError('collaboration_package_unsafe_path')
    return unicodedata.normalize('NFC',value).casefold()


def _database(path,raw):
    name=path.lower()
    if PurePosixPath(name).suffix in _DATABASE_SUFFIXES or name.endswith(('.sqlite-wal','.sqlite-shm','.sqlite3-wal','.sqlite3-shm')) or raw.startswith(b'SQLite format 3\0'):
        raise ValueError('collaboration_package_databases_not_allowed')


def _identity(kind,metadata):
    if kind not in {'work','submission','collection'} or not isinstance(metadata,dict):
        raise ValueError('collaboration_package_kind_or_metadata_invalid')
    identity=metadata.get('id')
    try:
        if not isinstance(identity,str) or str(uuid.UUID(identity))!=identity: raise ValueError()
    except (ValueError,TypeError,AttributeError):
        raise ValueError('collaboration_package_id_must_be_canonical_uuid') from None
    return identity


def build_package(kind,metadata,files):
    """Build an in-memory ZIP from caller-selected logical file names and bytes."""
    identity=_identity(kind,metadata)
    if not isinstance(files,dict) or len(files)>MAX_FILES:
        raise ValueError('collaboration_package_file_count_limit')
    seen=set();inventory=[];total=0
    for path in files: _path(path)
    for path,raw in sorted(files.items()):
        folded=_path(path)
        if folded in seen or any(folded.startswith(other+'/') or other.startswith(folded+'/') for other in seen): raise ValueError('collaboration_package_path_collision')
        seen.add(folded)
        if not isinstance(raw,bytes): raise ValueError('collaboration_package_file_bytes_required')
        if len(raw)>MAX_FILE_BYTES: raise ValueError('collaboration_package_file_size_limit')
        _database(path,raw)
        total+=len(raw)
        if total>MAX_TOTAL_BYTES: raise ValueError('collaboration_package_total_size_limit')
        inventory.append(dict(path=path,size=len(raw),sha256=sha256(raw).hexdigest()))
    manifest=_json(dict(format=FORMAT,version=2 if kind=='collection' else VERSION,kind=kind,package_id=identity,metadata=metadata,files=inventory))
    if len(manifest)>MAX_MANIFEST_BYTES or len(manifest)+total>MAX_TOTAL_BYTES:
        raise ValueError('collaboration_package_manifest_or_total_size_limit')
    output=BytesIO()
    with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        def write(path,raw):
            entry=ZipInfo(path,date_time=(1980,1,1,0,0,0));entry.compress_type=ZIP_DEFLATED
            entry.create_system=3;entry.external_attr=(stat.S_IFREG|0o600)<<16
            archive.writestr(entry,raw)
        write(_MANIFEST,manifest)
        for path,raw in sorted(files.items()): write('files/'+path,raw)
    result=output.getvalue()
    if len(result)>MAX_ARCHIVE_BYTES: raise ValueError('collaboration_package_archive_size_limit')
    return result


def read_package(data):
    """Validate fully before returning bytes. Never extract paths to a filesystem."""
    if not isinstance(data,bytes) or not data or len(data)>MAX_ARCHIVE_BYTES:
        raise ValueError('collaboration_package_archive_size_limit')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries=archive.infolist()
            if not entries or len(entries)>MAX_FILES+1: raise ValueError('collaboration_package_file_count_limit')
            seen=set();total=0
            for entry in entries:
                folded=_path(entry.filename)
                if folded in seen or any(folded.startswith(other+'/') or other.startswith(folded+'/') for other in seen): raise ValueError('collaboration_package_path_collision')
                seen.add(folded)
                mode=entry.external_attr>>16
                if entry.is_dir() or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in {0,stat.S_IFREG}:
                    raise ValueError('collaboration_package_nonregular_entry')
                if entry.flag_bits&1 or entry.compress_type not in {ZIP_STORED,ZIP_DEFLATED}:
                    raise ValueError('collaboration_package_encoding_not_supported')
                limit=MAX_MANIFEST_BYTES if entry.filename==_MANIFEST else MAX_FILE_BYTES
                if entry.file_size>limit: raise ValueError('collaboration_package_file_size_limit')
                total+=entry.file_size
                if total>MAX_TOTAL_BYTES: raise ValueError('collaboration_package_total_size_limit')
            if _MANIFEST not in archive.namelist(): raise ValueError('collaboration_package_manifest_missing')
            manifest=_load_json(archive.read(_MANIFEST))
            if not isinstance(manifest,dict) or manifest.get('format')!=FORMAT or type(manifest.get('version')) is not int or manifest['version'] not in (1,2):
                raise ValueError('collaboration_package_version_not_supported')
            if set(manifest)!={'format','version','kind','package_id','metadata','files'}:
                raise ValueError('collaboration_package_manifest_shape_invalid')
            if (manifest['kind']=='collection') != (manifest['version']==2):raise ValueError('collaboration_package_version_kind_mismatch')
            identity=_identity(manifest['kind'],manifest['metadata'])
            if manifest['package_id']!=identity: raise ValueError('collaboration_package_identity_mismatch')
            inventory=manifest['files']
            if not isinstance(inventory,list) or len(inventory)>MAX_FILES: raise ValueError('collaboration_package_inventory_invalid')
            logical_seen=set();expected={_MANIFEST};files={}
            for item in inventory:
                if not isinstance(item,dict) or set(item)!={'path','size','sha256'}:
                    raise ValueError('collaboration_package_inventory_invalid')
                path=item['path'];folded=_path(path)
                if folded in logical_seen: raise ValueError('collaboration_package_path_collision')
                logical_seen.add(folded)
                if type(item['size']) is not int or not 0<=item['size']<=MAX_FILE_BYTES or not isinstance(item['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',item['sha256']):
                    raise ValueError('collaboration_package_inventory_invalid')
                name='files/'+path;expected.add(name)
                if name not in archive.namelist(): raise ValueError('collaboration_package_file_missing')
                entry=archive.getinfo(name)
                if entry.file_size!=item['size']: raise ValueError('collaboration_package_file_integrity_failure')
                raw=archive.read(name)
                if len(raw)!=item['size'] or sha256(raw).hexdigest()!=item['sha256']:
                    raise ValueError('collaboration_package_file_integrity_failure')
                _database(path,raw);files[path]=raw
            if set(archive.namelist())!=expected: raise ValueError('collaboration_package_unlisted_entry')
            return dict(kind=manifest['kind'],metadata=manifest['metadata'],files=files,package_id=identity,digest=sha256(data).hexdigest())
    except (BadZipFile,LargeZipFile,KeyError,NotImplementedError,RuntimeError,EOFError,UnicodeError,zlib.error) as exc:
        raise ValueError('collaboration_package_corrupt_archive') from exc

