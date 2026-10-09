"""Native file access without changing portable path identities or stored names.

Windows extended-length syntax belongs at the filesystem boundary, never in
manifests, source IDs, browser URLs or serialized operational descriptors.
"""
import os
from contextlib import contextmanager
from pathlib import Path
import shutil
import stat
import tempfile
from urllib.parse import quote


def windows_io_path(value):
    """Normalize before adding the Win32 extended-length namespace."""
    import ntpath
    value = ntpath.abspath(value)
    if value.startswith('\\\\?\\'):
        return value
    if value.startswith('\\\\'):
        return '\\\\?\\UNC\\' + value[2:]
    return '\\\\?\\' + value


def logical_path(value):
    if value.startswith('\\\\?\\UNC\\'):
        return '\\\\' + value[8:]
    if value.startswith('\\\\?\\'):
        return value[4:]
    return value


class FilePath(type(Path())):
    """A normal pathlib path whose OS argument supports long Windows paths.

    Joining paths retains this type. str()/JSON/URIs retain ordinary path
    spelling; only os.fspath() opts into extended native file access. Reserve
    room for directory creation and SQLite journal/atomic-copy suffixes.
    """
    def __fspath__(self):
        value = str(self)
        if os.name == 'nt' and len(os.path.abspath(value).encode('utf-16-le')) // 2 >= 248:
            return windows_io_path(value)
        return value

    def resolve(self, strict=False):
        value = super().resolve(strict=strict)
        return type(self)(logical_path(str(value)) if os.name == 'nt' else value)

    def as_uri(self):
        return Path(str(self)).as_uri()


def check_file_paths(paths):
    """Reject unsupported component/total lengths before preparing a package."""
    if os.name != 'nt':
        return
    for value in paths:
        path = FilePath(value).absolute()
        units = lambda text: len(text.encode('utf-16-le')) // 2
        if units(windows_io_path(str(path))) >= 32760 or any(units(part) > 255 for part in path.parts[1:]):
            raise ValueError('Path exceeds native Windows filesystem limits: ' + str(path))


def sqlite_uri(path):
    """Native SQLite URI; separate from portable file/browser URIs."""
    path = FilePath(path).absolute()
    native = os.fspath(path)
    if os.name == 'nt' and native.startswith('\\\\?\\'):
        return 'file:' + quote(native, safe=':')
    return path.as_uri()


@contextmanager
def temporary_directory(prefix='wb-', dir=None):
    """Short, unique staging with long-path-safe cleanup of its own tree."""
    parent = FilePath(dir or tempfile.gettempdir()).resolve()
    root = FilePath(tempfile.mkdtemp(prefix=prefix, dir=parent))
    try:
        yield root
    finally:
        if root.resolve().parent != parent:
            raise ValueError('Temporary directory no longer belongs to its original parent.')
        def retry_readonly(function, path, error):
            candidate = FilePath(logical_path(path)).resolve()
            if not isinstance(error, PermissionError) or not candidate.is_relative_to(root.resolve()) or os.path.islink(path):
                raise error
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)
        shutil.rmtree(windows_io_path(str(root)) if os.name == 'nt' else root, onexc=retry_readonly)
