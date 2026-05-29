---
name: venv-ops
description: venvの操作・有効化・無効化・パッケージ管理・ChromaDB操作・環境トラブルの解決を行うときに使用する。WindowsネイティブPython + PowerShell環境を前提とする。
---

## venv基本操作（PowerShell）

```powershell
# 有効化（作業開始時に毎回）
.\venv\Scripts\Activate.ps1

# 有効化確認（プロンプトに(venv)が表示されるか）
python -c "import sys; print(sys.executable)"
# → C:\...\venv\Scripts\python.exe が返ればOK

# 無効化
deactivate
```

> 実行ポリシーエラーが出た場合：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

## パッケージ管理

```powershell
# パッケージ追加
pip install {package}
pip freeze > requirements.txt  # 必ず更新する

# 全パッケージ一括インストール
pip install -r requirements.txt

# インストール済み確認
pip list
pip show {package}
```

## venv再作成（環境が壊れた場合）

```powershell
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## APIキー確認・設定

```powershell
# 確認
[System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")

# 設定（初回のみ・設定後はPowerShell再起動が必要）
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-xxxx", "User")

# 現在のセッションで即時反映（再起動不要）
$env:ANTHROPIC_API_KEY = "sk-ant-xxxx"
```

## ChromaDB操作

```powershell
# データ確認
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma-data')
col = client.get_collection('anthropic_docs')
print(f'登録件数: {col.count()}')
"

# データリセット（再ベクトル化が必要）
Remove-Item -Recurse -Force chroma-data
python scripts/embed.py
```

## FastAPI起動・確認

```powershell
# 起動
uvicorn scripts.search_api:app --reload --port 8001

# ヘルスチェック（別のPowerShellで）
Invoke-RestMethod http://localhost:8001/health

# 検索テスト
Invoke-RestMethod -Method POST http://localhost:8001/search `
  -ContentType "application/json" `
  -Body '{"query": "Claude Code", "top_k": 3}'

# Swagger UI → ブラウザで http://localhost:8001/docs
```

## トラブルシューティング

### ModuleNotFoundError
```powershell
# venvが有効か確認
python -c "import sys; print(sys.executable)"
# venv有効化後に再インストール
pip install -r requirements.txt
```

### ChromaDBコレクションが見つからない
```powershell
python scripts/embed.py  # embed.pyを先に実行
```

### ポート8001が使用中
```powershell
netstat -ano | findstr :8001
taskkill /PID {PID} /F
```

## してはいけないこと

- venvを有効化せずにpip installする（システムPythonが汚染される）
- APIキーをコードやGitにコミットする
- chroma-data/を誤って削除する（再ベクトル化が必要になる）
- requirements.txtを更新せずにパッケージを追加する
