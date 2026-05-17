import json
from types import SimpleNamespace

import pytest

from mcp_bridge.openai_clients import streamChatCompletion

pytestmark = pytest.mark.unit


class FakeEvent:
    def __init__(self, data: str) -> None:
        self.event = "message"
        self.data = data
        self.id = None
        self.retry = None


class FakeResponse:
    headers = {"Content-Type": "text/event-stream"}
    url = "http://test/chat/completions"
    status_code = 200
    encoding = "utf-8"

    async def aread(self):
        return b""


class FakeEventSource:
    def __init__(self, events: list[str]) -> None:
        self.response = FakeResponse()
        self.events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def aiter_sse(self):
        for event in self.events:
            yield FakeEvent(event)


class FakeClientContext:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):
        return None


def tool_chunk(name: str, arguments: str, finish_reason=None) -> str:
    return json.dumps(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": name, "arguments": arguments},
                            }
                        ]
                    },
                    "finish_reason": finish_reason,
                }
            ],
        }
    )


def stop_chunk() -> str:
    return json.dumps(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "test-model",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )


def request_with_tool_names(tool_names: set[str] | None = None):
    request = SimpleNamespace(
        stream=False,
        messages=[],
        tools=[],
        model_dump=lambda **_: {"messages": [], "stream": True},
    )
    setattr(request, "_mcp_bridge_tool_names", tool_names or set())
    return request


async def return_request(request):
    return request


async def fake_call_tool(name: str, arguments: str):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="ok")],
        model_dump=lambda: {},
    )


@pytest.mark.asyncio
async def test_streaming_external_tool_call_replays_buffered_chunks(monkeypatch):
    chunk = tool_chunk("external_tool", '{"x":1}', "tool_calls")
    events = [chunk, "[DONE]"]
    monkeypatch.setattr(
        streamChatCompletion,
        "chat_completion_add_tools",
        return_request,
    )
    monkeypatch.setattr(
        streamChatCompletion,
        "get_client",
        lambda http_request: FakeClientContext(),
    )
    monkeypatch.setattr(
        streamChatCompletion,
        "aconnect_sse",
        lambda client, method, path, content: FakeEventSource(events),
    )

    outputs = [
        item
        async for item in streamChatCompletion.chat_completions(
            request_with_tool_names(), SimpleNamespace()
        )
    ]

    assert outputs[0] == chunk
    assert outputs[1].data == "[DONE]"


@pytest.mark.asyncio
async def test_streaming_mcp_tool_call_preserves_tool_call_id(monkeypatch):
    events_by_call = [
        [tool_chunk("mcp_tool", '{"x":1}', "tool_calls"), "[DONE]"],
        [stop_chunk(), "[DONE]"],
    ]
    monkeypatch.setattr(
        streamChatCompletion,
        "chat_completion_add_tools",
        return_request,
    )
    monkeypatch.setattr(
        streamChatCompletion,
        "get_client",
        lambda http_request: FakeClientContext(),
    )
    monkeypatch.setattr(
        streamChatCompletion,
        "aconnect_sse",
        lambda client, method, path, content: FakeEventSource(events_by_call.pop(0)),
    )
    monkeypatch.setattr(streamChatCompletion, "call_tool", fake_call_tool)
    request = request_with_tool_names({"mcp_tool"})

    outputs = [
        item
        async for item in streamChatCompletion.chat_completions(
            request, SimpleNamespace()
        )
    ]

    assistant_message = request.messages[0].model_dump(mode="json")
    tool_message = request.messages[1].model_dump(mode="json")
    assert assistant_message["tool_calls"][0]["id"] == "call_1"
    assert tool_message["tool_call_id"] == "call_1"
    assert outputs[-1].data == "[DONE]"
