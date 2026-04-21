"""Agent Stack A2A server — exposes each specialist + the orchestrator as an endpoint."""
from __future__ import annotations

import os

from a2a.types import Message
from a2a.utils.message import get_message_text
from agentstack_sdk.a2a.types import AgentMessage
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext

from .agents import (
    build_analysis_agent,
    build_database_agent,
    build_notification_agent,
    build_search_agent,
)
from .config import load_settings
from .orchestrator import build_orchestrator

server = Server()


async def _delegate(agent, input: Message):
    text = get_message_text(input)
    response = await agent.run(text)
    return response.last_message.text


@server.agent()
async def orchestrator(input: Message, context: RunContext):
    """Main user-facing entry point. Use this for conversational requests."""
    agent = build_orchestrator()
    yield AgentMessage(text=await _delegate(agent, input))


@server.agent()
async def search(input: Message, context: RunContext):
    """Direct access to the SearchAgent (pulls papers from arXiv + S2)."""
    agent = build_search_agent()
    yield AgentMessage(text=await _delegate(agent, input))


@server.agent()
async def analysis(input: Message, context: RunContext):
    """Direct access to the AnalysisAgent (breaks a single paper down)."""
    agent = build_analysis_agent()
    yield AgentMessage(text=await _delegate(agent, input))


@server.agent()
async def notification(input: Message, context: RunContext):
    """Direct access to the NotificationAgent (daily digest). Called by pg_cron."""
    agent = build_notification_agent()
    yield AgentMessage(text=await _delegate(agent, input))


@server.agent()
async def database(input: Message, context: RunContext):
    """Direct access to the DatabaseAgent (logging interactions, profile updates)."""
    agent = build_database_agent()
    yield AgentMessage(text=await _delegate(agent, input))


def run() -> None:
    s = load_settings()
    server.run(host=os.getenv("HOST", s.host), port=int(os.getenv("PORT", s.port)))


if __name__ == "__main__":
    run()
