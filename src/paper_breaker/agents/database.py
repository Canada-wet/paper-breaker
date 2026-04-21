"""DatabaseAgent — thin BeeAI wrapper over Supabase.

The heavy lifting is in `tools/supabase_tool.py`. Each write operation is
exposed as its own BeeAI Tool so the LLM can pick precisely what it needs.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.tools import Tool

from ..config import load_settings
from ..tools import supabase_tool as st


# -----------------------------------------------------------------------
# Per-operation Tools
# -----------------------------------------------------------------------

class _UpsertPaperInput(BaseModel):
    paper: dict = Field(..., description="Paper fields: arxiv_id, title, abstract, authors, url, pdf_url, published_at, source.")


class UpsertPaperTool(Tool):
    name = "upsert_paper"
    description = "Insert or update a paper keyed on arxiv_id."
    input_schema = _UpsertPaperInput

    async def _run(self, input: _UpsertPaperInput, *_: Any, **__: Any) -> dict:
        return st.upsert_paper(input.paper)


class _UpsertAnalysisInput(BaseModel):
    paper_id: str
    sections: list[dict]
    insights: list[dict]
    henry_application: str
    model: str


class UpsertAnalysisTool(Tool):
    name = "upsert_analysis"
    description = "Insert or update the analysis row for a paper."
    input_schema = _UpsertAnalysisInput

    async def _run(self, input: _UpsertAnalysisInput, *_: Any, **__: Any) -> dict:
        return st.upsert_analysis(input.model_dump())


class _UpsertVectorInput(BaseModel):
    paper_id: str
    embedding: list[float]


class UpsertVectorTool(Tool):
    name = "upsert_vector"
    description = "Store an embedding for a paper (for dedupe + similarity)."
    input_schema = _UpsertVectorInput

    async def _run(self, input: _UpsertVectorInput, *_: Any, **__: Any) -> dict:
        st.upsert_vector(input.paper_id, input.embedding)
        return {"ok": True}


class _MatchInput(BaseModel):
    embedding: list[float]
    threshold: float = 0.85
    count: int = 5


class MatchPaperTool(Tool):
    name = "match_paper_by_embedding"
    description = "Find papers whose embedding is above a cosine similarity threshold."
    input_schema = _MatchInput

    async def _run(self, input: _MatchInput, *_: Any, **__: Any) -> list[dict]:
        return st.match_paper_by_embedding(input.embedding, input.threshold, input.count)


class _InteractionInput(BaseModel):
    user_id: str
    paper_id: str
    type: str = Field(..., description="viewed | saved | dismissed | rated | asked")
    value: dict | None = None


class LogInteractionTool(Tool):
    name = "log_interaction"
    description = "Record a user interaction with a paper (viewed/saved/dismissed/rated/asked)."
    input_schema = _InteractionInput

    async def _run(self, input: _InteractionInput, *_: Any, **__: Any) -> dict:
        return st.log_interaction(input.user_id, input.paper_id, input.type, input.value)


class _ProfileUpdateInput(BaseModel):
    user_id: str
    updates: dict


class UpdateProfileTool(Tool):
    name = "update_user_profile"
    description = "Merge fields into the user_profile row (role, work_context, interests, ...)."
    input_schema = _ProfileUpdateInput

    async def _run(self, input: _ProfileUpdateInput, *_: Any, **__: Any) -> dict:
        return st.update_user_profile(input.user_id, input.updates)


class _DigestInput(BaseModel):
    user_id: str
    date: str
    paper_ids: list[str]
    summary: str


class UpsertDigestTool(Tool):
    name = "upsert_daily_digest"
    description = "Upsert the daily digest row for a given user + date."
    input_schema = _DigestInput

    async def _run(self, input: _DigestInput, *_: Any, **__: Any) -> dict:
        return st.upsert_daily_digest(
            input.user_id, input.date, input.paper_ids, input.summary
        )


def db_tools() -> list[Tool]:
    return [
        UpsertPaperTool(),
        UpsertAnalysisTool(),
        UpsertVectorTool(),
        MatchPaperTool(),
        LogInteractionTool(),
        UpdateProfileTool(),
        UpsertDigestTool(),
    ]


def build_database_agent() -> RequirementAgent:
    settings = load_settings()
    return RequirementAgent(
        llm=ChatModel.from_name(settings.llm_cheap_model_id),
        tools=db_tools(),
        role="DatabaseAgent",
        instructions=(
            "You persist and retrieve state for the paper-breaker system. "
            "Prefer deterministic tool calls; never invent IDs. If a required "
            "argument is missing, ask for it rather than guessing."
        ),
    )
