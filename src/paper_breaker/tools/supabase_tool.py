from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from ..config import Settings, load_settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Shared service-role client. Used by agents for writes."""
    s: Settings = load_settings()
    return create_client(s.supabase_url, s.supabase_service_key)


# -----------------------------------------------------------------------
# High-level helpers. These are plain async-friendly functions the
# DatabaseAgent exposes as BeeAI tools. Keeping them as functions (not
# classes) lets other agents call them directly for deterministic paths.
# -----------------------------------------------------------------------

def upsert_paper(paper: dict) -> dict:
    """Insert or update a paper row keyed on arxiv_id. Returns the stored row."""
    client = get_supabase()
    arxiv_id = paper.get("arxiv_id")
    payload = {k: v for k, v in paper.items() if v is not None}
    if arxiv_id:
        res = client.table("papers").upsert(payload, on_conflict="arxiv_id").execute()
    else:
        res = client.table("papers").insert(payload).execute()
    return res.data[0] if res.data else {}


def upsert_analysis(analysis: dict) -> dict:
    client = get_supabase()
    res = (
        client.table("paper_analyses")
        .upsert(analysis, on_conflict="paper_id")
        .execute()
    )
    return res.data[0] if res.data else {}


def upsert_vector(paper_id: str, embedding: list[float]) -> None:
    client = get_supabase()
    client.table("paper_vectors").upsert(
        {"paper_id": paper_id, "embedding": embedding}, on_conflict="paper_id"
    ).execute()


def match_paper_by_embedding(
    embedding: list[float], threshold: float = 0.85, count: int = 5
) -> list[dict]:
    client = get_supabase()
    res = client.rpc(
        "match_paper_by_embedding",
        {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": count,
        },
    ).execute()
    return res.data or []


def log_interaction(
    user_id: str, paper_id: str, type_: str, value: dict | None = None
) -> dict:
    client = get_supabase()
    res = (
        client.table("interactions")
        .insert(
            {"user_id": user_id, "paper_id": paper_id, "type": type_, "value": value}
        )
        .execute()
    )
    return res.data[0] if res.data else {}


def get_or_create_default_user(email: str | None = None) -> dict:
    """Return the single-user profile row, creating a blank one if it doesn't exist."""
    client = get_supabase()
    settings = load_settings()
    if settings.default_user_id:
        res = (
            client.table("user_profile").select("*").eq("id", settings.default_user_id).execute()
        )
        if res.data:
            return res.data[0]
    res = client.table("user_profile").select("*").limit(1).execute()
    if res.data:
        return res.data[0]
    created = (
        client.table("user_profile")
        .insert({"email": email, "interests": [], "tech_stack": []})
        .execute()
    )
    return created.data[0]


def update_user_profile(user_id: str, updates: dict) -> dict:
    client = get_supabase()
    res = (
        client.table("user_profile")
        .update({**updates, "updated_at": "now()"})
        .eq("id", user_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def get_active_topics(user_id: str) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("topics")
        .select("*")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute()
    )
    return res.data or []


def upsert_daily_digest(
    user_id: str, date: str, paper_ids: list[str], summary: str
) -> dict:
    client = get_supabase()
    res = (
        client.table("daily_digests")
        .upsert(
            {
                "user_id": user_id,
                "date": date,
                "paper_ids": paper_ids,
                "summary": summary,
            },
            on_conflict="user_id,date",
        )
        .execute()
    )
    return res.data[0] if res.data else {}


def recent_interactions(user_id: str, limit: int = 20) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("interactions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# -----------------------------------------------------------------------
# BeeAI Tool wrapper — exposes the handful of operations the DatabaseAgent
# advertises over A2A. Each operation is one Tool so the agent's tool list
# stays legible and the LLM picks the right call.
# -----------------------------------------------------------------------

from pydantic import BaseModel, Field

from ._base import Tool


class _UpsertPaperInput(BaseModel):
    paper: dict = Field(..., description="Paper dict with arxiv_id, title, abstract, authors, ...")


class SupabaseTool(Tool):
    """Umbrella tool exposing Supabase write ops.

    In practice the DatabaseAgent carries several *specialized* Tools (below);
    this class just exists so callers can `from .supabase_tool import SupabaseTool`
    and get the canonical upsert-paper op.
    """

    name = "upsert_paper"
    description = "Insert or update a paper row keyed on arxiv_id."
    input_schema = _UpsertPaperInput

    async def _run(self, input: _UpsertPaperInput, *_: Any, **__: Any) -> dict:
        return upsert_paper(input.paper)
