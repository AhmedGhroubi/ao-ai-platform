from typing import Any


def get_val(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    if hasattr(obj, key):
        value = getattr(obj, key, None)
        if value is not None:
            return value

    for attr_name in ["data", "_data", "profile", "criteres"]:
        if hasattr(obj, attr_name):
            internal = getattr(obj, attr_name)
            if isinstance(internal, dict) and key in internal:
                return internal[key]

    if hasattr(obj, "__dict__") and key in obj.__dict__:
        return obj.__dict__[key]

    return default