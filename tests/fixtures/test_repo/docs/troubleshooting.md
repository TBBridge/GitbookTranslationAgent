# トラブルシューティング

GitBook Translator の使用中に発生する可能性のある問題と解決方法を説明します。

## よくある問題

### 1. 認証エラー

#### 問題: "GITHUB_TOKEN が設定されていません"

```
Error: GITHUB_TOKEN environment variable must be set
```

**解決方法:**

1. GitHub で Personal Access Token を作成
2. 環境変数に設定

```bash
export GITHUB_TOKEN=your_token_here
```

または `.env` ファイルに追加：

```bash
GITHUB_TOKEN=your_token_here
```

#### 問題: "API キーが無効です"

```
Error: Invalid OpenAI API key
```

**解決方法:**

API キーを確認し、正しく設定してください：

```bash
export OPENAI_API_KEY=sk-your-key-here
# または
export ANTHROPIC_API_KEY=your-anthropic-key
```

### 2. ファイル処理エラー

#### 問題: "対象ファイルが見つかりません"

```
Warning: No files matched the target paths
```

**原因と解決方法:**

| 原因 | 解決方法 |
|------|----------|
| glob パターンが間違っている | `"docs/**/*.md"` のように正しいパターンを使用 |
| ブランチが存在しない | `--branch` パラメータを確認 |
| リポジトリが空 | リポジトリにファイルが存在することを確認 |

**正しい glob パターンの例:**

```bash
# すべての Markdown ファイル
--target-paths "**/*.md"

# docs フォルダ内のみ
--target-paths "docs/**/*.md"

# 特定のファイル
--target-paths "README.md" "CHANGELOG.md"

# 複数パターンの組み合わせ
--target-paths "docs/**/*.md" "*.md"
```

#### 問題: "ファイルサイズが大きすぎます"

```
Error: File size exceeds maximum limit (1MB)
```

**解決方法:**

1. ファイルを分割して小さくする
2. 不要なセクションを削除
3. 大きなコードブロックを別ファイルに移動

### 3. 翻訳品質の問題

#### 問題: "用語集の用語が適用されていません"

**確認事項:**

1. **用語集ファイルの形式**

```json
{
  "terms": [
    {
      "ja": "ワークフロー",
      "en": "Workflow",
      "zh-CN": "工作流"
    }
  ]
}
```

2. **用語の完全一致**

用語集は完全一致で動作します：

```
✅ 正しい: "ワークフロー" → "Workflow"
❌ 間違い: "ワークフローの" → 一致しない
```

3. **言語コードの確認**

サポートされている言語コード：
- `en` (英語)
- `zh-CN` (簡体中文)
- `zh-TW` (繁體中文)
- `ko` (한국어)
- `fr` (Français)
- `de` (Deutsch)
- `es` (Español)

#### 問題: "翻訳が不自然です"

**改善方法:**

1. **用語集の充実**
   - 専門用語を追加
   - 製品名を統一

2. **コンテキストの改善**
   - 文章を短く分割
   - 曖昧な表現を避ける

3. **レビューループの活用**
   - システムが自動的に2回まで修正
   - 重要な問題は優先的に修正

### 4. パフォーマンスの問題

#### 問題: "処理が遅すぎます"

**最適化方法:**

1. **差分検出の活用**
   ```bash
   # 初回実行後、キャッシュファイルが作成される
   ls -la .gitbook-translator-cache.json
   ```

2. **対象ファイルの絞り込み**
   ```bash
   # 特定のディレクトリのみ処理
   --target-paths "docs/important/**/*.md"
   ```

3. **タイムアウト設定の調整**
   ```bash
   export TRANSLATION_TIMEOUT=600  # 10分に延長
   ```

#### 問題: "トークン使用量が多すぎます"

**削減方法:**

1. **保護領域の最大化**
   - コードブロックを適切にマーク
   - 不要な翻訳対象を除外

2. **差分処理の活用**
   - 変更されたファイルのみ処理
   - キャッシュファイルを削除しない

3. **ファイルサイズの最適化**
   - 大きなファイルを分割
   - 不要なコンテンツを削除

### 5. GitHub 連携の問題

#### 問題: "プッシュに失敗しました"

```
Error: Failed to push to GitHub repository
```

**確認事項:**

1. **権限の確認**
   - リポジトリへの書き込み権限
   - Personal Access Token のスコープ

2. **ブランチの状態**
   - ブランチが最新かどうか
   - コンフリクトの有無

3. **プッシュオプションの選択**
   ```bash
   # 安全な新ブランチ作成
   --push-option push_same_repo_new_branch
   
   # 直接プッシュ（要確認）
   --push-option push_same_repo_direct
   ```

#### 問題: "レート制限に達しました"

```
Error: GitHub API rate limit exceeded
```

**解決方法:**

1. **認証トークンの使用**
   - 未認証: 60 requests/hour
   - 認証済み: 5,000 requests/hour

2. **待機時間**
   - システムが自動的に指数バックオフで再試行
   - 手動で時間を置いて再実行

## デバッグ方法

### 1. 詳細ログの有効化

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your_langchain_key
```

### 2. ログファイルの確認

実行時のログを確認して問題を特定：

```
Starting GitBook Translator...
Repository: https://github.com/user/repo
Branch: main
Target paths: docs/**/*.md
Languages: en, zh-CN

[INFO] Fetching files from GitHub...
[INFO] Found 5 files matching patterns
[INFO] Detecting changes...
[INFO] 2 new files, 1 modified file, 2 unchanged files
[INFO] Loading glossary...
[INFO] Processing file: docs/intro.md (language: en)
[INFO] Parsing markdown...
[INFO] Translating content...
[INFO] Reviewing translation...
[WARN] Found 1 MAJOR issue: untranslated Japanese text
[INFO] Correcting translation...
[INFO] Review passed - translation approved
[INFO] Saving translation...
[INFO] File saved: output/docs/intro.en.md
```

### 3. テストモードの実行

小さなファイルでテスト実行：

```bash
python -m src.cli \
  --repo-url https://github.com/user/repo \
  --target-paths "README.md" \
  --languages en \
  --glossary-path ./glossary.json \
  --output-root ./test-output
```

## サポート

### 問題報告

以下の情報を含めて問題を報告してください：

1. **実行コマンド**
2. **エラーメッセージ**
3. **環境情報**
   - Python バージョン
   - OS
   - 依存関係のバージョン

### よくある質問

**Q: 翻訳にどのくらい時間がかかりますか？**

A: ファイルサイズと内容によりますが、1KB あたり 5-10秒程度です。

**Q: どの LLM を使用していますか？**

A: OpenAI GPT-4 または Anthropic Claude を使用できます。

**Q: オフラインで使用できますか？**

A: いいえ、GitHub API と LLM API への接続が必要です。

**Q: 翻訳品質を向上させるには？**

A: 用語集を充実させ、明確で簡潔な日本語を使用してください。