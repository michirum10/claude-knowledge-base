---
name: conventional-commit
description: git commitを作成する・コミットメッセージを書く・変更をコミットする、いずれかの作業時に使用する。Conventional Commits形式でメッセージを生成する。
---

## コミットメッセージのフォーマット

```
<type>(<scope>): <subject>

[body] （任意）
```

## type一覧

| type | 用途 |
|------|------|
| feat | 新機能追加 |
| fix | バグ修正 |
| chore | ビルド・依存関係・設定変更 |
| docs | ドキュメントのみの変更 |
| test | テストコードの追加・修正 |
| refactor | 機能変更を伴わないリファクタリング |
| perf | パフォーマンス改善 |
| ci | CI/CD設定の変更 |

## scope（このプロジェクト固有）

- `fetch` / `embed` / `api` / `docker` / `deps` / `actions`

## ルール

1. subjectは英語・命令形・50文字以内・末尾ピリオドなし
2. bodyは72文字で折り返す
3. 複数の変更は1コミットにまとめない

## 例

```
feat(api): add category filter to search endpoint

Allow filtering search results by knowledge category
(docs, blog, release-notes) via optional query parameter.
```

```
chore(deps): pin chromadb to 1.5.3
```

```
test(fetch): add mock for HTTP timeout retry
```

## してはいけないこと

- `update files` / `fix stuff` などの曖昧なメッセージ
- type・scopeを省略する
- 日本語のsubject（bodyは日本語可）
