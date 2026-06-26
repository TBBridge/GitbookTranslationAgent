"""Deterministic translation pipeline orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gitbook_translator.dictionaries import LoadedDictionary, load_dictionary
from gitbook_translator.events import stage_event
from gitbook_translator.github_client import FetchError, SourceFile
from gitbook_translator.markdown import parse_markdown, reconstruct
from gitbook_translator.models import (
    FileLanguageResult,
    PipelineResult,
    ProgressEvent,
    RunStatus,
    TranslationIssue,
    TranslationJob,
)
from gitbook_translator.paths import resolve_output_path
from gitbook_translator.providers.base import SegmentInput, TranslationRequest
from gitbook_translator.providers.factory import create_provider
from gitbook_translator.storage import atomic_write_text
from gitbook_translator.verification import VerificationIssue, verify_translation


Emit = Callable[[ProgressEvent], None]
CancelProbe = Callable[[], bool]
Verifier = Callable[[str, str, dict[str, str], str], list[VerificationIssue]]


@dataclass(frozen=True)
class _TranslationCandidate:
    source_file: SourceFile
    language: str
    dictionary: LoadedDictionary
    content: str


class _AtomicStorage:
    def save(self, path: Path, content: str) -> None:
        atomic_write_text(path, content)


class TranslationPipeline:
    """Run deterministic translation in ordinary Python control flow."""

    def __init__(
        self,
        source,
        provider_factory: Callable[[Any], Any] = create_provider,
        dictionary_loader: Callable[[Path, str], LoadedDictionary] = load_dictionary,
        verifier: Verifier = verify_translation,
        storage: Any | None = None,
    ) -> None:
        self.source = source
        self.provider_factory = provider_factory
        self.dictionary_loader = dictionary_loader
        self.verifier = verifier
        self.storage = storage or _AtomicStorage()

    def run(
        self,
        job: TranslationJob,
        emit: Emit | None = None,
        should_cancel: CancelProbe | None = None,
    ) -> PipelineResult:
        emit = emit or (lambda event: None)
        should_cancel = should_cancel or (lambda: False)
        results: list[FileLanguageResult] = []
        issues: list[TranslationIssue] = []

        self._stage("validate", emit)
        if should_cancel():
            self._stage("complete", emit)
            return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)

        self._stage("fetch", emit)
        fetch_result = self.source.fetch(job.target_paths, job.branch)
        issues.extend(_fetch_errors_to_issues(fetch_result.errors))
        if not fetch_result.files:
            self._stage("complete", emit)
            return PipelineResult(status=RunStatus.FAILED, results=[], issues=issues)
        if should_cancel():
            self._stage("complete", emit)
            return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)

        self._stage("dictionary", emit)
        dictionaries: dict[str, LoadedDictionary] = {}
        for language in job.languages:
            if should_cancel():
                self._stage("complete", emit)
                return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)
            try:
                dictionaries[language] = self.dictionary_loader(job.dictionary_path, language)
            except Exception as exc:
                issue = _issue(
                    code="dictionary_failed",
                    message=str(exc),
                    stage="dictionary",
                    language=language,
                )
                issues.append(issue)
                for source_file in fetch_result.files:
                    results.append(
                        FileLanguageResult(
                            source_path=source_file.path,
                            language=language,
                            status=RunStatus.FAILED,
                            issues=[issue],
                        )
                    )

        self._stage("translate", emit)
        provider = self.provider_factory(job.translation_provider)
        candidates: list[_TranslationCandidate] = []
        for source_file in fetch_result.files:
            for language in job.languages:
                if should_cancel():
                    self._stage("complete", emit)
                    return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)
                if language not in dictionaries:
                    continue
                try:
                    translated = self._translate_file(provider, source_file, language, dictionaries[language])
                    candidates.append(
                        _TranslationCandidate(
                            source_file=source_file,
                            language=language,
                            dictionary=dictionaries[language],
                            content=translated,
                        )
                    )
                except Exception as exc:
                    issue = _issue(
                        code="translation_failed",
                        message=str(exc),
                        stage="translate",
                        file_path=source_file.path,
                        language=language,
                        retriable=True,
                    )
                    results.append(
                        FileLanguageResult(
                            source_path=source_file.path,
                            language=language,
                            status=RunStatus.FAILED,
                            issues=[issue],
                        )
                    )

        self._stage("verify", emit)
        verified: list[_TranslationCandidate] = []
        for candidate in candidates:
            if should_cancel():
                self._stage("complete", emit)
                return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)
            verification_issues = self.verifier(
                candidate.source_file.content,
                candidate.content,
                candidate.dictionary.terms,
                candidate.language,
            )
            if verification_issues:
                result_issues = [
                    _verification_issue_to_translation_issue(
                        issue,
                        candidate.source_file.path,
                        candidate.language,
                    )
                    for issue in verification_issues
                ]
                results.append(
                    FileLanguageResult(
                        source_path=candidate.source_file.path,
                        language=candidate.language,
                        status=RunStatus.FAILED,
                        issues=result_issues,
                    )
                )
            else:
                verified.append(candidate)

        self._stage("save", emit)
        for candidate in verified:
            if should_cancel():
                self._stage("complete", emit)
                return PipelineResult(status=RunStatus.CANCELLED, results=results, issues=issues)
            output_path = resolve_output_path(
                job.output_root,
                candidate.source_file.path,
                candidate.language,
                "directory",
            )
            try:
                self.storage.save(output_path, candidate.content)
                results.append(
                    FileLanguageResult(
                        source_path=candidate.source_file.path,
                        language=candidate.language,
                        status=RunStatus.SUCCEEDED,
                        output_path=str(output_path),
                    )
                )
            except Exception as exc:
                issue = _issue(
                    code="save_failed",
                    message=str(exc),
                    stage="save",
                    file_path=candidate.source_file.path,
                    language=candidate.language,
                )
                results.append(
                    FileLanguageResult(
                        source_path=candidate.source_file.path,
                        language=candidate.language,
                        status=RunStatus.FAILED,
                        issues=[issue],
                    )
                )

        self._stage("complete", emit)
        return PipelineResult(status=_aggregate_status(results, issues), results=results, issues=issues)

    def _stage(self, stage: str, emit: Emit) -> None:
        emit(stage_event(stage))

    def _translate_file(
        self,
        provider,
        source_file: SourceFile,
        language: str,
        dictionary: LoadedDictionary,
    ) -> str:
        document = parse_markdown(source_file.content)
        if not document.translatable_segments:
            return source_file.content

        response = provider.translate(
            TranslationRequest(
                language=language,
                segments=[
                    SegmentInput(id=segment.id, text=segment.text)
                    for segment in document.translatable_segments
                ],
                dictionary=dictionary.terms,
            )
        )
        translations = {
            segment.id: segment.translation
            for segment in response.segments
        }
        return reconstruct(document, translations)


def _aggregate_status(
    results: list[FileLanguageResult],
    global_issues: list[TranslationIssue],
) -> RunStatus:
    if not results:
        return RunStatus.FAILED
    successes = sum(result.status == RunStatus.SUCCEEDED for result in results)
    failures = sum(result.status == RunStatus.FAILED for result in results)
    if successes and (failures or global_issues):
        return RunStatus.PARTIAL
    if failures and not successes:
        return RunStatus.FAILED
    return RunStatus.SUCCEEDED


def _fetch_errors_to_issues(errors: list[FetchError]) -> list[TranslationIssue]:
    return [
        _issue(
            code=error.code,
            message=error.message,
            stage="fetch",
            file_path=error.path or None,
        )
        for error in errors
    ]


def _verification_issue_to_translation_issue(
    issue: VerificationIssue,
    file_path: str,
    language: str,
) -> TranslationIssue:
    return _issue(
        code=issue.code,
        message=issue.message,
        stage="verify",
        file_path=file_path,
        language=language,
    )


def _issue(
    code: str,
    message: str,
    stage: str,
    file_path: str | None = None,
    language: str | None = None,
    retriable: bool = False,
) -> TranslationIssue:
    return TranslationIssue(
        code=code,
        message=message,
        stage=stage,
        file_path=file_path,
        language=language,
        retriable=retriable,
    )


__all__ = ["TranslationPipeline"]
