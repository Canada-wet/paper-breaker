"""Orchestrator — routes user intents to the right specialist agent.

Uses HandoffTool for in-process delegation. For cross-process A2A, each
specialist is independently registered in `server.py` and is addressable via
the Agent Stack runtime at its own endpoint.
"""
from __future__ import annotations

from pathlib import Path

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.tools.think import ThinkTool

from .agents import (
    build_analysis_agent,
    build_database_agent,
    build_notification_agent,
    build_search_agent,
)
from .config import load_settings
from .memory import format_user_context_prompt, load_user_context


_ONBOARDING = (Path(__file__).parent / "prompts" / "onboarding.md").read_text()


def build_orchestrator() -> RequirementAgent:
    settings = load_settings()
    ctx = load_user_context()

    search = build_search_agent()
    analysis = build_analysis_agent()
    notif = build_notification_agent()
    db = build_database_agent()

    needs_onboarding = not (ctx.work_context and ctx.role)

    instructions = f"""You are **PaperBreaker**, the entry-point orchestrator. Route each
user message to the right specialist via the Handoff tools:

- `DelegateToSearch` — the user wants to find/pull papers on a topic.
- `DelegateToAnalysis` — the user wants a deep breakdown of a specific paper
  (they'll give you an arxiv_id or a paper_id).
- `DelegateToNotification` — the user wants to preview or re-trigger today's digest.
- `DelegateToDatabase` — low-level CRUD or logging an interaction.

If the user sends plain conversation, answer directly — don't delegate.

{'**ONBOARDING MODE** — the user profile is empty. Ask the onboarding questions below before anything else.' if needs_onboarding else ''}

{_ONBOARDING if needs_onboarding else ''}

{format_user_context_prompt(ctx)}
"""
    return RequirementAgent(
        llm=ChatModel.from_name(settings.llm_model_id),
        tools=[
            ThinkTool(),
            HandoffTool(search, name="DelegateToSearch"),
            HandoffTool(analysis, name="DelegateToAnalysis"),
            HandoffTool(notif, name="DelegateToNotification"),
            HandoffTool(db, name="DelegateToDatabase"),
        ],
        role="Orchestrator",
        instructions=instructions,
    )
