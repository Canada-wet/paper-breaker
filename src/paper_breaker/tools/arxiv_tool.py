from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import arxiv
from pydantic import BaseModel, Field

from beeai_framework.tools import Tool


class ArxivSearchInput(BaseModel):
    query: str = Field(..., description="Free-text search query, e.g. 'RLHF alignment'.")
    max_results: int = Field(10, ge=1, le=50)
    days_back: int = Field(
        7, ge=0, description="Only return papers published within the last N days. 0 = no limit."
    )


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    url: str
    pdf_url: str
    published_at: str  # ISO 8601
    categories: list[str]


class ArxivSearchTool(Tool):
    """Query the arXiv public API. Serialize calls with a 3s delay per arXiv's policy."""

    name = "arxiv_search"
    description = (
        "Search arXiv for papers by free-text query. Returns title, abstract, authors, "
        "arxiv_id, URLs, and publication date. Respects arXiv's 3-second-per-request rate limit."
    )
    input_schema = ArxivSearchInput

    def __init__(self) -> None:
        super().__init__()
        self._client = arxiv.Client(page_size=50, delay_seconds=3.0, num_retries=3)

    async def _run(self, input: ArxivSearchInput, *_: Any, **__: Any) -> list[dict]:
        return await asyncio.to_thread(self._search_sync, input)

    def _search_sync(self, input: ArxivSearchInput) -> list[dict]:
        search = arxiv.Search(
            query=input.query,
            max_results=input.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers: list[dict] = []
        from datetime import datetime, timezone, timedelta

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=input.days_back)
            if input.days_back > 0
            else None
        )

        for r in self._client.results(search):
            if cutoff and r.published < cutoff:
                continue
            arxiv_id = r.entry_id.rsplit("/", 1)[-1].split("v")[0]
            papers.append(
                ArxivPaper(
                    arxiv_id=arxiv_id,
                    title=r.title.strip(),
                    abstract=r.summary.strip(),
                    authors=[a.name for a in r.authors],
                    url=r.entry_id,
                    pdf_url=r.pdf_url,
                    published_at=r.published.isoformat(),
                    categories=r.categories,
                ).__dict__
            )
        return papers
