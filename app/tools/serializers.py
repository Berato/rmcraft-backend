from typing import Any, Dict
from datetime import datetime, date

try:
    from bson import ObjectId
except Exception:
    ObjectId = None  # type: ignore


def _convert_value(v: Any) -> Any:
    """Convert a single value to a JSON-friendly representation."""
    # ObjectId -> str
    if ObjectId is not None and isinstance(v, ObjectId):
        return str(v)
    # datetimes -> isoformat
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    # otherwise leave as-is (primitives, dicts, lists handled elsewhere)
    return v


def serialize_document(doc: Any) -> Dict[str, Any]:
    """Serialize a Beanie/Pydantic document or plain dict into JSON-friendly dict.

    - If the object has `model_dump` (Pydantic v2) or `dict` (v1), prefer that.
    - Convert ObjectId and datetime values.
    """
    if doc is None:
        return {}

    # If it's a Pydantic/Beanie model, use its dump method first
    if hasattr(doc, "model_dump"):
        data = doc.model_dump()
    elif hasattr(doc, "dict"):
        data = doc.dict()
    elif isinstance(doc, dict):
        data = dict(doc)
    else:
        # Fallback: try to build a dict from __dict__
        data = getattr(doc, "__dict__", {}) or {}

    def recurse(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: recurse(_convert_value(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [recurse(_convert_value(x)) for x in obj]
        return _convert_value(obj)

    return recurse(data)
