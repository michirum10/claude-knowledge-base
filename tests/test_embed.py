"""embed.py の単体テスト（TC-E-001〜005）。"""

from __future__ import annotations

from pathlib import Path

from scripts import embed
from scripts.embed import (
    Chunk,
    Document,
    _make_chunk_id,
    get_or_create_collection,
    load_documents,
    split_chunks,
)


def _write_doc(rel_path: str, body: str) -> None:
    path = Path(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = "---\nsource_url: https://example.com\ncategory: docs\n---\n\n"
    path.write_text(frontmatter + body, encoding="utf-8")


def test_load_documents_reads_three_files():
    """TC-E-001: knowledge/配下の3ファイルをDocument3件として読み込む。"""
    _write_doc("knowledge/docs/a.md", "ドキュメントAの本文。")
    _write_doc("knowledge/docs/b.md", "ドキュメントBの本文。")
    _write_doc("knowledge/blog/c.md", "ブログCの本文。")

    documents = load_documents("knowledge")

    assert len(documents) == 3
    assert all(d.content.strip() for d in documents)


def test_split_chunks_boundary():
    """TC-E-002: 1024トークンが2チャンク以上・各チャンク512トークン以内。"""
    text = " ".join(f"tok{i}" for i in range(1024))
    documents = [Document(content=text, source="knowledge/docs/big.md")]

    chunks = split_chunks(documents, chunk_size=512, overlap=50)

    tokenizer = embed.get_model(embed.get_model_name()).tokenizer
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(tokenizer.encode(chunk.content)) <= 512


def test_split_chunks_overlap():
    """TC-E-003: 隣接チャンク間に50トークンの重複が存在する。"""
    text = " ".join(f"tok{i}" for i in range(1024))
    documents = [Document(content=text, source="knowledge/docs/big.md")]

    chunks = split_chunks(documents, chunk_size=512, overlap=50)
    tokenizer = embed.get_model(embed.get_model_name()).tokenizer

    first = tokenizer.encode(chunks[0].content)
    second = tokenizer.encode(chunks[1].content)
    assert first[-50:] == second[:50]


def test_embed_and_store_registers_three(test_chroma_client):
    """TC-E-004: チャンク3件をChromaDBに登録できる。"""
    collection = get_or_create_collection(client=test_chroma_client)
    chunks = [
        Chunk(
            id=_make_chunk_id(f"knowledge/docs/d{i}.md", 0),
            content=f"チャンク{i}の本文",
            source=f"knowledge/docs/d{i}.md",
            category="docs",
            chunk_index=0,
            metadata={"source": f"knowledge/docs/d{i}.md", "category": "docs"},
        )
        for i in range(3)
    ]

    embed.embed_and_store(chunks, collection=collection)

    assert collection.count() == 3


def test_embed_and_store_upsert(test_chroma_client):
    """TC-E-005: 同一IDのupsertで件数は変わらず内容が更新される。"""
    collection = get_or_create_collection(client=test_chroma_client)
    source = "knowledge/docs/same.md"
    cid = _make_chunk_id(source, 0)
    meta = {"source": source, "category": "docs"}

    original = Chunk(id=cid, content="最初の本文", source=source, metadata=meta)
    embed.embed_and_store([original], collection=collection)
    assert collection.count() == 1

    updated = Chunk(id=cid, content="更新後の本文", source=source, metadata=meta)
    embed.embed_and_store([updated], collection=collection)

    assert collection.count() == 1
    stored = collection.get(ids=[cid])
    assert stored["documents"][0] == "更新後の本文"
