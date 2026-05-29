---
name: docker-ops
description: Dockerの操作・docker-compose.ymlの編集・コンテナのデバッグ・起動停止・ログ確認を行うときに使用する。
---

## コンテナ構成

| サービス | コンテナ名 | ポート | 用途 |
|---------|-----------|--------|------|
| app | claude-kb-app | 8001 | スクリプト実行・FastAPI |
| chromadb | claude-kb-chroma | 8000 | ベクトルDB |

## よく使うコマンド

```bash
# 起動（初回はビルドあり）
docker compose up --build -d

# 起動（ビルドなし）
docker compose up -d

# スクリプト実行
docker compose exec app python scripts/fetch.py
docker compose exec app python scripts/embed.py

# FastAPI起動
docker compose exec app uvicorn scripts.search_api:app --host 0.0.0.0 --port 8001 --reload

# テスト実行
docker compose exec app pytest tests/ -v

# ログ確認
docker compose logs -f app
docker compose logs -f chromadb

# 停止（データ保持）
docker compose down

# 停止（ボリューム削除・データリセット）
docker compose down -v

# コンテナ状態確認
docker compose ps

# ChromaDBヘルスチェック
curl http://localhost:8000/api/v2/heartbeat
```

## デバッグ手順

### FastAPIが起動しない場合
1. `docker compose logs app` でエラー確認
2. ChromaDBの起動待ちを確認（`depends_on: condition: service_healthy`）
3. ポート競合確認: `ss -tlnp | grep 8001`

### ChromaDBに接続できない場合
1. `docker compose ps` でchromadbコンテナがhealthyか確認
2. `curl http://localhost:8000/api/v2/heartbeat` でAPI疎通確認
3. docker-compose.ymlのCHROMA_HOSTが `chromadb`（コンテナ名）になっているか確認

### モデルのダウンロードが遅い場合
- model-cacheボリュームが機能しているか確認
- `docker volume ls` でvolume存在確認

## してはいけないこと

- `docker compose down -v` を本番データがある状態で実行する（chroma-dataが消える）
- ChromaDBのイメージバージョンを変更する際にクライアントバージョンを合わせずに更新する
