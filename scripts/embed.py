"""Markdownファイルのチャンク分割・ベクトル化・ChromaDB登録を行うモジュール。

``knowledge/`` 配下のMarkdownを読み込み、512トークン（overlap 50）でチャンク分割し、
sentence-transformers でベクトル化して ChromaDB（``./chroma-data/``）にupsertする。
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = "knowledge"

# 環境変数で差し替え可能な設定
DEFAULT_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_COLLECTION = "anthropic_docs"
DEFAULT_CHROMA_DIR = "./chroma-data"

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


@dataclass
class Document:
    """1つのMarkdownファイルを表すデータ構造。"""

    content: str
    source: str
    category: str = ""
    section: str = ""


@dataclass
class Chunk:
    """チャンク分割後の1断片を表すデータ構造。"""

    id: str
    content: str
    source: str
    category: str = ""
    section: str = ""
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


def get_model_name() -> str:
    """使用するエンベディングモデル名を返す（``EMBED_MODEL`` で差し替え可能）。"""
    return os.environ.get("EMBED_MODEL", DEFAULT_MODEL)


def get_chroma_dir() -> str:
    """ChromaDBの永続化パスを返す（``CHROMA_DIR`` で差し替え可能）。"""
    return os.environ.get("CHROMA_DIR", DEFAULT_CHROMA_DIR)


def get_collection_name() -> str:
    """ChromaDBコレクション名を返す（``CHROMA_COLLECTION`` で差し替え可能）。"""
    return os.environ.get("CHROMA_COLLECTION", DEFAULT_COLLECTION)


@lru_cache(maxsize=2)
def get_model(model_name: str | None = None):  # type: ignore[no-untyped-def]
    """SentenceTransformerモデルをロードする（同一名はキャッシュ）。

    Raises:
        Exception: モデルのロードに失敗した場合は送出してプロセスを止める。
    """
    from sentence_transformers import SentenceTransformer

    name = model_name or get_model_name()
    logger.info("モデルをロード中: %s", name)
    return SentenceTransformer(name)


def _is_e5(model_name: str) -> bool:
    """e5系モデルか判定する（passage/queryプレフィックスの要否判定に使う）。"""
    return "e5" in model_name.lower()


def embed_texts(texts: list[str], is_query: bool = False, model_name: str | None = None):  # type: ignore[no-untyped-def]
    """テキスト群をベクトル化する。e5系は ``passage:``/``query:`` を付与する。

    Args:
        texts: ベクトル化対象のテキスト群。
        is_query: 検索クエリの場合 ``True``（``query:`` を付与）。
        model_name: 使用するモデル名（省略時は環境変数）。

    Returns:
        ベクトルのリスト（list[list[float]]）。
    """
    name = model_name or get_model_name()
    model = get_model(name)
    if _is_e5(name):
        prefix = "query: " if is_query else "passage: "
        texts = [prefix + t for t in texts]
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """YAML Frontmatterを簡易パースし、(メタデータ, 本文) を返す。"""
    metadata: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()
            body = parts[2].lstrip("\n")
    return metadata, body


def load_documents(knowledge_dir: str = KNOWLEDGE_DIR) -> list[Document]:
    """``knowledge_dir`` 配下の全Markdownを読み込みDocumentのリストを返す。

    Args:
        knowledge_dir: 走査対象ディレクトリ。

    Returns:
        Documentオブジェクトのリスト（本文が空のファイルは除外）。
    """
    documents: list[Document] = []
    root = Path(knowledge_dir)
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        if not body.strip():
            continue
        documents.append(
            Document(
                content=body,
                source=str(path).replace("\\", "/"),
                category=metadata.get("category", ""),
                section=metadata.get("section", ""),
            )
        )
    return documents


def _make_chunk_id(source: str, chunk_index: int) -> str:
    """source と chunk_index から決定的なチャンクIDを生成する。"""
    return hashlib.md5(f"{source}::{chunk_index}".encode()).hexdigest()


def split_chunks(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    model_name: str | None = None,
) -> list[Chunk]:
    """Documentをトークン単位（overlapあり）でチャンク分割する。

    モデルのtokenizerでトークン化し、``chunk_size`` トークンの窓を
    ``chunk_size - overlap`` トークンずつスライドさせて分割する。
    これにより各チャンクは ``chunk_size`` トークン以内・隣接チャンク間に
    ``overlap`` トークンの重複を持つ。

    Args:
        documents: 分割対象のDocumentリスト。
        chunk_size: 1チャンクの最大トークン数。
        overlap: 隣接チャンク間の重複トークン数。
        model_name: tokenizer取得に使うモデル名（省略時は環境変数）。

    Returns:
        Chunkのリスト。
    """
    name = model_name or get_model_name()
    tokenizer = get_model(name).tokenizer
    stride = max(chunk_size - overlap, 1)

    chunks: list[Chunk] = []
    for doc in documents:
        token_ids = tokenizer.encode(doc.content, add_special_tokens=False)
        if not token_ids:
            continue
        index = 0
        start = 0
        while start < len(token_ids):
            window = token_ids[start : start + chunk_size]
            content = tokenizer.decode(window, skip_special_tokens=True).strip()
            if content:
                chunks.append(
                    Chunk(
                        id=_make_chunk_id(doc.source, index),
                        content=content,
                        source=doc.source,
                        category=doc.category,
                        section=doc.section,
                        chunk_index=index,
                        metadata={
                            "source": doc.source,
                            "category": doc.category,
                            "section": doc.section,
                            "chunk_index": index,
                        },
                    )
                )
                index += 1
            if start + chunk_size >= len(token_ids):
                break
            start += stride
    return chunks


def get_chroma_client(path: str | None = None):  # type: ignore[no-untyped-def]
    """ChromaDBのPersistentClientを生成する。

    Raises:
        Exception: 接続に失敗した場合は送出してプロセスを止める。
    """
    import chromadb

    return chromadb.PersistentClient(path=path or get_chroma_dir())


def get_or_create_collection(client=None, name: str | None = None):  # type: ignore[no-untyped-def]
    """コレクションを取得（なければ作成）する。距離関数はcosine。"""
    client = client or get_chroma_client()
    return client.get_or_create_collection(
        name=name or get_collection_name(),
        metadata={"hnsw:space": "cosine"},
    )


def embed_and_store(chunks: list[Chunk], collection=None, model_name: str | None = None) -> None:  # type: ignore[no-untyped-def]
    """チャンクをベクトル化しChromaDBにupsertする。

    Args:
        chunks: 登録対象のChunkリスト。
        collection: 登録先コレクション（省略時は既定コレクション）。
        model_name: 使用するモデル名（省略時は環境変数）。
    """
    if not chunks:
        logger.info("登録対象のチャンクがありません")
        return

    collection = collection if collection is not None else get_or_create_collection()
    embeddings = embed_texts(
        [c.content for c in chunks], is_query=False, model_name=model_name
    )
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[c.metadata for c in chunks],
        embeddings=embeddings,
    )
    logger.info("%d 件のチャンクをupsertしました", len(chunks))


def get_collection_stats(collection=None) -> dict:  # type: ignore[no-untyped-def]
    """コレクションの統計情報を返す。"""
    collection = collection if collection is not None else get_or_create_collection()
    return {
        "collection": collection.name,
        "total_documents": collection.count(),
    }


def main() -> None:
    """knowledge/配下を読み込み、チャンク化してChromaDBへ登録する。"""
    documents = load_documents()
    logger.info("%d 件のドキュメントを読み込みました", len(documents))
    chunks = split_chunks(documents)
    logger.info("%d 件のチャンクに分割しました", len(chunks))
    embed_and_store(chunks)
    logger.info("統計: %s", get_collection_stats())


if __name__ == "__main__":
    main()
