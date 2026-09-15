from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app
from app.runs.bus import StreamBus


def parse_sse(body: str) -> list[dict[str, object]]:
    messages = []
    for block in body.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if line.startswith(":"):
                continue
            key, _, value = line.partition(": ")
            fields[key] = value
        if "data" in fields:
            messages.append(
                {"id": fields["id"], "event": fields["event"], "data": json.loads(fields["data"])}
            )
    return messages


def fake(seq: int, type_: str = "task.progress") -> dict[str, object]:
    return {"event_id": f"e{seq}", "run_id": "r", "seq": seq, "type": type_}


async def test_stream_format_order_and_resume(tmp_path: Path) -> None:
    app = create_app(Settings(runs_dir=tmp_path / "runs", agent_mode="stub"))
    bus: StreamBus = app.state.bus
    bus.open("s1")
    for seq in range(1, 5):
        bus.publish("s1", fake(seq))
    bus.publish("s1", fake(5, "run.terminated"))
    bus.close("s1")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        full = parse_sse((await client.get("/api/streams/s1/events")).text)
        assert [m["id"] for m in full] == ["1", "2", "3", "4", "5"]
        assert full[-1]["event"] == "run.terminated"
        resumed = parse_sse((await client.get("/api/streams/s1/events?since=3")).text)
        assert [m["id"] for m in resumed] == ["4", "5"]
        by_header = parse_sse(
            (await client.get("/api/streams/s1/events", headers={"Last-Event-ID": "4"})).text
        )
        assert [m["id"] for m in by_header] == ["5"]


async def test_bus_never_duplicates_live_events() -> None:
    bus = StreamBus()
    bus.open("s")
    bus.publish("s", fake(1))
    received: list[int] = []

    async def reader() -> None:
        async for event in bus.subscribe("s", since_seq=0):
            received.append(int(event["seq"]))

    import asyncio

    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    bus.publish("s", fake(2))
    bus.publish("s", fake(3))
    bus.close("s")
    await asyncio.wait_for(task, 2)
    assert received == [1, 2, 3]
