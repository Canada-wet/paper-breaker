from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field
from semanticscholar import SemanticScholar

from beeai_framework.tools import Tool


class SemanticScholarInput(BaseModel):
    query: str = Field(..., description="Free-text query passed to Semantic Scholar.")
    max_results: int = Field(10, ge=1, le=50)
    year_from: int | None = Field(
        None, description="Only papers published on or after this year."
    )


class SemanticScholarSearchTool(Tool):
    """Semantic Scholar search — complements arXiv with citation-count-aware ranking."""

    name = "semantic_scholar_search"
    description = (
        "Search Semantic Scholar. Returns title, abstract, authors, s2_id, arxiv_id (if any), "
        "year, and citation count — useful for ranking 'insightful' papers by citations."
    )
    input_schema = SemanticScholarInput

    def __init__(self) -> None:
        super().__init__()
        self._client = SemanticScholar()

    async def _run(self, input: SemanticScholarInput, *_: Any, **__: Any) -> list[dict]:
        return await asyncio.to_thread(self._search_sync, input)

    def _search_sync(self, input: SemanticScholarInput) -> list[dict]:
        results = self._client.search_paper(
            query=input.query,
            limit=input.max_results,
            year=f"{input.year_from}-" if input.year_from else None,
            fields=[
                "paperId",
                "title",
                "abstract",
                "authors",
                "year",
                "externalIds",
                "citationCount",
                "url",
                "openAccessPdf",
            ],
        )
        out: list[dict] = []
        for p in results[: input.max_results]:
            ext = p.externalIds or {}
            pdf = p.openAccessPdf or {}
            out.append(
                {
                    "s2_id": p.paperId,
                    "arxiv_id": ext.get("ArXiv"),
                    "title": (p.title or "").strip(),
                    "abstract": (p.abstract or "").strip(),
                    "authors": [a.name for a in (p.authors or [])],
                    "year": p.year,
                    "citation_count": p.citationCount or 0,
                    "url": p.url,
                    "pdf_url": pdf.get("url"),
                }
            )
        return out
