"""Vector DB + RAG retrieval for DeepDraw (Phase 5)."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb

PERSIST_DIR = Path(os.environ.get("DEEPDRAW_CHROMA_DIR", "./.chroma_db"))

COLLECTION_MANUALS = "enterprise_manuals"
COLLECTION_DRAWINGS = "historical_drawings"


def get_client(persist: bool = True):
    """Get ChromaDB client. EphemeralClient avoids macOS lock file issues in tests."""
    if persist:
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(PERSIST_DIR))
    return chromadb.EphemeralClient()


def get_or_create_collection(client, name: str, embedding_fn=None):
    """Get or create a collection with cosine distance.

    If no embedding_fn provided, uses ChromaDB's default ONNX MiniLM-L6 (~80MB).
    For prod use OpenAI or another embedding via embedding_fn param.
    """
    if embedding_fn is None:
        try:
            from chromadb.utils import embedding_functions
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        except Exception:
            pass  # tests may pass empty collection; query() will raise at runtime
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(collection, docs: list[dict]) -> None:
    if not docs:
        return
    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[d.get("metadata", {}) for d in docs],
    )


def query(collection, query_text: str, n_results: int = 3, where: dict | None = None) -> list[dict]:
    kwargs: dict = {"query_texts": [query_text], "n_results": n_results}
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    out: list[dict] = []
    docs = results.get("documents") or []
    if docs and docs[0]:
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]
        for i, doc in enumerate(docs[0]):
            out.append(
                {
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 0.0,
                }
            )
    return out


def format_results(results: list[dict], max_chars: int = 3000) -> str:
    out: list[str] = []
    total = 0
    for i, r in enumerate(results, 1):
        chunk = f"[{i}] {r['text'][:500]}"
        if total + len(chunk) > max_chars:
            break
        out.append(chunk)
        total += len(chunk)
    return "\n\n".join(out)
