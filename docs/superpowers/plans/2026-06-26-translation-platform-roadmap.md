# Translation Platform Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement these plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved deterministic translation platform in four independently verifiable phases.

**Architecture:** Complete the Python core and CLI first because every later phase depends on their public API. Implement the local worker second against a fake server contract, the Next.js/Neon control plane third against that contract, and the final phase joins both sides and verifies packaging and Vercel deployment.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, PyGithub, OpenAI, Google Gemini, Ollama HTTP API, pytest, Next.js App Router, TypeScript, Neon Postgres, Zod, Vitest, Playwright, Vercel.

---

## Execution Order

1. [Python Translation Core and CLI](./2026-06-26-python-core-cli-implementation.md)
2. [Local Worker](./2026-06-26-local-worker-implementation.md)
3. [Next.js Web and Neon Control Plane](./2026-06-26-web-neon-implementation.md)
4. [Cross-System Integration and Release](./2026-06-26-integration-release-implementation.md)

Each phase must finish with its own test suite green before the next phase begins. The web application must not duplicate Python pipeline behavior; the versioned job schema is the shared boundary.

## Target Repository Structure

```text
GitbookTranslationAgent/
├── src/gitbook_translator/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── pipeline.py
│   ├── dictionaries.py
│   ├── markdown.py
│   ├── verification.py
│   ├── cache.py
│   ├── paths.py
│   ├── github_client.py
│   ├── providers/
│   └── worker/
├── dictionaries/default/
├── tests/
├── web/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── migrations/
│   └── tests/
├── contracts/
├── scripts/
├── docs/
├── pyproject.toml
└── README.md
```

## Global Completion Gate

- [ ] Run the complete Python unit, property, integration, contract, and E2E suites.
- [ ] Build and install the Python wheel in a fresh virtual environment outside the repository.
- [ ] Apply all SQL migrations to an empty Neon-compatible Postgres database.
- [ ] Run web lint, type-check, unit/API tests, E2E tests, and production build.
- [ ] Run the real local worker against the real Next.js API with fake external services.
- [ ] Run `vercel build` from `web/`.
- [ ] Run `git diff --check`.
- [ ] Confirm `git status --short` contains only intended changes.
