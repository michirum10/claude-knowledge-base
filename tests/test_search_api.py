"""search_api.py の単体テスト（TC-S-001〜006）。"""

from __future__ import annotations

from scripts import embed
from scripts.embed import Chunk, _make_chunk_id, get_or_create_collection


def _seed(count: int = 10, category: str = "docs") -> None:
    """アプリが参照するコレクションへチャンクを登録する。"""
    collection = get_or_create_collection()
    chunks = []
    for i in range(count):
        source = f"knowledge/{category}/doc{i}.md"
        chunks.append(
            Chunk(
                id=_make_chunk_id(source, 0),
                content=f"Claude Code のドキュメント {i} です。",
                source=source,
                category=category,
                section=f"section-{i}",
                chunk_index=0,
                metadata={
                    "source": source,
                    "category": category,
                    "section": f"section-{i}",
                },
            )
        )
    embed.embed_and_store(chunks, collection=collection)


def test_search_returns_top_k_results(api_client):
    """TC-S-001: 正常検索で200・results3件・各要素にcontent/source/score。"""
    _seed(10)

    response = api_client.post("/search", json={"query": "Claude Code", "top_k": 3})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3
    for result in data["results"]:
        assert "content" in result
        assert "source" in result
        assert "score" in result


def test_search_top_k_upper_bound(api_client):
    """TC-S-002: top_k=100 は 422。"""
    response = api_client.post("/search", json={"query": "test", "top_k": 100})
    assert response.status_code == 422


def test_search_empty_query(api_client):
    """TC-S-003: 空クエリは 422。"""
    response = api_client.post("/search", json={"query": "", "top_k": 5})
    assert response.status_code == 422


def test_search_category_filter(api_client):
    """TC-S-004: categoryフィルタで全resultsが該当カテゴリ配下になる。"""
    _seed(5, category="docs")
    _seed(5, category="blog")

    response = api_client.post(
        "/search", json={"query": "test", "top_k": 5, "category": "docs"}
    )

    assert response.status_code == 200
    for result in response.json()["results"]:
        assert result["source"].startswith("knowledge/docs/")


def test_health_check(api_client):
    """TC-S-005: /health が 200・status ok・total_documents を返す。"""
    _seed(3)

    response = api_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["total_documents"] == 3


def test_search_collection_not_initialized(api_client):
    """TC-S-006: コレクション未作成時は 503・案内文言を含む。"""
    response = api_client.post("/search", json={"query": "test", "top_k": 5})

    assert response.status_code == 503
    assert "embed.py" in response.json()["detail"]
