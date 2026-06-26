"""Command-line entrypoint for the deterministic translator."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from gitbook_translator.config import normalize_repository_url, validate_branch
from gitbook_translator.github_client import GitHubSource
from gitbook_translator.models import PipelineResult, ProviderSpec, TranslationJob
from gitbook_translator.pipeline import TranslationPipeline
from gitbook_translator.worker.client import WorkerControlPlaneClient
from gitbook_translator.worker.config import load_worker_config
from gitbook_translator.worker.models import WorkerConfig, WorkerProviderConfig
from gitbook_translator.worker.outbox import Outbox
from gitbook_translator.worker.runner import WorkerRunner


COMMANDS = {"translate", "worker"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitbook-translator",
        description="Deterministic GitBook documentation translator.",
        epilog="Use `gitbook-translator translate --dictionary-path ./dictionaries/default ...`.",
    )
    subparsers = parser.add_subparsers(dest="command")

    translate = subparsers.add_parser(
        "translate",
        help="Translate GitBook Markdown files.",
    )
    translate.add_argument("--repo-url", required=True)
    translate.add_argument("--branch", default="main")
    translate.add_argument("--target-paths", nargs="+", required=True)
    translate.add_argument("--languages", nargs="+", required=True)
    translate.add_argument(
        "--dictionary-path",
        required=True,
        help="Directory containing target-language dictionaries.",
    )
    translate.add_argument("--output-root", default="./output")
    translate.add_argument(
        "--provider",
        choices=["ollama", "openai", "gemini"],
        default="ollama",
        help="Translation provider.",
    )
    translate.add_argument("--model", help="Translation model name.")
    translate.add_argument("--provider-base-url")
    translate.add_argument(
        "--review-provider",
        choices=["none", "ollama", "openai", "gemini"],
        default="none",
    )
    translate.add_argument("--review-model")
    translate.add_argument("--review-base-url")
    translate.add_argument(
        "--push-option",
        choices=["none", "push_same_repo_direct", "push_same_repo_new_branch"],
        default="none",
        help="Reserved publish strategy for pipeline integrations.",
    )
    translate.add_argument(
        "--confirm-direct-push",
        action="store_true",
        help="Explicitly confirm direct push when that publish strategy is selected.",
    )

    worker = subparsers.add_parser(
        "worker",
        help="Run local worker mode.",
    )
    worker.add_argument("--config", required=True, help="Worker configuration file.")
    worker.add_argument(
        "--once",
        action="store_true",
        help="Run one polling cycle, then exit.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    args_list = list(sys.argv[1:] if argv is None else argv)

    if "--glossary-path" in args_list:
        print(
            "The --glossary-path option was removed; use --dictionary-path instead.",
            file=sys.stderr,
        )
        return 1

    parser = build_parser()
    try:
        args = parser.parse_args(_default_translate_command(args_list))
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "worker":
        try:
            return run_worker(args)
        except KeyboardInterrupt:
            print("Worker stopped by user", file=sys.stderr)
            return 130
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command != "translate":
        parser.print_help()
        return 0

    try:
        job = build_translation_job(args)
        validate_selected_provider_environment(job.translation_provider)
        if job.review_provider is not None:
            validate_selected_provider_environment(job.review_provider)
        result = run_translation(job)
    except KeyboardInterrupt:
        print("Operation cancelled by user", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    render_summary(result)
    return result.status.exit_code


def build_translation_job(args: argparse.Namespace) -> TranslationJob:
    provider = ProviderSpec(
        provider=args.provider,
        model=args.model or _default_model(args.provider),
        base_url=args.provider_base_url,
    )
    review_provider = None
    if args.review_provider != "none":
        review_provider = ProviderSpec(
            provider=args.review_provider,
            model=args.review_model or _default_model(args.review_provider),
            base_url=args.review_base_url,
        )

    return TranslationJob(
        repo_url=normalize_repository_url(args.repo_url),
        branch=validate_branch(args.branch),
        target_paths=args.target_paths,
        languages=args.languages,
        dictionary_path=Path(args.dictionary_path),
        output_root=Path(args.output_root),
        translation_provider=provider,
        review_provider=review_provider,
    )


def run_translation(job: TranslationJob) -> PipelineResult:
    """Run the deterministic translation pipeline for a CLI job."""

    source = GitHubSource(_load_github_repository(job.repo_url))
    return TranslationPipeline(source=source).run(job)


def run_worker(args: argparse.Namespace) -> int:
    """Run the local worker process."""

    config = load_worker_config(args.config)
    token = os.environ.get(config.token_env)
    if not token:
        raise ValueError(f"{config.token_env} is required for worker mode")

    validate_worker_provider_environment(config)
    runner = WorkerRunner(
        client=WorkerControlPlaneClient(
            server_url=config.server_url,
            token=token,
            timeout_seconds=config.request_timeout_seconds,
        ),
        pipeline=_build_worker_pipeline,
        config=config,
        outbox=Outbox(_worker_outbox_path(config, Path(args.config))),
    )

    if args.once:
        result = runner.run_once()
        render_summary(result)
        return result.status.exit_code

    runner.run_forever()
    return 0


def validate_worker_provider_environment(config: WorkerConfig) -> None:
    for provider in config.providers:
        validate_selected_provider_environment(_provider_spec_from_worker(provider))


def _provider_spec_from_worker(provider: WorkerProviderConfig) -> ProviderSpec:
    return ProviderSpec(
        provider=provider.provider,
        model=provider.model,
        base_url=provider.base_url,
    )


def _build_worker_pipeline(job: TranslationJob) -> TranslationPipeline:
    return TranslationPipeline(source=GitHubSource(_load_github_repository(job.repo_url)))


def _worker_outbox_path(config: WorkerConfig, config_path: Path) -> Path:
    if "default" in config.cache_roots:
        root = config.cache_roots["default"]
    elif config.cache_roots:
        root = config.cache_roots[sorted(config.cache_roots)[0]]
    else:
        root = config_path.expanduser().resolve().parent / ".gitbook-translator-worker"
    return root / "outbox.jsonl"


def validate_selected_provider_environment(provider: ProviderSpec) -> None:
    provider_name = provider.provider.lower()
    if provider_name == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required when provider is openai")
    if provider_name in {"gemini", "google", "google-gemini"} and not os.environ.get(
        "GOOGLE_API_KEY"
    ):
        raise ValueError("GOOGLE_API_KEY is required when provider is gemini")


def render_summary(result: PipelineResult) -> None:
    print(
        f"Translation {result.status.value}: "
        f"{result.success_count} succeeded, {result.failure_count} failed"
    )
    for issue in result.issues:
        print(f"- [{issue.stage or 'pipeline'}] {issue.code}: {issue.message}")


def _default_translate_command(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    first = argv[0]
    if first in COMMANDS or first in {"-h", "--help"}:
        return argv
    return ["translate", *argv]


def _default_model(provider: str) -> str:
    return {
        "ollama": "qwen3",
        "openai": "gpt-4.1-mini",
        "gemini": "gemini-2.5-flash",
    }[provider]


def _load_github_repository(repo_url: str):
    from github import Github

    parsed = urlparse(repo_url)
    owner_repo = parsed.path.strip("/")
    token = os.environ.get("GITHUB_TOKEN")
    github = Github(token) if token else Github()
    return github.get_repo(owner_repo)


if __name__ == "__main__":
    raise SystemExit(main())
