"""Agent Stack A2A server — single orchestrator endpoint.

Starting with agentstack-sdk 0.7.x a `Server()` hosts exactly one agent. That's
fine here: the LangGraph orchestrator already routes to every specialist
(search / analysis / notification / database) internally. The specialists keep
their builder functions (used directly by the CLI + the graph nodes) but do
*not* get their own HTTP endpoints. If you ever need a specialist as a separate
A2A service, spin up a second process with its own `Server()`.
"""
from __future__ import annotations

import os

from a2a.types import Message
from a2a.utils.message import get_message_text
from agentstack_sdk.a2a.types import AgentMessage
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext

from .config import load_settings
from .mcp_clients import load_external_mcp_tools
from .orchestrator import build_orchestrator_graph

server = Server()


@server.agent()
async def orchestrator(input: Message, context: RunContext):
    """PaperBreaker entry point. LangGraph state machine routes every intent:
    search papers, analyze a paper, run today's digest, log an interaction,
    or just chat. Onboarding is triggered automatically when the profile is empty.
    """
    extra = await load_external_mcp_tools()
    graph = build_orchestrator_graph()
    result = await graph.ainvoke(
        {"input": get_message_text(input), "extra_tools": extra}
    )
    yield AgentMessage(text=result.get("response", ""))


def run() -> None:
    s = load_settings()
    server.run(host=os.getenv("HOST", s.host), port=int(os.getenv("PORT", s.port)))


if __name__ == "__main__":
    run()
