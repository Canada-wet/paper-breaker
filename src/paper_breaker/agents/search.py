"""SearchAgent — pulls AI papers from arXiv + Semantic Scholar and persists them."""
from __future__ import annotations

from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.backend import ChatModel
from beeai_framework.tools.think import ThinkTool

from ..config import load_settings
from ..memory import format_user_context_prompt, load_user_context
from ..tools import ArxivSearchTool, EmbeddingTool, SemanticScholarSearchTool
from .database import (
    UpsertPaperTool,
    UpsertVectorTool,
    MatchPaperTool,
)


def build_search_agent(extra_tools: list | None = None) -> RequirementAgent:
    settings = load_settings()
    ctx = load_user_context()
    system = f"""You are **PaperBreaker/Search**, a retrieval agent that finds AI papers
for Henry. For each query:

1. Call `arxiv_search` with the query and days_back=7 (or whatever the user specifies).
2. Call `semantic_scholar_search` for the same query to get citation-count signal.
3. Merge by title/arxiv_id, deduping by `match_paper_by_embedding` (threshold 0.92)
   so you don't store the same paper twice across sources.
4. For each new paper: call `upsert_paper`, then compute an embedding of
   "title + abstract" with the `embedding` tool, then call `upsert_vector`.
5. Return a short markdown list of the top 5 results you added (title, arxiv_id,
   1-line why-it's-interesting) ordered by Henry's likely interest.

{format_user_context_prompt(ctx)}

Never invent arxiv_ids. Never upsert a paper without a title.
"""
    tools = [
        ThinkTool(),
        ArxivSearchTool(),
        SemanticScholarSearchTool(),
        EmbeddingTool(),
        UpsertPaperTool(),
        UpsertVectorTool(),
        MatchPaperTool(),
    ]
    if extra_tools:
        tools.extend(extra_tools)
    return RequirementAgent(
        llm=ChatModel.from_name(settings.llm_model_id),
        tools=tools,
        role="SearchAgent",
        instructions=system,
    )
