"""Document ingestion: markdown manuals + drawing summaries (Phase 5)."""

from __future__ import annotations

import hashlib
from typing import Any

from deepdraw.tools.rag import (
    COLLECTION_DRAWINGS,
    COLLECTION_MANUALS,
    add_documents,
    get_client,
    get_or_create_collection,
)


def _doc_id(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += chunk_size - overlap
    return chunks


_DEFAULT_EMBEDDING_AGENT = "bom_generator"  # borrows the LLM profile's API key/URL


def get_default_embedding():
    """Lazy-load embeddings matching the active LLM profile.

    For ``openai`` and ``openai-compatible`` providers this returns an
    ``OpenAIEmbeddings`` instance using the same ``base_url`` / ``api_key``
    that the chat models use. For ``anthropic`` there is no native embedding
    endpoint — we fall back to OpenAI's official API and require
    ``OPENAI_API_KEY`` (or return ``None`` to disable embedding).

    Returns ``None`` if the integration package is missing or no key is set,
    so callers can degrade gracefully (Chroma will then use a local
    all-MiniLM stub via ``embedding_fn=None``).
    """
    try:
        from langchain_openai import OpenAIEmbeddings  # type: ignore[import-not-found]
    except Exception:
        return None

    # Reuse the active LLM profile so embeddings + chat share one endpoint.
    from deepdraw.llm import get_profile  # local import to avoid cycles

    profile = get_profile(_DEFAULT_EMBEDDING_AGENT)
    base_url = profile.extra.get("base_url")
    api_key = profile.extra.get("api_key") or _env_fallback("OPENAI_API_KEY")
    if not api_key:
        return None
    model = (
        "text-embedding-3-small"
        if profile.provider in {"openai", "openai-compatible"}
        else "text-embedding-3-small"
    )
    try:
        return OpenAIEmbeddings(model=model, api_key=api_key, base_url=base_url)
    except Exception:
        return None


def _env_fallback(key: str) -> str | None:
    import os

    return os.environ.get(key)


def ingest_text(
    collection_name: str,
    text: str,
    source: str = "inline",
    category: str = "general",
    embedding_fn=None,
) -> int:
    chunks = _chunk_text(text)
    docs = [
        {
            "id": _doc_id(f"{source}:{i}:{c[:50]}"),
            "text": c,
            "metadata": {"source": source, "category": category, "chunk_index": i},
        }
        for i, c in enumerate(chunks)
    ]
    client = get_client(persist=True)
    coll = get_or_create_collection(client, collection_name, embedding_fn=embedding_fn)
    add_documents(coll, docs)
    return len(docs)


def ingest_manual(
    name: str,
    content: str,
    category: str = "general",
    embedding_fn=None,
) -> int:
    return ingest_text(
        COLLECTION_MANUALS, content, source=name, category=category, embedding_fn=embedding_fn
    )


def ingest_drawing_summary(
    part_number: str,
    summary: str,
    process_plan: list[str],
    metadata: dict[str, Any] | None = None,
    embedding_fn=None,
) -> None:
    plan_str = "; ".join(process_plan)
    text = f"Part: {part_number}\nProcess: {plan_str}\n{summary}"
    doc = {
        "id": _doc_id(part_number),
        "text": text,
        "metadata": {"part_number": part_number, **(metadata or {})},
    }
    client = get_client(persist=True)
    coll = get_or_create_collection(client, COLLECTION_DRAWINGS, embedding_fn=embedding_fn)
    add_documents(coll, [doc])
