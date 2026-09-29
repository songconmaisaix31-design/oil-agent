"""Read-only Streamable HTTP MCP subset; server instructions never gain authority."""

import json
from collections.abc import Awaitable, Callable

from pydantic import SecretStr

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import canonical_json
from oil_agent.ingestion.http import PinnedHttpClient

VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")


def invalid(message="Invalid MCP provider response"):
    return ServiceError(ErrorCode.INVALID_OUTPUT, message)


def load_json(raw: bytes | str):
    def reject_constant(_):
        raise ValueError("Non-finite JSON number")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON property")
            result[key] = value
        return result

    def walk(value, depth=0):
        if depth > 32:
            raise ValueError("JSON nesting limit")
        if isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)
        if isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
        walk(value)
        return value
    except (ValueError, RecursionError, UnicodeError):
        raise invalid() from None


def sse_response(raw: bytes, request_id: int):
    # Only complete frames count. A disconnected partial result cannot advance a cursor.
    frames = raw.replace(b"\r\n", b"\n").split(b"\n\n")[:-1]
    if len(frames) > 64:
        raise invalid("MCP event count limit exceeded")
    result = None
    for frame in frames:
        lines = [line[5:].lstrip(b" ") for line in frame.split(b"\n") if line.startswith(b"data:")]
        if not lines or not b"".join(lines):
            continue
        message = load_json(b"\n".join(lines))
        if not isinstance(message, dict):
            raise invalid()
        if "method" in message:
            if "id" in message or message["method"] not in {
                "notifications/progress",
                "notifications/message",
            }:
                raise invalid("Unsupported server request or changed tool list")
            continue
        if type(message.get("id")) is not int or message["id"] != request_id or result is not None:
            raise invalid("MCP response identity mismatch")
        result = message
    return result


class FlashMcpSession:
    """One bounded fetch session, only list_flash; no tools selected by model/content."""

    def __init__(
        self,
        http: PinnedHttpClient,
        token: SecretStr,
        authorize: Callable[[], Awaitable[object]],
        context: CallContext,
    ):
        self.http, self._token, self.authorize, self.context = http, token, authorize, context
        self.session_id = None
        self.version = None
        self.sequence = 0

    async def request(self, method, params=None, *, notification=False):
        self.sequence += 1
        request_id = self.sequence
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params
        headers = {
            "Authorization": "Bearer " + self._token.get_secret_value(),
            "Accept": "application/json, text/event-stream",
        }
        if self.version:
            headers["MCP-Protocol-Version"] = self.version
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        response = await self.http.post(
            canonical_json(payload).encode(),
            headers=headers,
            context=self.context,
            authorize=self.authorize,
            complete=lambda raw: sse_response(raw, request_id) is not None,
        )
        if notification:
            if response.status != 202 or response.body:
                raise invalid("MCP notification was not accepted")
            return None
        if response.status != 200:
            raise invalid()
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type == "application/json":
            message = load_json(response.body)
        elif content_type == "text/event-stream":
            message = sse_response(response.body, request_id)
        else:
            raise invalid("Unsupported MCP response type")
        if (
            not isinstance(message, dict)
            or message.get("jsonrpc") != "2.0"
            or type(message.get("id")) is not int
            or message["id"] != request_id
            or "error" in message
            or not isinstance(message.get("result"), dict)
            or "method" in message
        ):
            raise invalid()
        session = response.headers.get("mcp-session-id")
        if method == "initialize" and session is not None:
            if not session or len(session) > 1024 or any(not 33 <= ord(c) <= 126 for c in session):
                raise invalid("Invalid MCP session header")
            self.session_id = session
        return message["result"]

    async def discover(self):
        initialized = await self.request(
            "initialize",
            {
                "protocolVersion": VERSIONS[0],
                "capabilities": {},
                "clientInfo": {"name": "oil-agent-readonly", "version": "0.1.0"},
            },
        )
        if (
            initialized.get("protocolVersion") not in VERSIONS
            or not isinstance(initialized.get("capabilities"), dict)
            or not isinstance(initialized["capabilities"].get("tools"), dict)
        ):
            raise invalid("MCP version or tools capability unsupported")
        self.version = initialized["protocolVersion"]
        await self.request("notifications/initialized", notification=True)
        cursor, seen, selected = None, set(), None
        for _ in range(3):
            result = await self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools = result.get("tools")
            if not isinstance(tools, list) or len(tools) > 100:
                raise invalid("Invalid MCP tools list")
            for tool in tools:
                if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                    raise invalid()
                if tool["name"] == "list_flash":
                    if selected is not None or not isinstance(tool.get("inputSchema"), dict):
                        raise invalid("Ambiguous list_flash tool schema")
                    selected = tool
            cursor = result.get("nextCursor")
            if cursor is None:
                if selected is None:
                    raise invalid("list_flash tool is unavailable")
                return selected
            if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048 or cursor in seen:
                raise invalid("MCP discovery cursor invalid")
            seen.add(cursor)
        raise invalid("MCP discovery page limit exceeded")

    async def flash(self, arguments: dict):
        result = await self.request("tools/call", {"name": "list_flash", "arguments": arguments})
        if result.get("isError", False) is not False:
            raise invalid("MCP flash tool failed")
        structured = result.get("structuredContent")
        content = result.get("content", [])
        if (
            not isinstance(content, list)
            or len(content) > 1
            or any(not isinstance(c, dict) or c.get("type") != "text" for c in content)
        ):
            raise invalid("Unexpected MCP flash content")
        text_result = (
            load_json(content[0]["text"])
            if content and isinstance(content[0].get("text"), str)
            else None
        )
        if structured is not None and text_result is not None and structured != text_result:
            raise invalid("Conflicting MCP flash representations")
        data = structured if structured is not None else text_result
        if not isinstance(data, dict):
            raise invalid("Missing MCP flash data")
        return data
