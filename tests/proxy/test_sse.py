from __future__ import annotations

from local_mcp_gateway.proxy.sse import is_event_stream, parse_sse_json_payload


def test_parse_sse_json_payload_message_event() -> None:
    body = (
        b"event: message\n"
        b'data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"open_file"}]}}\n'
        b"\n"
    )
    payload = parse_sse_json_payload(body)
    assert payload is not None
    assert payload["result"]["tools"][0]["name"] == "open_file"


def test_is_event_stream() -> None:
    assert is_event_stream("text/event-stream")
    assert is_event_stream("text/event-stream; charset=utf-8")
    assert not is_event_stream("application/json")
