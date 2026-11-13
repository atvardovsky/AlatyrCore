"""Small shared CLI input primitives without loading a session or adapter."""

from __future__ import annotations

import argparse
import json
from typing import Any


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen", set())
        if self.dest in seen:
            parser.error(f"{option_string} may be supplied only once")
        namespace._seen = seen | {self.dest}
        setattr(namespace, self.dest, values)


def json_object(raw: bytes, label: str) -> dict[str, Any]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate keys")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value
