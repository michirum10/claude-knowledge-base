---
name: test-writer
description: テストを書く・テストコードを追加する・test_*.pyを作成・編集するときに使用する。pytestとrequests-mockを使ったテスト実装方針を提供する。
---

## テストフレームワーク

- pytest
- requests-mock（外部HTTP通信のモック）
- httpx（FastAPIテストクライアント）

## ファイル配置

```
tests/
├── conftest.py          # 共有フィクスチャ
├── test_fetch.py        # fetch.py単体テスト
├── test_embed.py        # embed.py単体テスト
├── test_search_api.py   # search_api.py単体テスト
├── test_integration.py  # 結合テスト
└── test_e2e.py          # E2Eテスト
```

## 必須フィクスチャ（conftest.py）

```python
@pytest.fixture
def mock_llms_txt():
    """llms-full.txtのモックレスポンスを返す"""

@pytest.fixture
def sample_chunks():
    """テスト用チャンクリスト（3件）を返す"""

@pytest.fixture
def test_chroma_client():
    """テスト用ChromaDBクライアント。テスト後にコレクションを削除する"""
    # コレクション名は "test_anthropic_docs" を使用（本番と分離）
    yield client
    client.delete_collection("test_anthropic_docs")

@pytest.fixture
def api_client():
    """FastAPIテストクライアント"""
    from httpx import TestClient
    from scripts.search_api import app
    return TestClient(app)
```

## モック方針

- 外部HTTP通信（requests）は**すべてrequests-mockでモック**する
- ChromaDBは**テスト用コレクション**（test_anthropic_docs）を使用する
- sentence-transformersモデルは環境変数 `EMBED_MODEL` で差し替え可能にする

```python
# 外部通信のモック例
def test_fetch_llms_txt(requests_mock):
    requests_mock.get(
        "https://docs.anthropic.com/llms-full.txt",
        text="# Claude Code\n\nサンプルドキュメント"
    )
    fetch_llms_full_txt()
    assert Path("knowledge/docs/overview.md").exists()
```

## テスト命名規則

```
test_{対象関数}_{条件}
例: test_fetch_llms_full_txt_success
    test_fetch_llms_full_txt_timeout_retry
    test_search_returns_top_k_results
```

## カバレッジ目標

- scripts/*.py: 80%以上
- `pytest --cov=scripts --cov-report=term-missing` で計測

## してはいけないこと

- 本番ChromaDBコレクション（anthropic_docs）に書き込む
- 実際の外部URLにHTTPリクエストを送る
- テスト間で状態を共有する（各テストは独立させる）
