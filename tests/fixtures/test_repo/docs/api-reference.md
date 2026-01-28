---
title: API リファレンス
description: GitBook Translator の詳細な API 仕様
version: 1.0.0
---

# API リファレンス

GitBook Translator の内部 API とツールの詳細な仕様です。

## コマンドライン インターフェース

### 基本構文

```bash
python -m src.cli [OPTIONS]
```

### 必須パラメータ

| パラメータ | 型 | 説明 | 例 |
|-----------|----|----|-----|
| `--repo-url` | string | GitHub リポジトリ URL | `https://github.com/user/repo` |
| `--target-paths` | string[] | 対象ファイルのパターン | `"docs/**/*.md"` `"README.md"` |
| `--languages` | string[] | 翻訳先言語コード | `en` `zh-CN` `zh-TW` |
| `--glossary-path` | string | 用語集ファイルのパス | `./glossary.json` |

### オプションパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|----|---------|----|
| `--branch` | string | `main` | 対象ブランチ名 |
| `--output-root` | string | `./output` | 出力ディレクトリ |
| `--push-option` | enum | `none` | GitHub プッシュ方式 |
| `--output-naming` | enum | `suffix` | ファイル命名規則 |

## エージェント ツール

### FetchGitHubFilesTool

GitHub リポジトリからファイルを取得します。

```python
class FetchGitHubFilesTool(BaseTool):
    name = "fetch_github_files"
    description = "GitHub リポジトリから指定されたパターンのファイルを取得"
    
    def _run(self, repo_url: str, branch: str, target_paths: List[str]) -> List[FetchedFile]:
        # 実装詳細
        pass
```

**入力パラメータ:**
- `repo_url`: GitHub リポジトリ URL
- `branch`: ブランチ名
- `target_paths`: glob パターンのリスト

**出力:**
- `List[FetchedFile]`: 取得したファイルのリスト

### ParseMarkdownTool

Markdown ファイルを解析し、保護領域を特定します。

```python
class ParseMarkdownTool(BaseTool):
    name = "parse_markdown"
    description = "Markdown を解析し、翻訳対象と保護領域を分離"
    
    def _run(self, content: str) -> ParsedMarkdown:
        # 実装詳細
        pass
```

**保護領域の種類:**

1. **YAML frontmatter**
   ```yaml
   ---
   title: タイトル
   ---
   ```

2. **コードブロック**
   ```python
   def example():
       return "Hello"
   ```

3. **インラインコード**
   ```
   `const API_KEY = "secret"`
   ```

4. **GitBook タグ**
   ```
   {% hint style="info" %}
   ヒントテキスト
   {% endhint %}
   ```

5. **HTML 要素**
   ```html
   <div class="container">
   <p>コンテンツ</p>
   </div>
   ```

### TranslateContentTool

テキストを指定言語に翻訳します。

```python
class TranslateContentTool(BaseTool):
    name = "translate_content"
    description = "日本語テキストを指定言語に翻訳"
    
    def _run(self, segments: List[Segment], target_language: str, glossary: Glossary) -> TranslationResult:
        # 実装詳細
        pass
```

**翻訳プロンプト例:**

```
あなたは技術文書の専門翻訳者です。

タスク: 以下の日本語テキストを{target_language}に翻訳してください。

重要なルール:
1. 日本語テキストのみを翻訳し、他の言語は保持
2. フォーマット、改行、インデントを完全に保持
3. 保護領域（コード、URL、タグなど）は翻訳しない
4. フォーマル、丁寧、ビジネス適切なトーンを使用
5. 用語集の用語を正確に適用

用語集:
{glossary_terms}

翻訳対象セグメント:
{segments}
```

### ReviewTranslationTool

翻訳品質をレビューし、問題を特定します。

```python
class ReviewTranslationTool(BaseTool):
    name = "review_translation"
    description = "翻訳品質をレビューし、問題を分類"
    
    def _run(self, original: str, translated: str, target_language: str, glossary: Glossary) -> ReviewResult:
        # 実装詳細
        pass
```

**問題の重要度分類:**

| 重要度 | 説明 | 例 |
|--------|------|-----|
| `BLOCKER` | 構造破損、リンク破損、コンテンツ欠落 | Markdown テーブルの列数不一致 |
| `MAJOR` | 意味エラー、用語集違反、未翻訳日本語 | 用語集にない独自翻訳の使用 |
| `MINOR` | スタイル改善提案 | より自然な表現の提案 |

## データモデル

### FetchedFile

```python
@dataclass
class FetchedFile:
    path: str              # リポジトリ内の相対パス
    content: str           # ファイル内容
    commit_hash: str       # コミットハッシュ
    last_modified: datetime # 最終更新日時
```

### Segment

```python
@dataclass
class Segment:
    type: SegmentType      # PROTECTED または TRANSLATABLE
    content: str           # セグメント内容
    start_line: int        # 開始行番号
    end_line: int          # 終了行番号
    metadata: Optional[SegmentMetadata] = None
```

### Issue

```python
@dataclass
class Issue:
    severity: IssueSeverity    # BLOCKER, MAJOR, MINOR
    category: IssueCategory    # format, completeness, terminology, links, style
    location: IssueLocation    # 行番号と列番号
    description: str           # 問題の説明
    suggestion: Optional[str]  # 修正提案
```

## エラーコード

| コード | 説明 | 対処法 |
|--------|------|--------|
| `E001` | GitHub API 認証エラー | `GITHUB_TOKEN` を設定 |
| `E002` | リポジトリが見つからない | URL を確認 |
| `E003` | 用語集ファイルが見つからない | パスを確認 |
| `E004` | LLM API キーが未設定 | API キーを設定 |
| `E005` | 翻訳タイムアウト | `TRANSLATION_TIMEOUT` を増加 |

## 使用例

### 基本的な翻訳

```bash
python -m src.cli \
  --repo-url https://github.com/example/docs \
  --target-paths "**/*.md" \
  --languages en zh-CN \
  --glossary-path ./terms.json
```

### 高度な設定

```bash
python -m src.cli \
  --repo-url https://github.com/example/docs \
  --branch develop \
  --target-paths "docs/**/*.md" "README.md" \
  --languages en zh-CN zh-TW ko \
  --glossary-path ./glossary.json \
  --output-root ./translations \
  --output-naming directory \
  --push-option push_same_repo_new_branch
```

## パフォーマンス指標

### 処理時間の目安

| ファイルサイズ | 処理時間（目安） | トークン使用量（目安） |
|---------------|-----------------|---------------------|
| 1KB | 5-10秒 | 200-500 tokens |
| 10KB | 30-60秒 | 2,000-5,000 tokens |
| 100KB | 5-10分 | 20,000-50,000 tokens |

### 最適化のヒント

1. **差分検出の活用**: 未変更ファイルは自動スキップ
2. **保護領域の最大化**: コードブロックを適切にマーク
3. **用語集の整備**: 一貫した翻訳で修正回数を削減