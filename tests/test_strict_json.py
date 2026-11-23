import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_course.strict_json import StrictJSONRequest, StrictJSONRoute, decode_json


@pytest.mark.parametrize(
    "body",
    [
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b'{"value":1e999}',
        b'{"value":1,"value":2}',
        b'{"nested":{"a":1,"a":2}}',
        b'{"value":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}",
    ],
)
def test_invalid_json_is_rejected_before_endpoint_execution(body):
    app = FastAPI()
    app.router.route_class = StrictJSONRoute
    called = []

    @app.post("/input")
    def process(payload: dict):
        called.append(payload)
        return payload

    with TestClient(app) as client:
        response = client.post("/input", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"
    assert not called


def test_valid_types_and_negative_numbers_are_preserved():
    value = decode_json(b'{"array":[-1,1.5,true,false,null],"nested":{"text":"ok"}}')
    assert value == {"array": [-1, 1.5, True, False, None], "nested": {"text": "ok"}}


def test_request_body_and_parsed_json_are_cached_once():
    async def scenario():
        reads = []

        async def receive():
            reads.append(True)
            return {"type": "http.request", "body": b'{"a":1}', "more_body": False}

        request = StrictJSONRequest({"type": "http"}, receive)
        first = await request.json()
        assert first is await request.json()
        assert reads == [True]

    asyncio.run(scenario())


def test_invalid_number_encoding_does_not_raise_a_server_exception():
    with pytest.raises(json.JSONDecodeError):
        decode_json(b'{"value":' + b"1" * 10000 + b"}")


def test_structural_characters_in_strings_are_not_counted_as_nesting():
    value = {"text": "[" * 1000, "escaped": '\\"[' * 100, "unicode": "Français"}
    assert decode_json(json.dumps(value, ensure_ascii=False).encode()) == value


def test_json_depth_limit_is_deterministic_and_allows_the_boundary():
    allowed = b'{"value":' + b"[" * 63 + b"0" + b"]" * 63 + b"}"
    assert decode_json(allowed) is not None
    with pytest.raises(json.JSONDecodeError):
        decode_json(b'{"value":' + b"[" * 64 + b"0" + b"]" * 64 + b"}")


def test_http_json_must_use_utf8():
    with pytest.raises(json.JSONDecodeError):
        decode_json('{"value":1}'.encode("utf-16"))


def test_unterminated_escaped_quote_sequences_are_rejected():
    with pytest.raises(json.JSONDecodeError):
        decode_json(b'{"text":"' + b'\\"' * 5000)
