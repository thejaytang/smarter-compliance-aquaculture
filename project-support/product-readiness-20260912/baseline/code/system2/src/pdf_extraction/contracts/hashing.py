"""Stable hashes for versioned JSON contracts."""
import json
from hashlib import sha256


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(encoded(value).encode()).hexdigest()


