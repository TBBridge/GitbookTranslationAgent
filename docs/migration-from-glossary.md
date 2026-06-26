# Migration from legacy glossary files

Legacy single-file terminology should be converted to language-specific dictionary files.

Old style:

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

New style:

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

Use `--dictionary-path ./dictionaries/default` in CLI and worker configurations.
