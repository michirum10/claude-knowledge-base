# 設計書

**プロジェクト名**: claude-knowledge-base  
**バージョン**: 1.0.0  
**作成日**: 2026-05-26  
**ステータス**: 設計中

-----

## 開発環境

### 構成概要

|項目     |内容                      |
|-------|------------------------|
|ホストOS  |Windows + WSL2（Ubuntu）  |
|コンテナ   |Docker / Docker Compose |
|エディタ   |VSCode（Dev Containers拡張）|
|実装担当   |Claude Code / Codex     |
|設計・レビュー|Claude（claude.ai）       |

### 役割分担

|フェーズ |ツール           |用途                    |
|-----|--------------|----------------------|
|計画・設計|Claude        |アーキテクチャ検討・設計書作成・レビュー  |
|実装   |Claude Code   |スクリプト・テストコード・設定ファイルの生成|
|実装補完 |Codex         |コード補完・リファクタリング        |
|CI/CD|GitHub Actions|自動取得・ベクトル化・テスト実行      |

-----

### Docker構成

#### docker-compose.yml

```yaml
services:
  app:
    build: .
    container_name: claude-kb-app
    volumes:
      - .:/app                        # ソースコードをマウント
      - model-cache:/root/.cache      # sentence-transformersモデルキャッシュ
    ports:
      - "8001:8001"                   # FastAPI（ChromaDBの8000と競合回避）
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      chromadb:
        condition: service_healthy

  chromadb:
    image: chromadb/chroma:1.5.3      # バージョン固定（意図しないアップグレード防止）
    container_name: claude-kb-chroma
    volumes:
      - ./chroma-data:/data           # ベクトルデータ永続化
    ports:
      - "8000:8000"
    environment:
      - ANONYMIZED_TELEMETRY=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  model-cache:                        # sentence-transformersモデルを永続化
```

#### Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
```

#### ポート整理

|サービス    |コンテナポート|ホストポート|用途    |
|--------|-------|------|------|
|ChromaDB|8000   |8000  |ベクトルDB|
|FastAPI |8001   |8001  |検索API |

#### 起動手順

```bash
# 初回 / ビルド
docker compose up --build -d

# 初回データ取得・ベクトル化
docker compose exec app python scripts/fetch.py
docker compose exec app python scripts/embed.py

# ログ確認
docker compose logs -f app

# 停止
docker compose down
```

-----

### VSCode設定

#### 推奨拡張機能（.vscode/extensions.json）

```json
{
  "recommendations": [
    "ms-vscode-remote.remote-wsl",         // WSL2接続（必須）
    "ms-vscode-remote.remote-containers",  // Dev Containers（必須）
    "ms-azuretools.vscode-docker",         // Docker管理UI
    "ms-python.python",                    // Python基本
    "ms-python.vscode-pylance",            // 型チェック・補完
    "ms-python.black-formatter",           // コードフォーマット
    "charliermarsh.ruff",                  // Linter（flake8+isort代替）
    "ms-python.debugpy",                   // デバッガ
    "rangav.vscode-thunder-client",        // APIテストクライアント（Postman代替）
    "fastapi.fastapi-vscode",              // FastAPIルート一覧表示
    "github.vscode-github-actions"         // GitHub Actions構文チェック
  ]
}
```

#### Dev Container設定（.devcontainer/devcontainer.json）

```json
{
  "name": "claude-knowledge-base",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/app",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "charliermarsh.ruff",
        "ms-python.debugpy",
        "rangav.vscode-thunder-client",
        "fastapi.fastapi-vscode"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "[python]": {
          "editor.defaultFormatter": "ms-python.black-formatter",
          "editor.formatOnSave": true
        }
      }
    }
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

-----

### 推奨ライブラリ一覧（requirements.txt）

```
# 取得・整形
requests==2.32.*
beautifulsoup4==4.12.*
feedparser==6.0.*          # RSSフィード取得

# ベクトル化
sentence-transformers==3.*
torch==2.*                 # CPU版で十分

# ベクトルDB
chromadb==1.5.*            # docker-compose.ymlのバージョンと合わせる

# API
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.*

# テスト
pytest==8.*
pytest-cov
requests-mock
httpx                      # FastAPIテストクライアント

# 開発ツール
black
ruff
```

