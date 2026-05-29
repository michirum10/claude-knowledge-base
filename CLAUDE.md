# claude-knowledge-base

Anthropic公式情報を自動収集・ベクトルDB化し、RAG検索APIとして提供するシステム。

## プロジェクト構成

```
claude-knowledge-base/
├── .github/
│   └── workflows/
│       └── update.yml              # 毎日00:00 JST 自動実行
├── .claude/
│   └── skills/
│       ├── conventional-commit/
│       │   └── SKILL.md            # コミットメッセージ規約
│       ├── test-writer/
│       │   └── SKILL.md            # テスト実装方針
│       ├── venv-ops/
│       │   └── SKILL.md            # venv・ChromaDB操作
│       └── fetch-script/
│           └── SKILL.md            # 取得スクリプト実装方針
├── .vscode/
│   ├── extensions.json             # 推奨拡張機能
│   └── settings.json               # エディタ設定
├── scripts/
│   ├── fetch.py                    # 情報取得・Markdown整形
│   ├── embed.py                    # ベクトル化・ChromaDB登録
│   └── search_api.py               # FastAPI検索エンドポイント
├── knowledge/                      # 取得済みドキュメント
│   ├── docs/                       # APIドキュメント
│   ├── blog/                       # 公式ブログ
│   ├── release-notes/              # リリースノート
│   └── academy/                    # Academyコース（手動追加）
├── chroma-data/                    # ChromaDBデータ（ローカルファイルDB）
├── tests/
│   ├── conftest.py
│   ├── test_fetch.py
│   ├── test_embed.py
│   ├── test_search_api.py
│   ├── test_integration.py
│   └── test_e2e.py
├── docs/
│   ├── DESIGN.md                   # 設計書
│   └── TEST.md                     # テスト仕様書
├── venv/                           # Python仮想環境（Git管理外）
├── .env                            # APIキー等（Git管理外）
├── .gitignore
├── requirements.txt
├── CLAUDE.md                       # このファイル
└── README.md
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.11 |
| OS | Windows（ネイティブ） |
| シェル | PowerShell |
| 実行環境 | venv（Docker・WSL2不使用） |
| 取得 | requests / beautifulsoup4 / feedparser / tenacity |
| エンベディング | sentence-transformers (multilingual-e5-base) |
| ベクトルDB | ChromaDB（ローカルファイルDB・./chroma-data/） |
| 検索API | FastAPI / uvicorn（port: 8001） |
| CI/CD | GitHub Actions |

## 開発環境

- Windows ネイティブ Python + PowerShell
- APIキー: Windowsユーザー環境変数で管理
- FastAPI: `localhost:8001`
- Swagger UI: `http://localhost:8001/docs`

## 操作コマンド（PowerShell）

```powershell
# venv有効化（作業開始時に毎回）
.\venv\Scripts\Activate.ps1

# 取得・ベクトル化
python scripts/fetch.py
python scripts/embed.py

# 検索API起動
uvicorn scripts.search_api:app --reload --port 8001

# テスト実行
pytest tests/ -v

# venv無効化
deactivate
```

## APIキー管理

```powershell
# 確認
[System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")

# 設定（初回のみ）
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-xxxx", "User")
```

コードから参照：
```python
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
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

## スキル一覧

| スキル | 発動タイミング |
|--------|-------------|
| @.claude/skills/conventional-commit/ | コミット作業時 |
| @.claude/skills/test-writer/ | テストコード作成時 |
| @.claude/skills/venv-ops/ | venv・ChromaDB操作時 |
| @.claude/skills/fetch-script/ | fetch.py編集・ソース追加時 |

## 設計書

- @docs/DESIGN.md
- @docs/TEST.md
