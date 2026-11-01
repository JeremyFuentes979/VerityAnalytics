"""JSON helpers shared by every agent.

Agent output is read by Python (Manager) *and* by the Node site, so it must be
strictly valid JSON: no NaN / Infinity literals, no numpy scalars, no Timestamps.
Writes go through a temp file + rename so a reader never sees a half-written file.
"""

import json
import math
import os
import tempfile
from datetime import date, datetime


def sanitize(obj):
    """Recursively convert obj into plain, strictly-JSON-serialisable Python."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "item") and callable(obj.item):  # numpy scalar
        try:
            return sanitize(obj.item())
        except (ValueError, TypeError):
            return str(obj)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, int):
        return obj
    if hasattr(obj, "isoformat"):  # pandas Timestamp / NaT-like
        try:
            return obj.isoformat()
        except (ValueError, TypeError):
            return None
    return str(obj)


def write_json(path, obj, indent=2):
    """Atomically write sanitised JSON to path."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sanitize(obj), f, indent=indent, allow_nan=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default
