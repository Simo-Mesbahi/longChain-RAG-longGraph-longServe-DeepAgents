"""Concurrency admission must free capacity on every outcome, without reading rejected bodies."""

import asyncio

import pytest
from starlette.responses import Response

from ai_course.concurrency_limit import RequestConcurrencyLimit


def test_excess_work_is_rejected_while_health_stays_available():
    async def scenario():
        entered = []
        full = asyncio.Event()
        release = asyncio.Event()

        async def work(scope, receive, send):
            if scope["method"] == "POST":
                entered.append(True)
                if len(entered) == 2:
                    full.set()
                await release.wait()
            await Response(status_code=204)(scope, receive, send)

        async def receive():
            raise AssertionError("rejected requests must not read their body")

        async def discard(message):
            pass

        app = RequestConcurrencyLimit(work, max_concurrent=2)
        scope = {"type": "http", "method": "POST"}
        tasks = [asyncio.create_task(app(scope, receive, discard)) for _ in range(2)]
        await asyncio.wait_for(full.wait(), 1)
        messages = []

        async def collect(message):
            messages.append(message)

        await app(scope, receive, collect)
        assert messages[0]["status"] == 503
        assert (b"retry-after", b"1") in messages[0]["headers"]
        messages.clear()
        await app({"type": "http", "method": "GET", "path": "/health"}, receive, collect)
        assert messages[0]["status"] == 204
        release.set()
        await asyncio.gather(*tasks)
        await app(scope, receive, discard)
        assert len(entered) == 3

    asyncio.run(scenario())


def test_downstream_failure_and_task_cancellation_release_capacity():
    async def scenario():
        started = asyncio.Event()
        mode = ["failure"]

        async def work(scope, receive, send):
            if mode[0] == "failure":
                raise RuntimeError("downstream failure")
            if mode[0] == "wait":
                started.set()
                await asyncio.Event().wait()

        async def noop(*args):
            pass

        app = RequestConcurrencyLimit(work, max_concurrent=1)
        scope = {"type": "http", "method": "POST"}
        with pytest.raises(RuntimeError):
            await app(scope, noop, noop)
        mode[0] = "wait"
        task = asyncio.create_task(app(scope, noop, noop))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        mode[0] = "success"
        await app(scope, noop, noop)

    asyncio.run(scenario())


@pytest.mark.parametrize("limit", [True, 0, -1, 1.5])
def test_invalid_capacity_is_rejected(limit):
    with pytest.raises(ValueError):
        RequestConcurrencyLimit(None, max_concurrent=limit)
