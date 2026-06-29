# ローカルワーカーのセットアップ

ローカルワーカーは Vercel コントロールプレーンをポーリングし、1 度に 1 件ずつジョブをリースして、Python の翻訳パイプラインをローカルで実行し、進捗を Web アプリへ報告します。

## 設定

サンプルをコピーします。

```bash
cp worker.example.toml worker.toml
```

シェルまたは `.env.local` 相当の場所にシークレットを設定します。

```bash
export WORKER_TOKEN="$(openssl rand -hex 32)"
```

Vercel 側の `WORKER_TOKEN` と同じ値を使用してください。

## 実行

```bash
gitbook-translator worker --config worker.toml
```

ポーリングを 1 サイクルだけ実行する場合:

```bash
gitbook-translator worker --config worker.toml --once
```

ワーカーは、辞書セット名・出力ルート名・プロバイダ名・モデル・言語を申告します。ローカルのファイルパスやプロバイダのシークレットをコントロールプレーンへ送信することは一切ありません。

## Ollama の境界

Ollama はローカルマシン上で動作します。`base_url` は `http://127.0.0.1:11434` のような信頼できるローカルエンドポイントに向けたままにしてください。別途のネットワーク認証なしに Ollama を公開しないでください。

## 出力の扱い

Web アプリはジョブの状態と返却されたローカル出力パスを記録します。ファイルは、設定された出力ルート配下のワーカーマシン上に残ります。
