from __future__ import annotations

import asyncio
import io
from typing import Any

import httpx
from pydantic import BaseModel, Field
from pypdf import PdfReader

from ._base import Tool


class PdfFetchInput(BaseModel):
    url: str = Field(..., description="Direct URL to a PDF (e.g. arxiv pdf_url).")
    max_pages: int = Field(40, ge=1, le=200, description="Safety limit to cap token use.")


class PdfFetchTool(Tool):
    """Download a PDF and extract plain text. No OCR — text-only PDFs."""

    name = "pdf_fetch"
    description = (
        "Download a PDF from a URL and extract its text. Returns the concatenated page text. "
        "Use this on paper pdf_url values so the AnalysisAgent can read the full manuscript."
    )
    input_schema = PdfFetchInput

    async def _run(self, input: PdfFetchInput, *_: Any, **__: Any) -> dict:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(input.url)
            resp.raise_for_status()
            data = resp.content
        text = await asyncio.to_thread(self._extract, data, input.max_pages)
        return {"url": input.url, "chars": len(text), "text": text}

    @staticmethod
    def _extract(data: bytes, max_pages: int) -> str:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:max_pages]
        return "\n\n".join((p.extract_text() or "") for p in pages)
