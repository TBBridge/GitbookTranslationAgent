# GitBook 翻訳プラットフォーム

GitBook/Markdown を決定的に翻訳するツール群です。2 つのエントリポイントを提供します。

- `gitbook-translator translate` — CLI から直接実行する。
- `gitbook-translator worker` — Vercel 上の Web コントロールプレーンで作成されたジョブをローカルで実行する。

本ツールは、`dictionary_*.json` の言語別辞書を用いながら、Markdown の構造・保護領域・リンク・コードブロック・GitBook 構文をそのまま保持して翻訳します。

> **補足:** 本プロジェクトは、当初の LangChain ReAct エージェントを決定的（deterministic）なパイプラインに置き換えました。ワークフローの進行を LLM に判断させることはなくなり、LLM は固定された監査可能な制御フローの中で「翻訳・レビュー・修正」のステップでのみ呼び出されます。

## アーキテクチャ

本プラットフォームは 3 つの部品で構成され、それらは単一の **バージョン付きジョブスキーマ** のみを介して連携します。Web アプリ自体は翻訳処理を一切実行しません。

```text
                 ジョブの作成 / 監視
   管理者         ───────────────────────▶  ┌────────────────────────────┐
   (ブラウザ)                                │  Web コントロールプレーン  │
                                            │  (web/) Next.js on Vercel  │
                                            │  + Neon Postgres           │
                                            │  ジョブのキュー/リース管理 │
                                            └─────────────┬──────────────┘
                                       リース/ハートビート/ │ 進捗 (HTTP, Bearerトークン)
                                       完了通知             ▼
                                            ┌────────────────────────────┐
   ローカル/オンプレ ─────────────────────▶│  ローカルワーカー          │
   (Ollama, ファイル出力, GitHubトークン)   │  src/gitbook_translator/   │
                                            │      worker/               │
                                            └─────────────┬──────────────┘
                                                          │ 呼び出し
                                                          ▼
                                            ┌────────────────────────────┐
                                            │  決定的パイプライン        │
                                            │  src/gitbook_translator/   │
                                            │  validate→fetch→dictionary │
                                            │  →translate→verify→save    │
                                            └────────────────────────────┘
```

- **Python コア** (`src/gitbook_translator/`): 決定的パイプライン、Markdown セグメント保持、機械的検証、フィンガープリントキャッシュ、遅延ロード型の OpenAI/Gemini/Ollama プロバイダアダプタ。`translate` CLI で単体実行でき、Web アプリは不要です。
- **ローカルワーカー** (`src/gitbook_translator/worker/`): コントロールプレーンからジョブをリースし、パイプラインをローカルで実行します。長時間処理やローカル資源（Ollama、出力ファイル）をサーバーレス環境から切り離して保持します。
- **Web コントロールプレーン** (`web/`): Vercel 上で動く Next.js App Router アプリ。バックエンドは Neon Postgres。管理者とワーカーを認証し、ジョブをキューイングして安全にワーカーへリースします。翻訳処理自体は行いません。

## 必要要件

- Python 3.11 以上
- `web/` コントロールプレーン用に Node.js 20.9 以上
- プライベートリポジトリ用の GitHub トークン
- いずれか 1 つの翻訳プロバイダ:
  - ローカル LLM 実行用の Ollama
  - OpenAI
  - Google Gemini

## インストール

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

Web アプリ:

```bash
cd web
npm install
```

## 辞書の配置

ターゲット言語ごとに 1 つの JSON ファイルを置いたディレクトリを使用します。

```text
dictionaries/default/
  dictionary_en.json
  dictionary_zh-cn.json
  dictionary_zh-tw.json
```

各ファイルはフラットなオブジェクトです。

```json
{
  "帳票定義": "Template Form",
  "ワークフロー": "Workflow"
}
```

## CLI の実行例

ローカル Ollama:

```bash
gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --branch main \
  --target-paths "docs/**/*.md" README.md \
  --languages en zh-CN \
  --dictionary-path ./dictionaries/default \
  --output-root ./output \
  --provider ollama \
  --model qwen3 \
  --provider-base-url http://127.0.0.1:11434
```

OpenAI:

```bash
OPENAI_API_KEY=... gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --target-paths "docs/**/*.md" \
  --languages en \
  --dictionary-path ./dictionaries/default \
  --provider openai \
  --model gpt-4.1-mini
```

Gemini:

```bash
GOOGLE_API_KEY=... gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --target-paths "docs/**/*.md" \
  --languages zh-CN \
  --dictionary-path ./dictionaries/default \
  --provider gemini \
  --model gemini-2.5-flash
```

終了コード:

- `0`: 成功
- `1`: 失敗
- `2`: 部分成功 または キャンセル
- `130`: 中断（Ctrl+C 等）

## ローカルワーカー

ワーカーは長時間の翻訳処理を手元のマシンに留め、Vercel にはコントロールプレーンのみをホストさせます。

```bash
WORKER_TOKEN=... gitbook-translator worker --config worker.example.toml
```

診断用に 1 回だけポーリングする場合は `--once`:

```bash
gitbook-translator worker --config worker.example.toml --once
```

詳細は [docs/worker-setup.md](docs/worker-setup.md) を参照してください。

## Web コントロールプレーン

`web/` は Vercel 向けの Next.js App Router アプリです。ジョブ・ワーカー・セッション・リース・ログを Neon Postgres に保存します。

```bash
cd web
npm run typecheck
npm run test:run
npm run build
npm run test:e2e
```

詳細は [docs/web-deployment.md](docs/web-deployment.md) を参照してください。

## 検証（テスト）

```bash
.venv/bin/python -m pytest tests/unit tests/property tests/integration tests/contract -q
cd web && npm run lint && npm run typecheck && npm run test:run && npm run build
```

Web の DB マイグレーションテストと Playwright E2E スイートは、`TEST_DATABASE_URL` 経由で実際の Postgres インスタンスを必要とします。Python のクロスシステム E2E（`tests/e2e/`）は、インメモリストア（`E2E_IN_MEMORY=1`）を使って実際の Web API に対して実行され、`web/` の依存関係のインストールが必要です。

## リポジトリ構成

```text
src/gitbook_translator/   Python コアパイプライン・プロバイダ・ローカルワーカー
dictionaries/default/     言語別辞書 (dictionary_<lang>.json)
web/                      Next.js + Neon コントロールプレーン (Vercel)
contracts/                ワーカー API 契約の共有フィクスチャ
tests/                    unit / property / integration / contract / e2e スイート
docs/                     セットアップ・デプロイ・設計のドキュメント
```

## ドキュメント

- [docs/worker-setup.md](docs/worker-setup.md) — ローカルワーカーの設定と実行。
- [docs/web-deployment.md](docs/web-deployment.md) — Vercel + Neon へのコントロールプレーンのデプロイ。
- [docs/migration-from-glossary.md](docs/migration-from-glossary.md) — 旧来の用語集（glossary）から辞書への移行。
