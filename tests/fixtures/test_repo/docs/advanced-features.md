# 高度な機能

このセクションでは、GitBook Translatorの高度な機能について説明します。

## 多言語対応

### サポート言語

GitBook Translatorは以下の言語への翻訳をサポートしています：

1. **英語** (en) - English
2. **中国語（簡体字）** (zh-CN) - 简体中文  
3. **中国語（繁体字）** (zh-TW) - 繁體中文
4. **韓国語** (ko) - 한국어
5. **フランス語** (fr) - Français
6. **ドイツ語** (de) - Deutsch
7. **スペイン語** (es) - Español

### 用語集機能

専門用語の一貫性を保つため、用語集ファイルを使用できます：

```json
{
  "terms": [
    {
      "ja": "ワークフロー",
      "en": "Workflow",
      "zh-CN": "工作流",
      "zh-TW": "工作流程"
    },
    {
      "ja": "ユーザーインターフェース",
      "en": "User Interface", 
      "zh-CN": "用户界面",
      "zh-TW": "使用者介面"
    }
  ]
}
```

## 差分検出システム

### キャッシュメカニズム

システムは `.gitbook-translator-cache.json` ファイルを使用して、前回の処理状況を記録します：

```json
{
  "version": "1.0",
  "lastRun": "2026-01-16T10:30:00Z",
  "files": [
    {
      "path": "docs/basic-features.md",
      "commitHash": "abc123def456",
      "lastModified": "2026-01-15T14:20:00Z",
      "translatedLanguages": ["en", "zh-CN"]
    }
  ]
}
```

### 処理最適化

- **新規ファイル**: 初回処理時に翻訳対象として追加
- **変更ファイル**: コミットハッシュの比較で検出
- **未変更ファイル**: スキップしてトークン消費を削減

## エラーハンドリング

### エラー分離

個別のファイルや言語でエラーが発生しても、他の処理は継続されます：

{% hint style="warning" %}
**注意**: ネットワークエラーや API 制限により、一部のファイルの翻訳が失敗する場合があります。
{% endhint %}

### 再試行メカニズム

- **GitHub API**: 指数バックオフで最大3回再試行
- **翻訳 API**: タイムアウト時に1回再試行
- **レビュー処理**: 最大2回の修正ループ

## パフォーマンス最適化

### トークン使用量の最適化

1. **保護領域の除外**: コードブロックやURLは翻訳対象外
2. **差分処理**: 変更されたファイルのみを処理
3. **セグメント化**: 大きなファイルを適切なサイズに分割

### 処理時間の短縮

- **並列処理**: 複数言語の同時処理（将来実装予定）
- **キャッシュ活用**: 未変更ファイルのスキップ
- **効率的なAPI呼び出し**: バッチ処理とレート制限の考慮

## 設定オプション

### 環境変数

```bash
# GitHub設定
GITHUB_TOKEN=your_github_token

# LLM設定
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# エージェント設定
MAX_ITERATIONS=50
MAX_CORRECTION_LOOPS=2
TRANSLATION_TIMEOUT=300
```

### 出力オプション

#### サフィックス形式
```
output/
├── docs/
│   ├── basic-features.en.md
│   ├── basic-features.zh-CN.md
│   └── advanced-features.en.md
└── README.en.md
```

#### ディレクトリ形式
```
output/
├── en/
│   ├── docs/
│   │   ├── basic-features.md
│   │   └── advanced-features.md
│   └── README.md
└── zh-CN/
    ├── docs/
    │   ├── basic-features.md
    │   └── advanced-features.md
    └── README.md
```