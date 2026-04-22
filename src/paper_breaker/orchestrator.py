"""Orchestrator — LangGraph StateGraph routing user intents to specialist agents.

Why LangGraph (not BeeAI) for *just* this node:
- The orchestrator is the one piece that benefits from an explicit state machine:
  onboarding gate, intent classification, per-intent branch, and eventual
  interrupts/human-in-the-loop. BeeAI's `RequirementAgent + HandoffTool` works
  but hides the routing in tool-call decisions — hard to reason about or test.
- LangGraph keeps it deterministic and inspectable. Specialists stay BeeAI.
- The A2A boundary (Agent Stack `@server.agent()`) is the seam: whatever lives
  inside each endpoint is an implementation detail.

Graph shape:
    START → route → { onboard | search | analyze | notify | db | chat } → END

`route` is a single LLM call on Haiku that picks one of those six labels.
If `user_profile` is empty we force `onboard` regardless of the message.
Each branch node builds the corresponding BeeAI agent and runs it, preserving
the `extra_tools` (external MCP) flow unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from anthropic import AsyncAnthropic
from langgraph.graph import END, START, StateGraph

from .agents import (
    build_analysis_agent,
    build_database_agent,
    build_notification_agent,
    build_search_agent,
)
from .config import load_settings
from .memory import format_user_context_prompt, load_user_context

_ONBOARDING = (Path(__file__).parent / "prompts" / "onboarding.md").read_text()

INTENTS = ("search", "analyze", "notify", "db", "chat")


class OrchestratorState(TypedDict, total=False):
    input: str
    intent: str
    response: str
    extra_tools: list


def _strip_model_prefix(model_id: str) -> str:
    return model_id.split(":", 1)[1] if ":" in model_id else model_id


async def _classify(text: str, settings) -> str:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = (
        "You are a router. Read the user message and return JSON "
        '{"intent": "<one of: search, analyze, notify, db, chat>"}.\n'
        "- search: wants to find/pull papers on a topic.\n"
        "- analyze: wants a breakdown of a specific paper (arxiv_id / paper_id).\n"
        "- notify: wants to preview or re-trigger today's digest.\n"
        "- db: low-level CRUD or logging an interaction.\n"
        "- chat: general conversation, no delegation needed."
    )
    resp = await client.messages.create(
        model=_strip_model_prefix(settings.llm_cheap_model_id),
        max_tokens=64,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    raw = resp.content[0].text if resp.content else ""
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
        intent = str(parsed.get("intent", "chat")).lower().strip()
    except (ValueError, json.JSONDecodeError):
        intent = "chat"
    return intent if intent in INTENTS else "chat"


async def _run_beeai(agent, text: str) -> str:
    response = await agent.run(text)
    return response.last_message.text


async def route_node(state: OrchestratorState) -> dict:
    ctx = load_user_context()
    needs_onboarding = not (ctx.work_context and ctx.role)
    if needs_onboarding:
        return {"intent": "onboard"}
    intent = await _classify(state["input"], load_settings())
    return {"intent": intent}


async def onboard_node(state: OrchestratorState) -> dict:
    ctx = load_user_context()
    preface = (
        "Welcome to PaperBreaker. Before I can tailor analyses to your work, "
        "I need a bit about you. Please answer the questions below — you can "
        "also run `paper-breaker profile ...` from the CLI.\n\n"
    )
    return {"response": preface + _ONBOARDING + "\n\n" + format_user_context_prompt(ctx)}


def _make_specialist_node(builder):
    async def node(state: OrchestratorState) -> dict:
        agent = builder(extra_tools=state.get("extra_tools"))
        return {"response": await _run_beeai(agent, state["input"])}
    return node


search_node = _make_specialist_node(build_search_agent)
analyze_node = _make_specialist_node(build_analysis_agent)
notify_node = _make_specialist_node(build_notification_agent)
db_node = _make_specialist_node(build_database_agent)


async def chat_node(state: OrchestratorState) -> dict:
    settings = load_settings()
    ctx = load_user_context()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = (
        "You are PaperBreaker's conversational front-door. Answer directly and "
        "briefly. Mention that you can also search papers, analyze a paper by id, "
        "or preview today's digest if the user asks.\n\n"
        + format_user_context_prompt(ctx)
    )
    resp = await client.messages.create(
        model=_strip_model_prefix(settings.llm_model_id),
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": state["input"]}],
    )
    text = resp.content[0].text if resp.content else ""
    return {"response": text}


def build_orchestrator_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("route", route_node)
    g.add_node("onboard", onboard_node)
    g.add_node("search", search_node)
    g.add_node("analyze", analyze_node)
    g.add_node("notify", notify_node)
    g.add_node("db", db_node)
    g.add_node("chat", chat_node)

    g.add_edge(START, "route")
    g.add_conditional_edges(
        "route",
        lambda s: s["intent"],
        {
            "onboard": "onboard",
            "search": "search",
            "analyze": "analyze",
            "notify": "notify",
            "db": "db",
            "chat": "chat",
        },
    )
    for leaf in ("onboard", "search", "analyze", "notify", "db", "chat"):
        g.add_edge(leaf, END)
    return g.compile()