#### バージョン固定の方針

- `==x.y.*` でマイナーバージョンを固定（パッチは自動更新）
- ChromaDBはdocker-compose.ymlのイメージバージョンとクライアントを**必ず合わせる**
- sentence-transformersとtorchは組み合わせ依存があるため、更新時は両方確認

-----

### .gitignore 設定

```
# Python
__pycache__/
*.pyc
.venv/

# モデルキャッシュ（容量大・再ダウンロード可）
.cache/

# ChromaDBデータ（Gitで管理する場合はコメントアウト）
# chroma-data/

# 環境変数
.env
```

> **Note**: `chroma-data/` をGit管理する場合はサイズに注意。  
> 初期は数MB程度だが、ドキュメント増加で肥大化する可能性あり。  
> 肥大化した場合はGit LFSまたはGitHub Actionsでの再生成に切り替える。

-----

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
1. [要件定義](#2-要件定義)
1. [システム構成](#3-システム構成)
1. [コンポーネント設計](#4-コンポーネント設計)
1. [データ設計](#5-データ設計)
1. [API設計](#6-api設計)
1. [CI/CDパイプライン設計](#7-cicdパイプライン設計)
1. [エラーハンドリング設計](#8-エラーハンドリング設計)
1. [技術選定根拠](#9-技術選定根拠)

-----

## 1. プロジェクト概要

### 1.1 背景・目的

Claude.aiは学習データのカットオフ以降の最新情報を持たない。  
AnthropicはAPIドキュメント・ブログ・リリースノートを継続的に更新しているが、  
これらを手動で追跡するのはコストが高い。

本システムは以下を自動化する：

- Anthropic公式情報の定期取得・整形
- ベクトルDB（ChromaDB）への登録
- FastAPIによる意味検索エンドポイントの提供

### 1.2 スコープ

**対象（In Scope）**

- Anthropic公式ドキュメント・ブログ・リリースノートの取得
- テキストのチャンク分割・ベクトル化・ChromaDB登録
- 意味検索APIの提供
- GitHub Actionsによる自動更新

**対象外（Out of Scope）**

- Anthropic Academy動画コンテンツの自動取得
- 多言語翻訳の自動化
- クラウドデプロイ（ローカル運用のみ）
- 認証・認可機能

-----

## 2. 要件定義

### 2.1 機能要件

|ID    |要件                               |優先度   |
|------|---------------------------------|------|
|FR-001|llms-full.txtを取得しMarkdownに整形できること|Must  |
|FR-002|公式ブログ記事を取得・保存できること               |Must  |
|FR-003|GitHubリリースノートを取得・保存できること         |Must  |
|FR-004|テキストをチャンク分割しベクトル化できること           |Must  |
|FR-005|ChromaDBにベクトルを永続化できること           |Must  |
|FR-006|自然言語クエリで類似チャンクを検索できること           |Must  |
|FR-007|検索結果にソースURLとスコアを含めること            |Must  |
|FR-008|前回取得との差分のみ更新できること                |Should|
|FR-009|GitHub Actionsで毎日自動実行されること       |Must  |
|FR-010|FastAPI経由でHTTPリクエストで検索できること      |Must  |

### 2.2 非機能要件

|ID     |要件               |基準値                 |
|-------|-----------------|--------------------|
|NFR-001|検索レスポンスタイム       |2秒以内（top_k=5）       |
|NFR-002|取得スクリプトの実行時間     |10分以内               |
|NFR-003|運用コスト            |月額0円                |
|NFR-004|Python依存パッケージ    |requirements.txtで管理 |
|NFR-005|エラー発生時の通知        |GitHub Actionsのログに記録|
|NFR-006|ChromaDBデータのGit管理|chroma_db/をリポジトリに含める|

-----

## 3. システム構成

### 3.1 全体アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│                  GitHub Actions                  │
│  ┌────────────┐  ┌────────────┐                  │
│  │ fetch.py   │→ │ embed.py   │                  │
│  │ (取得・整形) │  │ (ベクトル化) │                  │
│  └────────────┘  └─────┬──────┘                  │
│                        │ commit & push            │
└────────────────────────┼────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   GitHubリポジトリ   │
              │  ┌───────────────┐  │
              │  │ knowledge/    │  │
              │  │ chroma_db/    │  │
              │  └───────────────┘  │
              └──────────┬──────────┘
                         │ git pull（手動 or 自動）
                         ▼
              ┌──────────────────────┐
              │    ローカル環境        │
              │  ┌────────────────┐  │
              │  │ search_api.py  │  │
              │  │ (FastAPI)      │  │
              │  └───────┬────────┘  │
              └──────────┼───────────┘
                    ┌────┴────┐
                    ▼         ▼
               Claude Code  ブラウザ
               （質問応答）  (Swagger UI)
```

### 3.2 データフロー

```
[取得フェーズ]
外部ソース → fetch.py → knowledge/{カテゴリ}/*.md

[ベクトル化フェーズ]
knowledge/*.md → チャンク分割（512トークン / overlap 50）
              → multilingual-e5-base でエンベディング生成
              → ChromaDB（chroma_db/）に保存

[検索フェーズ]
クエリ文字列 → エンベディング生成
            → ChromaDB でコサイン類似度検索
            → 上位k件を返却（content / source / score）
```

-----

## 4. コンポーネント設計

### 4.1 fetch.py

**責務**: 外部ソースからの情報取得・Markdown整形・ファイル保存

```python
# 公開インターフェース
fetch_llms_full_txt() -> None
    """
    docs.anthropic.com/llms-full.txt を取得し、
    セクション単位でknowledge/docs/*.mdに分割保存する。
    """

fetch_blog_posts() -> None
    """
    anthropic.com/news のRSSフィードを取得し、
    knowledge/blog/{YYYY-MM-DD}-{slug}.mdに保存する。
    """

fetch_release_notes() -> None
    """
    github.com/anthropics/claude-code のリリースノートを取得し、
    knowledge/release-notes/{tag}.mdに保存する。
    """

fetch_cookbooks() -> None
    """
    github.com/anthropics/claude-cookbooks のREADMEを取得し、
    knowledge/cookbooks/*.mdに保存する。
    """

is_updated(filepath: str, content: str) -> bool
    """
    前回保存内容とのハッシュ比較で差分を検出する。
    """
```

**処理フロー**

```
1. 各ソースにHTTP GETリクエスト
2. レスポンスをMarkdownに整形
3. is_updated()で差分確認
4. 差分あり → 上書き保存
5. 差分なし → スキップ（ログ出力）
6. 処理結果サマリをstdoutに出力
```

**エラー処理**

- HTTPエラー（4xx/5xx）: ログ出力後スキップ（他ソースの処理は継続）
- タイムアウト: 30秒で打ち切り・リトライ2回
- パースエラー: ログ出力後スキップ

-----

### 4.2 embed.py

**責務**: Markdownファイルのチャンク分割・ベクトル化・ChromaDB登録

```python
# 公開インターフェース
load_documents(knowledge_dir: str) -> list[Document]
    """
    knowledge/以下の全.mdファイルを読み込む。
    """

split_chunks(documents: list[Document]) -> list[Chunk]
    """
    テキストをチャンク分割する。
    chunk_size=512トークン / overlap=50トークン
    メタデータ: source（ファイルパス）/ section（見出し）
    """

embed_and_store(chunks: list[Chunk]) -> None
    """
    sentence-transformersでエンベディング生成し、
    ChromaDBのコレクション "anthropic_docs" に保存する。
    既存IDは上書き（upsert）。
    """

get_collection_stats() -> dict
    """
    登録済みドキュメント数・コレクション情報を返す。
    """
```

**チャンク分割仕様**

|パラメータ     |値        |理由                               |
|----------|---------|---------------------------------|
|chunk_size|512トークン  |multilingual-e5-baseの最大入力512に合わせる|
|overlap   |50トークン   |文脈の連続性を保持                        |
|分割基準      |改行・見出しを優先|意味的まとまりを維持                       |

-----

### 4.3 search_api.py

**責務**: FastAPIによるベクトル検索エンドポイントの提供

```python
# エンドポイント

POST /search
    """クエリに対して類似チャンクを返す"""
    Request:
        query: str          # 検索クエリ
        top_k: int = 5      # 返却件数（1〜20）
        category: str = ""  # カテゴリフィルタ（docs/blog/release-notes）
    Response:
        results: list[SearchResult]
            content: str    # チャンクテキスト
            source: str     # ファイルパス
            score: float    # 類似度スコア（0〜1）
            section: str    # セクション見出し

GET /health
    """ヘルスチェック・コレクション統計"""
    Response:
        status: str         # "ok"
        total_documents: int
        last_updated: str   # ISO8601

GET /sources
    """登録済みソース一覧"""
    Response:
        sources: list[str]
```

-----

### 4.4 CLAUDE.md

**責務**: Claude Codeが最初に読む索引ファイル

```markdown
# claude-knowledge-base 索引

## このリポジトリについて
Anthropic公式情報のRAGナレッジベース。
最終更新: {自動更新日時}

## 検索API
ローカルで `uvicorn scripts.search_api:app` を起動後、
POST http://localhost:8000/search で検索可能。

## ドキュメントカテゴリ
- @knowledge/docs/       # APIドキュメント
- @knowledge/blog/       # 公式ブログ
- @knowledge/release-notes/ # リリースノート
- @knowledge/academy/    # Academyコース（手動追加）

## よく参照するドキュメント
- @knowledge/docs/claude-code/overview.md
- @knowledge/docs/api/messages.md
- @knowledge/docs/build-with-claude/agents.md
```

-----

## 5. データ設計

### 5.1 knowledgeディレクトリ構造

```
knowledge/
├── docs/
│   ├── claude-code/
│   │   ├── overview.md
│   │   ├── cli-reference.md
│   │   └── ...
│   ├── api/
│   │   ├── messages.md
│   │   └── ...
│   └── build-with-claude/
│       ├── agents.md
│       └── ...
├── blog/
│   ├── 2026-05-01-claude-4-announcement.md
│   └── ...
├── release-notes/
│   ├── v2.1.0.md
│   └── ...
└── academy/
    └── （手動追加）
```

### 5.2 Markdownファイルのメタデータ形式

各ファイル先頭にFrontmatterを付与：

```yaml
---
source_url: https://docs.anthropic.com/en/docs/claude-code/overview
fetched_at: 2026-05-26T00:00:00+09:00
category: docs
section: claude-code
---
```

### 5.3 ChromaDBコレクション設計

|項目        |値                                       |
|----------|----------------------------------------|
|コレクション名   |anthropic_docs                          |
|エンベディングモデル|multilingual-e5-base                    |
|次元数       |768                                     |
|距離関数      |cosine                                  |
|メタデータフィールド|source / category / section / fetched_at|

-----

## 6. API設計

### 6.1 POST /search リクエスト/レスポンス例

**リクエスト**

```json
{
  "query": "Claude Codeでサブエージェントを使う方法",
  "top_k": 5,
  "category": "docs"
}
```

**レスポンス**

```json
{
  "results": [
    {
      "content": "サブエージェントはTask toolを使って...",
      "source": "knowledge/docs/claude-code/subagents.md",
      "score": 0.923,
      "section": "サブエージェントの基本"
    }
  ],
  "query": "Claude Codeでサブエージェントを使う方法",
  "total": 5,
  "elapsed_ms": 312
}
```

### 6.2 エラーレスポンス

```json
{
  "error": "ChromaDB collection not found",
  "detail": "embed.pyを先に実行してください",
  "status_code": 503
}
```

-----

## 7. CI/CDパイプライン設計

### 7.1 update.yml ワークフロー仕様

```yaml
トリガー:
  - schedule: cron '0 15 * * *'  # 毎日00:00 JST（UTC 15:00）
  - workflow_dispatch             # 手動実行

ジョブ: update
  実行環境: ubuntu-latest
  タイムアウト: 30分

ステップ:
  1. actions/checkout@v4
  2. actions/setup-python@v5 (python-version: '3.11')
  3. pip install -r requirements.txt
  4. python scripts/fetch.py       # 情報取得
  5. python scripts/embed.py       # ベクトル化
  6. git diff --quiet || git commit # 差分があればコミット
  7. git push
```

### 7.2 シークレット管理

|シークレット名     |用途       |必須     |
|------------|---------|-------|
|GITHUB_TOKEN|コミット・プッシュ|✅（自動付与）|

APIキー不要（ローカルモデルのみ使用）。

-----

## 8. エラーハンドリング設計

### 8.1 エラー分類と対応

|エラー種別        |発生箇所                    |対応                        |
|-------------|------------------------|--------------------------|
|HTTPタイムアウト   |fetch.py                |リトライ2回後スキップ・ログ出力          |
|HTTPステータスエラー |fetch.py                |スキップ・ログ出力（他ソース継続）         |
|パースエラー       |fetch.py                |スキップ・ログ出力                 |
|ChromaDB接続エラー|embed.py / search_api.py|例外送出・プロセス終了               |
|モデルロードエラー    |embed.py                |例外送出・プロセス終了               |
|クエリバリデーションエラー|search_api.py           |422 Unprocessable Entity返却|

### 8.2 ログ出力仕様

```
[INFO]  2026-05-26 00:01:23 fetch.py: llms-full.txt 取得完了 (2.3MB)
[INFO]  2026-05-26 00:01:45 fetch.py: blog 3件取得 (差分2件)
[WARN]  2026-05-26 00:01:50 fetch.py: cookbooks タイムアウト リトライ1/2
[ERROR] 2026-05-26 00:02:10 fetch.py: cookbooks 取得失敗 スキップ
[INFO]  2026-05-26 00:05:33 embed.py: 1,243チャンク登録完了
```

-----

## 9. 技術選定根拠

### 9.1 ベクトルDB: ChromaDB vs 代替案

|比較項目        |ChromaDB |Pinecone|Supabase pgvector|
|------------|---------|--------|-----------------|
|コスト         |無料       |有料      |無料枠あり            |
|ローカル動作      |✅        |❌       |❌                |
|Gitでのバージョン管理|✅（ファイルDB）|❌       |❌                |
|セットアップ      |pip一発    |API登録必要 |インスタンス設定必要       |
|Python統合    |◎        |○       |△                |

**選定理由**: 完全無料・ローカル動作・Gitバージョン管理が可能な点でChromaDBが最適。

### 9.2 エンベディングモデル: multilingual-e5-base vs 代替案

|比較項目   |multilingual-e5-base|text-embedding-3-small|all-MiniLM-L6-v2|
|-------|--------------------|----------------------|----------------|
|コスト    |無料                  |API従量課金               |無料              |
|日本語対応  |✅                   |✅                     |△               |
|最大トークン数|512                 |8191                  |256             |
|ベクトル次元数|768                 |1536                  |384             |
|ローカル動作 |✅                   |❌                     |✅               |

**選定理由**: 日本語対応・完全無料・ローカル動作の3条件を満たす唯一の選択肢。

### 9.3 検索API: FastAPI vs 代替案

|比較項目            |FastAPI    |Flask|CLIスクリプト|
|----------------|-----------|-----|--------|
|Swagger UI自動生成  |✅          |❌    |❌       |
|型バリデーション        |✅（Pydantic）|❌    |❌       |
|Claude Codeツール連携|✅          |✅    |△       |
|学習コスト           |低          |低    |最低      |

**選定理由**: Swagger UIによる動作確認のしやすさと、将来的なClaude Codeツール連携を考慮してFastAPIを選定。