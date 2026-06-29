# 旧来の用語集（glossary）ファイルからの移行

従来の単一ファイル形式の用語集は、言語別の辞書ファイルへ変換してください。

旧形式:

```json
{
  "terms": [
    {
      "ja": "帳票定義",
      "en": "Template Form",
      "zh-CN": "报表定义"
    }
  ]
}
```

新形式:

```text
dictionaries/default/
  dictionary_en.json
  dictionary_zh-cn.json
```

`dictionary_en.json`:

```json
{
  "帳票定義": "Template Form"
}
```

`dictionary_zh-cn.json`:

```json
{
  "帳票定義": "报表定义"
}
```

CLI およびワーカーの設定では `--dictionary-path ./dictionaries/default` を指定してください。
