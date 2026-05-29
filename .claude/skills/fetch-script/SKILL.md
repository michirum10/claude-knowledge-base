---
name: fetch-script
description: fetch.pyを編集する・新しいソースを追加する・取得処理を実装するときに使用する。エラー処理・差分検出・Frontmatter付与の実装方針を提供する。
---

## 基本構造

fetch.pyの各取得関数は以下のパターンで実装する：

```python
def fetch_xxx() -> None:
    """
    XXXを取得しknowledge/{category}/に保存する。
    差分がない場合はスキップする。
    """
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        content = parse(response)
        filepath = Path(f"knowledge/{category}/{filename}.md")
        if is_updated(filepath, content):
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(add_frontmatter(content, url=URL))
            logger.info(f"{filepath} 更新")
        else:
            logger.info(f"{filepath} 差分なし スキップ")
    except requests.Timeout:
        logger.warning(f"タイムアウト: {URL}")
        # リトライはtenacity等で別途実装
    except requests.HTTPError as e:
        logger.error(f"HTTPエラー {e.response.status_code}: {URL} スキップ")
    except Exception as e:
        logger.error(f"予期しないエラー: {e} スキップ")
```

## 差分検出の実装

```python
import hashlib

def is_updated(filepath: Path, new_content: str) -> bool:
    """前回保存内容とのMD5ハッシュ比較で差分を検出する"""
    if not filepath.exists():
        return True
    existing = filepath.read_text()
    return hashlib.md5(existing.encode()).hexdigest() != \
           hashlib.md5(new_content.encode()).hexdigest()
```

## Frontmatterの付与

```python
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

def add_frontmatter(content: str, url: str, category: str) -> str:
    """Markdownの先頭にFrontmatterを付与する"""
    fetched_at = datetime.now(JST).isoformat()
    frontmatter = f"""---
source_url: {url}
fetched_at: {fetched_at}
category: {category}
---

"""
    return frontmatter + content
```

## リトライの実装

```python
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(requests.Timeout)
)
def fetch_with_retry(url: str) -> requests.Response:
    return requests.get(url, timeout=30)
```

## 情報ソース一覧

| ソース | URL | 保存先 |
|--------|-----|--------|
| APIドキュメント全文 | https://docs.anthropic.com/llms-full.txt | knowledge/docs/ |
| 公式ブログ | https://www.anthropic.com/news（RSS） | knowledge/blog/ |
| リリースノート | https://github.com/anthropics/claude-code/releases | knowledge/release-notes/ |
| Cookbooks | https://github.com/anthropics/claude-cookbooks | knowledge/cookbooks/ |

## してはいけないこと

- 1つのHTTPエラーで全体の処理を止める（他ソースの取得は継続する）
- Frontmatterなしでファイルを保存する（embed.pyがメタデータを読めなくなる）
- knowledge/以外のパスに保存する
