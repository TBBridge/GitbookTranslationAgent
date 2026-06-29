# Vercel と Neon へのデプロイ

Web コントロールプレーンは `web/` にあり、Vercel と Neon Postgres を前提に設計されています。

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
