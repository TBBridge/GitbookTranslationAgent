---
title: 基本機能
description: GitBook Translatorの基本的な使用方法
---

# 基本機能

GitBook Translatorは、GitBook形式のMarkdownドキュメントを自動翻訳するツールです。

## 主な特徴

### 1. フォーマット保持

翻訳時に以下の要素を完全に保持します：

- **改行とインデント**: 元のレイアウトを維持
- **コードブロック**: プログラムコードは翻訳対象外
- **リンク**: URLと相対パスを保護
- **GitBook記法**: 専用タグとテンプレートを保護

### 2. 保護領域の検出

以下の領域は自動的に翻訳から除外されます：

```yaml
# YAML frontmatter
title: サンプルタイトル
description: 説明文
```

```javascript
// JavaScriptコード
function translateDocument(content) {
    return translator.process(content);
}
```

インラインコード: `const API_KEY = "your-key-here"`

### 3. GitBook専用記法

{% hint style="info" %}
**情報**: この機能は GitBook でのみ利用可能です。
{% endhint %}

{% tabs %}
{% tab title="JavaScript" %}
```javascript
const result = await translator.translate(text);
console.log(result);
```
{% endtab %}

{% tab title="Python" %}
```python
result = translator.translate(text)
print(result)
```
{% endtab %}
{% endtabs %}

## テーブル機能

| 機能名 | 説明 | 対応状況 |
|--------|------|----------|
| 基本翻訳 | 日本語テキストの翻訳 | ✅ 対応済み |
| フォーマット保持 | Markdown構造の維持 | ✅ 対応済み |
| 用語集対応 | 専門用語の統一 | ✅ 対応済み |
| 差分検出 | 変更ファイルのみ処理 | ✅ 対応済み |

## リンクと画像

- [内部リンク](../api-reference.md)
- [外部リンク](https://github.com/example/repo)
- [アンカーリンク](#主な特徴)

![サンプル画像](../images/sample.png "画像の説明")

## HTML要素

<div class="custom-container">
<p>カスタムHTMLコンテナ内のテキスト</p>
</div>

<span style="color: red;">赤色のテキスト</span>

## テンプレート記法

現在の日時: {{ "now" | date: "%Y-%m-%d" }}

ユーザー名: {{ user.name }}

{% include "shared/footer.md" %}