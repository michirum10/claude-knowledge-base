"""ベクトル検索エンドポイントを提供するFastAPIアプリケーション。

ChromaDBに登録済みのチャンクに対し、自然言語クエリで類似検索を行う。
``POST /search`` / ``GET /health`` / ``GET /sources`` を公開する。
"""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scripts.embed import (
    embed_texts,
    get_chroma_client,
    get_collection_name,
)

app = FastAPI(title="claude-knowledge-base search API", version="1.0.0")

# ChromaDB未初期化時の案内文言
NOT_INITIALIZED_MESSAGE = (
    "ChromaDBコレクションが見つかりません。"
    "先に `python scripts/embed.py` を実行してベクトルDBを構築してください。"
)


class SearchRequest(BaseModel):
    """検索リクエストのスキーマ。"""

    query: str = Field(..., min_length=1, description="検索クエリ（空文字不可）")
    top_k: int = Field(5, ge=1, le=20, description="返却する上位件数（1〜20）")
    category: str | None = Field(None, description="カテゴリで絞り込む（任意）")


class SearchResult(BaseModel):
    """検索結果1件のスキーマ。"""

    content: str
    source: str
    score: float
    section: str | None = None


class SearchResponse(BaseModel):
    """検索レスポンスのスキーマ。"""

    results: list[SearchResult]
    total: int
    elapsed_ms: int


def _get_existing_collection():  # type: ignore[no-untyped-def]
    """既存コレクションを取得する。未作成なら503を送出する。"""
    try:
        client = get_chroma_client()
        return client.get_collection(get_collection_name())
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 未初期化を503へ変換
        raise HTTPException(status_code=503, detail=NOT_INITIALIZED_MESSAGE) from exc


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    """クエリに類似するチャンクを返す。"""
    started = time.perf_counter()
    collection = _get_existing_collection()

    query_embedding = embed_texts([request.query], is_query=True)
    where = {"category": request.category} if request.category else None

    response = collection.query(
        query_embeddings=query_embedding,
        n_results=request.top_k,
        where=where,
    )

    documents = response.get("documents") or [[]]
    metadatas = response.get("metadatas") or [[]]
    distances = response.get("distances") or [[]]

    results: list[SearchResult] = []
    for doc, meta, dist in zip(documents[0], metadatas[0], distances[0], strict=False):
        meta = meta or {}
        results.append(
            SearchResult(
                content=doc,
                source=str(meta.get("source", "")),
                # cosine距離 → 類似度スコアへ変換
                score=round(1.0 - float(dist), 4),
                section=meta.get("section") or None,
            )
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return SearchResponse(results=results, total=len(results), elapsed_ms=elapsed_ms)


@app.get("/health")
def health() -> dict:
    """ヘルスチェック。コレクションの登録件数を返す。"""
    collection = _get_existing_collection()
    return {"status": "ok", "total_documents": collection.count()}


@app.get("/sources")
def sources() -> dict:
    """登録済みのソース一覧を返す。"""
    collection = _get_existing_collection()
    data = collection.get(include=["metadatas"])
    metadatas = data.get("metadatas") or []
    unique_sources = sorted(
        {str(m.get("source", "")) for m in metadatas if m and m.get("source")}
    )
    return {"sources": unique_sources, "total": len(unique_sources)}
