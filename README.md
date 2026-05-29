# claude-knowledge-base

Anthropic公式情報を自動収集・ベクトルDB化し、RAG検索APIとして提供するシステム。  
Claude Codeおよびコンテンツ制作のナレッジベースとして活用する。

## 概要

| 項目 | 内容 |
|------|------|
| 目的 | Anthropic公式情報の継続的な収集・検索基盤の構築 |
| 対象情報 | APIドキュメント / 公式ブログ / リリースノート / Academyコース |
| 更新頻度 | 毎日00:00 JST（GitHub Actions） |
| 検索方式 | ベクトル類似検索（RAG） |
| コスト | 完全無料（ローカルモデル・パブリックリポジトリ） |

## システム構成

```
[GitHub Actions / 毎日自動実行]
        │
        ▼
[fetch.py] ← 公式ソース取得・Markdown整形・チャンク分割
        │
        ▼
[embed.py] ← sentence-transformersでベクトル化
        │
        ▼
[ChromaDB] ← ベクトル永続化（./chroma_db/）
        │
        ▼
[search_api.py] ← FastAPI検索エンドポイント（ローカル起動）
        │
   ┌────┴────┐
   ▼         ▼
Claude Code  コンテンツ執筆
（質問応答）  （@参照）
```

## 技術スタック

| レイヤー | 技術 | 選定理由 |
|---------|------|---------|
| 言語 | Python 3.11 | 標準的・ライブラリ豊富 |
| 取得 | requests / beautifulsoup4 | 軽量・依存少 |
| エンベディング | sentence-transformers (multilingual-e5-base) | 日本語対応・完全無料 |
| ベクトルDB | ChromaDB | ローカル永続化・RAG定番 |
| 検索API | FastAPI | 軽量・OpenAPI自動生成 |
| CI/CD | GitHub Actions | パブリックリポジトリは無料無制限 |

## ディレクトリ構成

```
claude-knowledge-base/
├── .github/
│   └── workflows/
│       └── update.yml          # 自動更新ワークフロー
├── scripts/
│   ├── fetch.py                # ソース取得・整形
│   ├── embed.py                # ベクトル化・ChromaDB登録
│   └── search_api.py           # FastAPI検索エンドポイント
├── knowledge/
│   ├── docs/                   # APIドキュメント（Markdown）
│   ├── blog/                   # 公式ブログ記事
│   ├── release-notes/          # リリースノート
│   └── academy/                # Academyコース（手動追加）
├── chroma_db/                  # ChromaDBデータ（自動生成）
├── tests/
│   ├── test_fetch.py
│   ├── test_embed.py
│   └── test_search_api.py
├── docs/
│   ├── DESIGN.md               # 設計書
│   └── TEST.md                 # テスト仕様書
├── CLAUDE.md                   # Claude Code用索引
├── requirements.txt
└── README.md
```

## セットアップ

```bash
# リポジトリクローン
git clone https://github.com/{username}/claude-knowledge-base.git
cd claude-knowledge-base

# 依存パッケージインストール
pip install -r requirements.txt

# 初回データ取得・ベクトル化
python scripts/fetch.py
python scripts/embed.py

# 検索API起動
uvicorn scripts.search_api:app --reload
# → http://localhost:8000/docs でSwagger UI確認可能
```

## 検索APIの使い方

```bash
# クエリ例
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Claude Codeのサブエージェント機能", "top_k": 5}'
```

```json
{
  "results": [
    {
      "content": "...",
      "source": "docs/claude-code/subagents.md",
      "score": 0.91
    }
  ]
}
```

## Claude Codeでの使い方

```bash
# CLAUDE.mdを起点に参照
@CLAUDE.md

# 特定ドキュメントを直接参照
@knowledge/docs/claude-code/overview.md
```

## 自動更新の仕組み

GitHub Actionsが毎日00:00 JSTに以下を実行：

1. 各ソースから最新情報を取得
2. 前回取得分との差分を検出
3. 差分のみベクトル化してChromaDBに追加
4. `knowledge/`ディレクトリの変更をコミット・プッシュ

## 情報ソース一覧

| ソース | URL | 更新頻度 |
|--------|-----|---------|
| APIドキュメント全文 | docs.anthropic.com/llms-full.txt | 随時 |
| 公式ブログ | anthropic.com/news | 不定期 |
| リリースノート | github.com/anthropics/claude-code | 随時 |
| Cookbooks | github.com/anthropics/claude-cookbooks | 随時 |

## ライセンス

本リポジトリのコード（scripts/以下）はMITライセンス。  
`knowledge/`以下のコンテンツはAnthropicの利用規約に従う。
