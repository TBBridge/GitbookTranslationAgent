# Vercel と Neon へのデプロイ

Web コントロールプレーンは `web/` にあり、Vercel と Neon Postgres を前提に設計されています。

## Root Directory（最重要）

このリポジトリのルートは Python プロジェクトで、`package.json` はルートではなく `web/` にあります。そのため Vercel の **Root Directory を `web` に設定**しないと、次のエラーになります。

```text
Error: No Next.js version detected. Make sure your package.json has "next" in
either "dependencies" or "devDependencies". Also check your Root Directory
setting matches the directory of your package.json file.
```

設定方法（Vercel ダッシュボード）:

1. プロジェクトの **Settings → Build and Deployment**（インポート時は設定画面）を開く。
2. **Root Directory** に `web` を指定して保存する。
3. Framework Preset は `web` を基準に Next.js が自動検出される。
4. 再デプロイ（Redeploy）する。

Root Directory が `web` のとき、`web/vercel.json`・環境変数・`web/package.json` の設定がそのまま適用されます。なお Root Directory は `vercel.json` では指定できず、プロジェクト設定（またはインポート時）でのみ設定できます。

## 必須の環境変数

- `DATABASE_URL`: Neon Postgres の接続文字列。
- `ADMIN_PASSWORD_HASH`: 管理者パスワードの Argon2id ハッシュ。
- `WORKER_TOKEN`: ローカルワーカーが提示する共有 Bearer トークン。

任意:

- `WORKER_TOKENS`: 複数ワーカー用の追加トークン。カンマ区切りのリスト、または JSON 配列/マップ。`WORKER_TOKEN` に加えて適用されます。

管理者パスワードのハッシュを生成する:

```bash
cd web
node -e "const {hash}=require('@node-rs/argon2'); hash(process.argv[1]).then(console.log)" 'your-password'
```

## マイグレーション

Vercel のデプロイでは自動実行されません。Neon に対して一度手動で実行してください。

```bash
cd web
DATABASE_URL=postgresql://... npm exec tsx scripts/migrate.ts
```

Neon に対してテストを実行する場合:

```bash
TEST_DATABASE_URL=postgresql://... npm test -- --run tests/db/migrations.test.ts
```

## Vercel

Vercel ダッシュボード、または `vercel env add` で環境変数を設定します。その後:

```bash
cd web
npm run build
vercel build
```

翻訳処理そのものは Vercel Functions では実行されません。LLM を用いた処理はローカルワーカーが担い、`/api/worker/v1/*` を呼び出します。
