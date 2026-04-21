"""NotificationAgent — runs daily, updates the digest for the landing page."""
from __future__ import annotations

from datetime import date

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.tools.think import ThinkTool

from ..config import load_settings
from ..memory import format_user_context_prompt, load_user_context
from .database import MatchPaperTool, UpsertDigestTool
from .search import build_search_agent


def build_notification_agent() -> RequirementAgent:
    settings = load_settings()
    ctx = load_user_context()
    today = date.today().isoformat()

    search_agent = build_search_agent()

    system = f"""You are **PaperBreaker/Notification**. You run on a daily cron.

Steps for today ({today}):
1. For each of Henry's active standing topics: {', '.join(ctx.active_topics) or '(none — fall back to his interests)'}.
2. For each topic, hand off to the SearchAgent to pull the top new papers from the last 24h.
3. Dedupe across topics using `match_paper_by_embedding`.
4. Pick the top 5 most promising papers for Henry (prioritise novelty + citation
   count + alignment with his goals — DO NOT include any in his recently
   dismissed list).
5. Write a 3-5 sentence `summary` that ties the day's papers to a theme.
6. Call `upsert_daily_digest` with user_id="{ctx.user_id}", date="{today}",
   the selected paper_ids, and the summary.

{format_user_context_prompt(ctx)}

Keep handoffs tight — one SearchAgent call per topic, not one per paper.
"""
    return RequirementAgent(
        llm=ChatModel.from_name(settings.llm_model_id),
        tools=[
            ThinkTool(),
            HandoffTool(search_agent, name="DelegateToSearch"),
            MatchPaperTool(),
            UpsertDigestTool(),
        ],
        role="NotificationAgent",
        instructions=system,
    )
