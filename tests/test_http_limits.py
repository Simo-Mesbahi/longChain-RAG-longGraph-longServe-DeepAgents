"""Exercise admission controls with ASGI streams, without network or model calls."""

import asyncio

import pytest

from ai_course.http_limits import RequestBodyLimit


def exchange(chunks, *, headers=(), max_bytes=5, timeout=1.0, delay=0.0, downstream_delay=0.0):
    observed, sent = [], []
    messages = iter(chunks)

    async def downstream(scope, receive, send):
        await asyncio.sleep(downstream_delay)
        observed.append(await receive())

    async def receive():
        await asyncio.sleep(delay)
        return next(messages)

    async def send(message):
        sent.append(message)

    async def execute():
        await asyncio.wait_for(
            RequestBodyLimit(downstream, max_bytes=max_bytes, body_timeout_seconds=timeout)(
                {"type": "http", "headers": list(headers)}, receive, send
            ),
            timeout=1.0,
        )

    asyncio.run(execute())
    return observed, sent


def test_oversized_declared_body_is_rejected_without_receiving_it():
    observed, sent = exchange([], headers=[(b"content-length", b"6")])
    assert not observed
    assert sent[0]["status"] == 413


@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-length", b"-1")],
        [(b"content-length", b"1,2")],
        [(b"content-length", b"1"), (b"content-length", b"1")],
        [(b"content-length", b"9" * 5000)],
    ],
)
def test_invalid_framing_is_rejected_before_application(headers):
    observed, sent = exchange([], headers=headers)
    assert not observed
    assert sent[0]["status"] == 400


def test_understated_length_does_not_bypass_actual_byte_count():
    observed, sent = exchange(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ],
        headers=[(b"content-length", b"1")],
    )
    assert not observed
    assert sent[0]["status"] == 413


def test_body_at_cap_is_replayed_exactly_once():
    observed, sent = exchange(
        [
            {"type": "http.request", "body": b"12", "more_body": True},
            {"type": "http.request", "body": b"345", "more_body": False},
        ]
    )
    assert observed == [{"type": "http.request", "body": b"12345", "more_body": False}]
    assert sent == []


def test_timeout_covers_the_whole_stream_and_prevents_application_work():
    observed, sent = exchange(
        [{"type": "http.request", "body": b"x", "more_body": True}] * 100,
        max_bytes=1000,
        timeout=0.02,
        delay=0.005,
    )
    assert not observed
    assert sent[0]["status"] == 408


def test_read_deadline_does_not_limit_inference_execution():
    observed, sent = exchange(
        [{"type": "http.request", "body": b"123", "more_body": False}],
        timeout=0.005,
        downstream_delay=0.03,
    )
    assert observed[0]["body"] == b"123"
    assert sent == []


def test_disconnected_client_does_not_start_application():
    observed, sent = exchange([{"type": "http.disconnect"}])
    assert observed == sent == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": 0},
        {"max_bytes": True},
        {"body_timeout_seconds": 0},
        {"body_timeout_seconds": float("nan")},
        {"body_timeout_seconds": True},
    ],
)
def test_invalid_limits_fail_fast(kwargs):
    with pytest.raises(ValueError):
        RequestBodyLimit(None, **kwargs)


def test_response_backpressure_is_not_mistaken_for_a_body_read_timeout():
    sent = []

    async def downstream(*args):
        raise AssertionError("Oversized body reached the application")

    async def receive():
        return {"type": "http.request", "body": b"123456", "more_body": False}

    async def send(message):
        await asyncio.sleep(0.02)
        sent.append(message)

    asyncio.run(
        RequestBodyLimit(downstream, max_bytes=5, body_timeout_seconds=0.005)(
            {"type": "http", "headers": []}, receive, send
        )
    )
    assert [message["status"] for message in sent if message["type"] == "http.response.start"] == [
        413
    ]
