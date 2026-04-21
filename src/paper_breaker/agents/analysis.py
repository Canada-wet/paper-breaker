"""AnalysisAgent — breaks a paper into readable sections + a Henry-specific application."""
from __future__ import annotations

from pathlib import Path

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.tools.think import ThinkTool

from ..config import load_settings
from ..memory import format_user_context_prompt, load_user_context
from ..tools import EmbeddingTool, PdfFetchTool
from .database import UpsertAnalysisTool, UpsertVectorTool


_ANALYSIS_SYS = (Path(__file__).parent.parent / "prompts" / "analysis_system.md").read_text()


def build_analysis_agent(extra_tools: list | None = None) -> RequirementAgent:
    settings = load_settings()
    ctx = load_user_context()
    system = f"{_ANALYSIS_SYS}\n\n{format_user_context_prompt(ctx)}"
    tools = [
        ThinkTool(),
        PdfFetchTool(),
        EmbeddingTool(),
        UpsertAnalysisTool(),
        UpsertVectorTool(),
    ]
    if extra_tools:
        tools.extend(extra_tools)
    return RequirementAgent(
        llm=ChatModel.from_name(settings.llm_model_id),
        tools=tools,
        role="AnalysisAgent",
        instructions=system,
    )
