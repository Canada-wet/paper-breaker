"""FastMCP server exposing the paper-breaker tools to any MCP client.

Entry point: `paper-breaker-mcp` (stdio). Plug into Claude Code via .mcp.json
or into any other MCP-compatible client so you can call these tools
without going through the A2A agent layer.

Tools exposed (names mirror the BeeAI tools so agents + humans agree on naming):

  arxiv_search, semantic_scholar_search, pdf_fetch, embed,
  upsert_paper, upsert_analysis, upsert_vector, match_paper_by_embedding,
  log_interaction, update_user_profile, upsert_daily_digest,
  get_active_topics, recent_interactions, load_user_context.
"""
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP

from .memory import load_user_context as _load_user_context
from .tools import supabase_tool as st
from .tools.arxiv_tool import ArxivSearchInput, ArxivSearchTool
from .tools.embedding_tool import EmbeddingInput, EmbeddingTool
from .tools.pdf_fetch_tool import PdfFetchInput, PdfFetchTool
from .tools.semantic_scholar_tool import SemanticScholarInput, SemanticScholarSearchTool

mcp = FastMCP("paper-breaker")

# Instantiate once — these tools carry connection/model state.
_arxiv = ArxivSearchTool()
_s2 = SemanticScholarSearchTool()
_pdf = PdfFetchTool()
_embed = EmbeddingTool()


# ---------------------------------------------------------------
# Search / retrieval
# ---------------------------------------------------------------

@mcp.tool()
async def arxiv_search(query: str, max_results: int = 10, days_back: int = 7) -> list[dict]:
    """Search arXiv for recent papers matching a query.

    Returns a list of paper dicts: arxiv_id, title, abstract, authors, url, pdf_url,
    published_at, categories. Respects arXiv's 3-second rate limit.
    """
    return await _arxiv._run(
        ArxivSearchInput(query=query, max_results=max_results, days_back=days_back)
    )


@mcp.tool()
async def semantic_scholar_search(
    query: str, max_results: int = 10, year_from: int | None = None
) -> list[dict]:
    """Search Semantic Scholar. Returns dicts with citation_count for ranking."""
    return await _s2._run(
        SemanticScholarInput(query=query, max_results=max_results, year_from=year_from)
    )


@mcp.tool()
async def pdf_fetch(url: str, max_pages: int = 40) -> dict:
    """Download a PDF and extract its plain text. Returns {url, chars, text}."""
    return await _pdf._run(PdfFetchInput(url=url, max_pages=max_pages))


@mcp.tool()
async def embed(text: str) -> dict:
    """Embed a text snippet. Returns {embedding: list[float], dim: int}."""
    return await _embed._run(EmbeddingInput(text=text))


# ---------------------------------------------------------------
# Supabase CRUD (service-role — do not expose this MCP server publicly)
# ---------------------------------------------------------------

@mcp.tool()
def upsert_paper(paper: dict) -> dict:
    """Insert or update a paper row keyed on arxiv_id."""
    return st.upsert_paper(paper)


@mcp.tool()
def upsert_analysis(
    paper_id: str,
    sections: list[dict],
    insights: list[dict],
    henry_application: str,
    model: str,
) -> dict:
    """Insert or update the analysis row for a paper."""
    return st.upsert_analysis(
        {
            "paper_id": paper_id,
            "sections": sections,
            "insights": insights,
            "henry_application": henry_application,
            "model": model,
        }
    )


@mcp.tool()
def upsert_vector(paper_id: str, embedding: list[float]) -> dict:
    """Store or replace a paper's embedding for dedupe + similarity search."""
    st.upsert_vector(paper_id, embedding)
    return {"ok": True}


@mcp.tool()
def match_paper_by_embedding(
    embedding: list[float], threshold: float = 0.85, count: int = 5
) -> list[dict]:
    """Find papers whose embedding is above a cosine similarity threshold."""
    return st.match_paper_by_embedding(embedding, threshold, count)


@mcp.tool()
def log_interaction(
    user_id: str, paper_id: str, type: str, value: dict | None = None
) -> dict:
    """Record a user interaction. type ∈ viewed | saved | dismissed | rated | asked."""
    return st.log_interaction(user_id, paper_id, type, value)


@mcp.tool()
def update_user_profile(user_id: str, updates: dict) -> dict:
    """Merge fields into a user_profile row (role, work_context, interests, ...)."""
    return st.update_user_profile(user_id, updates)


@mcp.tool()
def upsert_daily_digest(
    user_id: str, date: str, paper_ids: list[str], summary: str
) -> dict:
    """Upsert today's digest row for the landing page."""
    return st.upsert_daily_digest(user_id, date, paper_ids, summary)


@mcp.tool()
def get_active_topics(user_id: str) -> list[dict]:
    """Return the user's active standing topics."""
    return st.get_active_topics(user_id)


@mcp.tool()
def recent_interactions(user_id: str, limit: int = 20) -> list[dict]:
    """Return the user's most recent interactions, newest first."""
    return st.recent_interactions(user_id, limit)


@mcp.tool()
def load_user_context() -> dict:
    """Hydrate the full Henry-context an agent would normally load at run start."""
    ctx = _load_user_context()
    return ctx.__dict__


def run() -> None:
    """Start the FastMCP server on stdio. Called by the paper-breaker-mcp script."""
    mcp.run()


if __name__ == "__main__":
    run()
