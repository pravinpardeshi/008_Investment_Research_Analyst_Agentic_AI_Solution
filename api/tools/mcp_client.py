import asyncio
import json
import logging
import threading
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._tools: list[dict[str, Any]] = []
        self._ready = False
        self._error: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self, command: str = "python3", module: str = "api.tools.mcp_server"):
        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect(command, module))
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        import time
        time.sleep(2)
        if self._error:
            logger.warning("MCP client error: %s", self._error)
        elif self._ready:
            logger.info("MCP client ready with %d tools", len(self._tools))
        else:
            logger.info("MCP client starting in background...")

    async def _connect(self, command: str, module: str):
        try:
            server_params = StdioServerParameters(
                command=command,
                args=["-m", module],
            )
            async with stdio_client(server_params) as (read, write):
                self._read = read
                self._write = write
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    result = await session.list_tools()
                    self._tools = [
                        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                        for t in result.tools
                    ]
                    self._ready = True
                    logger.info("MCP connected: %d tools available", len(self._tools))
                    while True:
                        await asyncio.sleep(3600)
        except Exception as e:
            self._error = str(e)
            logger.warning("MCP connection failed: %s", e)

    def list_tools(self) -> list[dict[str, Any]]:
        return self._tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if not self._ready or not self._session or not self._loop:
            return json.dumps({"error": "MCP client not connected", "tools_available": self._tools[:2]})
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._session.call_tool(name, arguments or {}),
                self._loop,
            )
            result = fut.result(timeout=30)
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
            return "\n".join(texts)
        except Exception as e:
            logger.warning("MCP tool call '%s' failed: %s", name, e)
            return json.dumps({"error": str(e)})

    def is_ready(self) -> bool:
        return self._ready


# Global singleton
_client: MCPClient | None = None


def get_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient()
        _client.start()
    return _client


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> str:
    try:
        client = get_client()
        return client.call_tool(name, arguments)
    except Exception as e:
        logger.warning("MCP call_tool failed: %s", e)
        return json.dumps({"error": str(e)})
