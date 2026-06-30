"""Tests for ChromaDB RAG retrieval (Phase 5)."""

from __future__ import annotations

from deepdraw.tools.rag import (
    add_documents, format_results, get_client,
    get_or_create_collection, query,
)


def test_add_and_query_roundtrip():
    """add + query 完整闭环 (EphemeralClient 避 macOS lock)"""
    client = get_client(persist=False)
    coll = get_or_create_collection(client, "test_roundtrip")
    docs = [
        {"id": "1", "text": "Q235B 5mm 折弯 R5mm", "metadata": {"material": "Q235B"}},
        {"id": "2", "text": "AL6061 阳极氧化", "metadata": {"material": "AL6061"}},
    ]
    add_documents(coll, docs)
    results = query(coll, "折弯 Q235B", n_results=1)
    assert len(results) == 1
    assert "折弯" in results[0]["text"]


def test_query_empty_collection():
    """空 collection 召回返回空列表"""
    client = get_client(persist=False)
    coll = get_or_create_collection(client, "test_empty")
    results = query(coll, "anything", n_results=3)
    assert results == []


def test_format_results_truncates():
    """format_results 限制输出长度"""
    results = [{"text": "X" * 500, "metadata": {}, "distance": 0.1}] * 10
    formatted = format_results(results, max_chars=1000)
    assert len(formatted) <= 1000


def test_query_with_where_filter():
    """metadata filter 工作"""
    client = get_client(persist=False)
    coll = get_or_create_collection(client, "test_filter")
    docs = [
        {"id": "a", "text": "Q235B info", "metadata": {"category": "equipment"}},
        {"id": "b", "text": "process info", "metadata": {"category": "process"}},
    ]
    add_documents(coll, docs)
    results = query(coll, "info", n_results=5, where={"category": "process"})
    assert isinstance(results, list)