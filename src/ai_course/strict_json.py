"""Decode each JSON request once, rejecting ambiguous and non-finite input."""

import json
import math
import re

from fastapi.routing import APIRoute
from starlette.requests import Request

MAX_JSON_DEPTH = 64
_STRUCTURAL_TOKENS = re.compile(r'["{}\[\]]')


def _invalid(message):
    raise json.JSONDecodeError(message, "", 0)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid("Duplicate JSON object key")
        result[key] = value
    return result


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        _invalid("Non-finite JSON number")
    return number


def decode_json(body):
    try:
        document = body.decode("utf-8-sig") if isinstance(body, (bytes, bytearray)) else body
        depth = 0
        cursor = 0
        while token := _STRUCTURAL_TOKENS.search(document, cursor):
            character = token.group(0)
            cursor = token.end()
            if character == '"':
                # Skip a string in linear time without decoding it a second time.
                # Quote/escape repetitions must not trigger regex backtracking.
                while True:
                    end = document.find('"', cursor)
                    if end < 0:
                        _invalid("Unterminated JSON string")
                    slash = end - 1
                    while slash >= 0 and document[slash] == "\\":
                        slash -= 1
                    cursor = end + 1
                    if (end - 1 - slash) % 2 == 0:
                        break
                continue
            if character in "{[":
                depth += 1
                if depth > MAX_JSON_DEPTH:
                    _invalid("JSON nesting exceeds 64 levels")
            elif character in "}]":
                depth -= 1
        return json.loads(
            document,
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: _invalid("Non-finite JSON number"),
            parse_float=_finite_float,
        )
    except json.JSONDecodeError:
        raise
    except (ValueError, RecursionError):
        _invalid("JSON value exceeds parser limits or uses invalid encoding")


class StrictJSONRequest(Request):
    async def json(self):
        if not hasattr(self, "_json"):
            self._json = decode_json(await self.body())
        return self._json


class StrictJSONRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def strict_handler(request):
            return await original(StrictJSONRequest(request.scope, request.receive))

        return strict_handler
