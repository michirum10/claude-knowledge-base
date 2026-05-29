# claude-knowledge-base

Anthropic公式情報を自動収集・ベクトルDB化し、RAG検索APIとして提供するシステム。

## プロジェクト構成

```
claude-knowledge-base/
├── .github/workflows/update.yml   # 毎日00:00 JST 自動実行
├── .claude/skills/                # Claude Codeスキル
├── scripts/
│   ├── fetch.py                   # 情報取得・Markdown整形
│   ├── embed.py                   # ベクトル化・ChromaDB登録
│   └── search_api.py              # FastAPI検索エンドポイント
├── knowledge/                     # 取得済みドキュメント
│   ├── docs/                      # APIドキュメント
│   ├── blog/                      # 公式ブログ
│   ├── release-notes/             # リリースノート
│   └── academy/                   # Academyコース（手動追加）
├── chroma-data/                   # ChromaDBデータ（Docker volume）
├── tests/
│   ├── conftest.py
│   ├── test_fetch.py
│   ├── test_embed.py
│   ├── test_search_api.py
│   ├── test_integration.py
│   └── test_e2e.py
├── docs/
│   ├── DESIGN.md                  # 設計書
│   └── TEST.md                    # テスト仕様書
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── CLAUDE.md                      # このファイル
└── README.md
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.11 |
| 取得 | requests / beautifulsoup4 / feedparser |
| エンベディング | sentence-transformers (multilingual-e5-base) |
| ベクトルDB | ChromaDB 1.5.3（Dockerコンテナ） |
| 検索API | FastAPI / uvicorn（port: 8001） |
| CI/CD | GitHub Actions |

## 開発環境

- WSL2（Ubuntu）+ Docker + VSCode Dev Containers
- ChromaDB: `localhost:8000`
- FastAPI: `localhost:8001`
- Swagger UI: `http://localhost:8001/docs`

## Docker操作

```bash
docker compose up --build -d          # 起動
docker compose exec app python scripts/fetch.py   # 取得実行
docker compose exec app python scripts/embed.py   # ベクトル化実行
docker compose logs -f app            # ログ確認
docker compose down                   # 停止
```

## コーディング規約

- フォーマッター: Black
- Linter: Ruff
- 型ヒント: 全関数に付与する
- docstring: 全公開関数に記載（日本語可）
- コミット: Conventional Commits形式（feat / fix / chore / docs / test）

## 実装方針

- エラーは例外を握りつぶさない。HTTPエラーはスキップ・ログ出力し他処理を継続
- ChromaDBへの登録はupsert（重複登録しない）
- チャンク分割: chunk_size=512 / overlap=50
- テストでは外部HTTP通信をすべてrequests-mockでモック化
- ChromaDBはテスト用一時コレクションを使用（本番コレクションを汚染しない）

## 設計書の参照先

詳細な仕様・技術選定根拠・テストケースは以下を参照：

- @docs/DESIGN.md
- @docs/TEST.md
