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


def get_default_embedding():
    """Lazy-load OpenAI embeddings. None if unavailable."""
    try:
        from langchain_openai import OpenAIEmbeddings  # type: ignore[import-not-found]

        return OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception:
        return None


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
