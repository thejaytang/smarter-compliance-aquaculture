"""Last checked source-authority version for asynchronous output status.

This is a replaceable marker, not source business state or an Excel input.
"""
import json
import os
from pathlib import Path
import tempfile
import time


def publish(root, registry_sha256=None, registry_kind=None, error=False):
    root=Path(root);target=root/'source-version.json'
    value={'schema':'system2-source-version/1','checked_at':time.time(),
           'status':'unknown' if error else 'checked',
           'registry_sha256':registry_sha256,'registry_kind':registry_kind}
    fd,name=tempfile.mkstemp(prefix='.source-version-',dir=root)
    try:
        with os.fdopen(fd,'w') as handle:
            json.dump(value,handle);handle.flush();os.fsync(handle.fileno())
        os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)
