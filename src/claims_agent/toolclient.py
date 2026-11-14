"""MCP stdio client with the run's tool-call limit and retry policy. Synthetic data only."""
import json
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .checks import TOOL_NAMES


class ToolLimit(Exception):
    """The run's maximum number of tool calls was reached."""


class ToolClient:
    """Every attempt, including retries, counts toward max_calls.

    `faults` maps a tool name to a number of injected transient failures; it
    exists only so tests and the evaluation can exercise the retry path.
    """

    def __init__(self, data_dir, max_calls=12, max_retries=2, faults=None):
        self.data_dir, self.max_calls, self.max_retries = str(data_dir), max_calls, max_retries
        self.faults = dict(faults or {})
        self.calls, self.log = 0, []

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        env = {**os.environ, "CLAIMS_DATA_DIR": self.data_dir}
        params = StdioServerParameters(command=sys.executable, args=["-m", "claims_agent.server"], env=env)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def list_tools(self):
        return [{"name": t.name, "description": t.description} for t in (await self.session.list_tools()).tools]

    async def call(self, name):
        if name not in TOOL_NAMES:  # never forwarded to the server
            self.log.append({"tool": name, "outcome": "rejected_unknown_tool"})
            return {"tool": name, "error": "unknown_tool"}
        for attempt in range(1, self.max_retries + 2):
            if self.calls >= self.max_calls:
                self.log.append({"tool": name, "outcome": "blocked_by_tool_call_limit"})
                raise ToolLimit(name)
            self.calls += 1
            try:
                if self.faults.get(name, 0) > 0:
                    self.faults[name] -= 1
                    raise ConnectionError("injected transient failure")
                response = await self.session.call_tool(name, {})
                if response.isError:
                    raise RuntimeError("tool reported an error")
                result = json.loads(response.content[0].text)
            except Exception as error:  # transient by assumption; refusals are results, not exceptions
                self.log.append({"tool": name, "attempt": attempt, "outcome": "error", "error": type(error).__name__})
                continue
            self.log.append({"tool": name, "attempt": attempt, "outcome": "refused" if result.get("refused") else "ok"})
            return result
        return {"tool": name, "error": "tool_failed", "attempts": self.max_retries + 1}
