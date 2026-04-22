from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from ._base import Tool

from ..config import load_settings


class EmbeddingInput(BaseModel):
    text: str = Field(..., description="Text to embed. Typically title + abstract.")


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    settings = load_settings()
    return SentenceTransformer(settings.embedding_model)


class EmbeddingTool(Tool):
    """Produce a single embedding vector for arbitrary text.

    Default provider is `local` (sentence-transformers MiniLM, 384 dims) so no extra
    API key is needed. Swap to OpenAI / Voyage via EMBEDDING_PROVIDER in .env.
    """

    name = "embedding"
    description = (
        "Embed a text snippet to a numeric vector. Used for dedupe + similarity search "
        "over the paper_vectors table."
    )
    input_schema = EmbeddingInput

    async def _run(self, input: EmbeddingInput, *_: Any, **__: Any) -> dict:
        settings = load_settings()
        if settings.embedding_provider == "local":
            vec = await asyncio.to_thread(self._embed_local, input.text)
        else:
            raise NotImplementedError(
                f"Embedding provider '{settings.embedding_provider}' not wired up yet."
            )
        return {"embedding": vec, "dim": len(vec)}

    @staticmethod
    def _embed_local(text: str) -> list[float]:
        model = _local_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
