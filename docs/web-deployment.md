# Vercel and Neon deployment

The web control plane is in `web/` and is designed for Vercel plus Neon Postgres.

## Required environment variables

- `DATABASE_URL`: Neon Postgres connection string.
- `ADMIN_PASSWORD_HASH`: Argon2id hash for the administrator password.
- `WORKER_TOKEN`: shared bearer token for local workers.

Generate an admin hash:

```bash
cd web
node -e "const {hash}=require('@node-rs/argon2'); hash(process.argv[1]).then(console.log)" 'your-password'
```

## Migrations

```bash
cd web
DATABASE_URL=postgresql://... npm exec tsx scripts/migrate.ts
```

For tests against Neon:

```bash
TEST_DATABASE_URL=postgresql://... npm test -- --run tests/db/migrations.test.ts
```

## Vercel

Set the variables in the Vercel dashboard or with `vercel env add`. Then run:

```bash
cd web
npm run build
vercel build
```

Translation itself does not run in Vercel Functions. Local workers do the LLM work and call `/api/worker/v1/*`.
