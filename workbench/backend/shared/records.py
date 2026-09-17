"""Canonical record encoding, fingerprints and UTC timestamps."""
from datetime import datetime, timezone
from hashlib import sha256
import json


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def fingerprint(value):
    return sha256(encoded(value).encode()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()
