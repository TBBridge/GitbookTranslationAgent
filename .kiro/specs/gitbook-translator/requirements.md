# Requirements Document / 要件定義書

## Introduction / はじめに

GitBook Translator は、GitHubリポジトリから取得したGitBook形式のMarkdownマニュアルを、GitBook固有の記法・構造・レイアウトを完全に保持したまま、日本語部分のみを指定言語へ翻訳するシステムです。翻訳後は別のAIがレビューを行い、翻訳品質と完全性を検証します。差分検出により前回処理からの変更ファイルのみを処理対象とし、LLMトークン消費を最適化します。

GitBook Translator is a system that fetches GitBook-formatted Markdown manuals from GitHub repositories and translates only the Japanese portions into specified target languages while completely preserving GitBook-specific syntax, structure, and layout. After translation, a separate AI reviews the results to verify translation quality and completeness. Diff detection ensures only changed files are processed, optimizing LLM token consumption.

## Glossary / 用語集

- **GitBook Translator**: 本システムの名称 / The name of this system
- **Writer AI**: 翻訳を実行するAIコンポーネント / The AI component that performs translation
- **Reviewer AI**: 翻訳結果をレビューするAIコンポーネント / The AI component that reviews translation results
- **Source Repository**: 翻訳対象のMarkdownファイルが格納されているGitHubリポジトリ / The GitHub repository containing Markdown files to be translated
- **Target Language**: 翻訳先の言語（en, zh-CN, zh-TW等） / The destination language for translation (e.g., en, zh-CN, zh-TW)
- **Glossary File**: 専門用語辞書を格納したJSONファイル / A JSON file containing technical term dictionary
- **Diff Detection**: 前回処理時との差分を検出する機能 / The functionality to detect changes since the last processing
- **Format Preservation**: GitBook記法・構造・改行・レイアウトを保持すること / Preserving GitBook syntax, structure, line breaks, and layout
- **Protected Region**: コードブロック、テンプレート、タグ、URL等の翻訳禁止領域 / Regions that must not be translated, such as code blocks, templates, tags, and URLs
- **Translation Region**: 日本語テキストが含まれる翻訳対象領域 / Regions containing Japanese text that should be translated

## Requirements / 要件

### Requirement 1 / 要件1

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to fetch Markdown files from a GitHub repository, so that I can process the latest documentation content for translation.

ドキュメント管理者として、GitHubリポジトリからMarkdownファイルを取得したい。そうすることで、最新のドキュメントコンテンツを翻訳処理できるようにするため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN a user provides a repository URL and branch name THEN the GitBook Translator SHALL fetch all files matching the specified target paths from the Source Repository
2. WHEN fetching files from GitHub THEN the GitBook Translator SHALL store file metadata including commit hash and last modified timestamp for each file
3. WHEN a user specifies target paths with glob patterns THEN the GitBook Translator SHALL resolve all matching file paths recursively
4. IF the GitHub API returns an error THEN the GitBook Translator SHALL report the error with specific details and halt processing
5. WHEN authentication is required for private repositories THEN the GitBook Translator SHALL support GitHub token-based authentication

### Requirement 2 / 要件2

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to detect changes since the last processing, so that I can minimize LLM token consumption by only processing modified files.

ドキュメント管理者として、前回処理からの変更を検出したい。そうすることで、変更されたファイルのみを処理してLLMトークン消費を最小化するため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the GitBook Translator processes files for the first time THEN the GitBook Translator SHALL store file metadata in a local cache
2. WHEN the GitBook Translator processes files on subsequent runs THEN the GitBook Translator SHALL compare current file commit hashes with cached metadata
3. WHEN a file has not changed since the last processing THEN the GitBook Translator SHALL skip that file from the translation queue
4. WHEN a file has changed since the last processing THEN the GitBook Translator SHALL add that file to the translation queue
5. WHEN comparing translated output with source THEN the GitBook Translator SHALL detect if the source has changed and mark translations as outdated

### Requirement 3 / 要件3

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to preserve all GitBook-specific syntax and structure during translation, so that the translated documents remain fully compatible with GitBook.

ドキュメント管理者として、翻訳中にすべてのGitBook固有の構文と構造を保持したい。そうすることで、翻訳されたドキュメントがGitBookと完全に互換性を保つため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN translating a Markdown file THEN the GitBook Translator SHALL preserve all line breaks, blank lines, indentation, and spacing exactly as in the original
2. WHEN encountering YAML frontmatter THEN the GitBook Translator SHALL preserve the structure and keys without translating values by default
3. WHEN encountering GitBook-specific blocks THEN the GitBook Translator SHALL preserve {% hint %}, {% tabs %}, {% tab %}, {% endtab %}, {% endtabs %}, {% include %}, {% embed %}, {% file %} tags unchanged
4. WHEN encountering template expressions THEN the GitBook Translator SHALL preserve {{ ... }} and {% ... %} expressions unchanged
5. WHEN encountering HTML tags THEN the GitBook Translator SHALL preserve all HTML tags and attributes unchanged

### Requirement 4 / 要件4

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to protect code blocks and inline code from translation, so that technical content remains accurate and executable.

ドキュメント管理者として、コードブロックとインラインコードを翻訳から保護したい。そうすることで、技術的なコンテンツが正確で実行可能な状態を保つため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN encountering fenced code blocks THEN the GitBook Translator SHALL exclude all content within ``` ``` markers from translation
2. WHEN encountering inline code THEN the GitBook Translator SHALL exclude all content within `backticks` from translation
3. WHEN parsing a file THEN the GitBook Translator SHALL identify and mark all Protected Regions before translation begins
4. WHEN translating text THEN the GitBook Translator SHALL only process content outside of Protected Regions
5. WHEN reconstructing the translated file THEN the GitBook Translator SHALL restore all Protected Regions to their exact original form

### Requirement 5 / 要件5

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to preserve all links and image paths during translation, so that navigation and media references remain functional.

ドキュメント管理者として、翻訳中にすべてのリンクと画像パスを保持したい。そうすることで、ナビゲーションとメディア参照が機能し続けるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN encountering Markdown links THEN the GitBook Translator SHALL preserve the URL portion of [text](URL) while allowing translation of the display text
2. WHEN encountering image references THEN the GitBook Translator SHALL preserve the path portion of ![alt](path) while allowing translation of the alt text
3. WHEN encountering relative paths THEN the GitBook Translator SHALL preserve all relative path references unchanged
4. WHEN encountering anchor links THEN the GitBook Translator SHALL preserve all anchor references starting with # unchanged
5. WHEN encountering file references THEN the GitBook Translator SHALL preserve all filename references unchanged

### Requirement 6 / 要件6

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to preserve table structure during translation, so that tabular data remains properly formatted.

ドキュメント管理者として、翻訳中にテーブル構造を保持したい。そうすることで、表形式データが適切にフォーマットされた状態を保つため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN encountering Markdown tables THEN the GitBook Translator SHALL preserve all pipe characters and alignment markers
2. WHEN translating table cells THEN the GitBook Translator SHALL only translate the content within cells while maintaining column structure
3. WHEN encountering table headers THEN the GitBook Translator SHALL preserve the separator row with :--: alignment markers unchanged
4. WHEN reconstructing tables THEN the GitBook Translator SHALL ensure the number of columns remains consistent across all rows

### Requirement 7 / 要件7

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to translate only Japanese text while preserving non-Japanese content, so that multilingual documents are handled correctly.

ドキュメント管理者として、日本語テキストのみを翻訳し、非日本語コンテンツを保持したい。そうすることで、多言語ドキュメントが正しく処理されるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN analyzing text content THEN the GitBook Translator SHALL identify Japanese characters using Unicode ranges
2. WHEN translating content THEN the GitBook Translator SHALL only translate segments containing Japanese text
3. WHEN encountering non-Japanese text THEN the GitBook Translator SHALL preserve that text unchanged
4. WHEN encountering mixed Japanese and non-Japanese text THEN the GitBook Translator SHALL translate only the Japanese portions while preserving the rest
5. WHEN encountering punctuation and symbols THEN the GitBook Translator SHALL preserve their usage and positioning

### Requirement 8 / 要件8

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to apply a glossary of technical terms, so that terminology remains consistent across all translations.

ドキュメント管理者として、技術用語の辞書を適用したい。そうすることで、すべての翻訳で用語が一貫性を保つため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN a user provides a Glossary File path THEN the GitBook Translator SHALL load and parse the glossary before translation begins
2. WHEN the glossary format is unknown THEN the GitBook Translator SHALL analyze the file structure to identify language mappings
3. WHEN translating text containing glossary terms THEN the Writer AI SHALL use the specified translations from the glossary
4. WHEN a term appears in the glossary THEN the GitBook Translator SHALL enforce exact terminology without variation
5. WHEN encountering product names, feature names, UI labels, commands, or technical identifiers THEN the GitBook Translator SHALL not translate them unless specified in the glossary

### Requirement 9 / 要件9

**User Story / ユーザーストーリー:** As a documentation maintainer, I want the Writer AI to produce natural, formal, business-appropriate translations, so that the translated documentation maintains professional quality.

ドキュメント管理者として、Writer AIが自然でフォーマルなビジネスに適した翻訳を生成することを望む。そうすることで、翻訳されたドキュメントがプロフェッショナルな品質を維持するため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the Writer AI translates text THEN the Writer AI SHALL produce translations in a formal and polite tone appropriate for business documentation
2. WHEN the Writer AI translates text THEN the Writer AI SHALL ensure semantic accuracy and faithfulness to the original meaning
3. WHEN the Writer AI translates procedural content THEN the Writer AI SHALL maintain clarity in steps, warnings, and notices
4. WHEN the Writer AI translates text THEN the Writer AI SHALL prioritize Format Preservation rules above all other considerations
5. WHEN the Writer AI completes translation THEN the Writer AI SHALL output valid Markdown that preserves the original structure

### Requirement 10 / 要件10

**User Story / ユーザーストーリー:** As a documentation maintainer, I want the Reviewer AI to verify translation quality and completeness, so that errors are caught before final output.

ドキュメント管理者として、Reviewer AIが翻訳品質と完全性を検証することを望む。そうすることで、最終出力前にエラーが検出されるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the Reviewer AI receives a translation THEN the Reviewer AI SHALL verify that all GitBook syntax, tags, line breaks, indentation, tables, and code blocks are preserved
2. WHEN the Reviewer AI reviews a translation THEN the Reviewer AI SHALL check for untranslated Japanese text and missing lines
3. WHEN the Reviewer AI reviews a translation THEN the Reviewer AI SHALL verify that glossary terms are used consistently without variation
4. WHEN the Reviewer AI reviews a translation THEN the Reviewer AI SHALL verify that all URLs, relative paths, and anchor links remain unchanged
5. WHEN the Reviewer AI reviews a translation THEN the Reviewer AI SHALL verify that the translation uses formal and natural language appropriate for the Target Language

### Requirement 11 / 要件11

**User Story / ユーザーストーリー:** As a documentation maintainer, I want the Reviewer AI to classify issues by severity, so that critical problems are addressed before minor improvements.

ドキュメント管理者として、Reviewer AIが問題を重要度で分類することを望む。そうすることで、軽微な改善の前に重大な問題が対処されるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the Reviewer AI identifies an issue THEN the Reviewer AI SHALL classify it as BLOCKER, MAJOR, or MINOR
2. WHEN the Reviewer AI identifies a BLOCKER issue THEN the Reviewer AI SHALL flag structural damage, link corruption, missing content, or code modification
3. WHEN the Reviewer AI identifies a MAJOR issue THEN the Reviewer AI SHALL flag semantic errors or glossary violations
4. WHEN the Reviewer AI identifies a MINOR issue THEN the Reviewer AI SHALL flag stylistic improvements
5. WHEN the Reviewer AI finds BLOCKER or MAJOR issues THEN the Reviewer AI SHALL provide specific correction suggestions and request re-translation

### Requirement 12 / 要件12

**User Story / ユーザーストーリー:** As a documentation maintainer, I want an iterative review process, so that translations are refined until they meet quality standards.

ドキュメント管理者として、反復的なレビュープロセスを望む。そうすることで、翻訳が品質基準を満たすまで改善されるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the Reviewer AI identifies BLOCKER or MAJOR issues THEN the GitBook Translator SHALL send the translation back to the Writer AI for correction
2. WHEN the Writer AI receives correction requests THEN the Writer AI SHALL modify only the flagged sections
3. WHEN the Writer AI completes corrections THEN the GitBook Translator SHALL submit the revised translation to the Reviewer AI again
4. WHEN the review-correction cycle completes twice THEN the GitBook Translator SHALL proceed with the current version regardless of remaining issues
5. WHEN the Reviewer AI finds no BLOCKER or MAJOR issues THEN the GitBook Translator SHALL accept the translation as final

### Requirement 13 / 要件13

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to save translated files locally with configurable naming conventions, so that I can organize translations according to my project structure.

ドキュメント管理者として、設定可能な命名規則でローカルに翻訳ファイルを保存したい。そうすることで、プロジェクト構造に応じて翻訳を整理できるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN a user specifies suffix naming mode THEN the GitBook Translator SHALL save files as <name>.<lang>.md
2. WHEN a user specifies directory naming mode THEN the GitBook Translator SHALL save files in language-specific subdirectories like /en/, /zh-CN/, /zh-TW/
3. WHEN saving translated files THEN the GitBook Translator SHALL create all necessary parent directories automatically
4. WHEN saving translated files THEN the GitBook Translator SHALL preserve the relative directory structure from the source
5. WHEN all translations are complete THEN the GitBook Translator SHALL save all files to the specified output_root directory

### Requirement 14 / 要件14

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to optionally push translations to GitHub, so that I can integrate translated documentation into version control.

ドキュメント管理者として、オプションで翻訳をGitHubにプッシュしたい。そうすることで、翻訳されたドキュメントをバージョン管理に統合できるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN push_option is set to none THEN the GitBook Translator SHALL only save files locally without any GitHub operations
2. WHEN push_option is set to push_same_repo_direct THEN the GitBook Translator SHALL request explicit user confirmation before pushing
3. WHEN push_option is set to push_same_repo_new_branch THEN the GitBook Translator SHALL create a new branch with a name like translation/<lang>/<timestamp>
4. WHEN pushing to a new branch THEN the GitBook Translator SHALL push all translated files and provide information for creating a pull request
5. WHEN GitHub push operations fail THEN the GitBook Translator SHALL report the error and ensure local files are still saved

### Requirement 15 / 要件15

**User Story / ユーザーストーリー:** As a documentation maintainer, I want to process multiple target languages in a single run, so that I can efficiently create multilingual documentation.

ドキュメント管理者として、1回の実行で複数のターゲット言語を処理したい。そうすることで、効率的に多言語ドキュメントを作成できるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN a user specifies multiple Target Languages THEN the GitBook Translator SHALL process each language sequentially
2. WHEN translating to multiple languages THEN the GitBook Translator SHALL apply language-specific glossary mappings for each Target Language
3. WHEN saving files for multiple languages THEN the GitBook Translator SHALL organize output according to the specified naming convention
4. WHEN an error occurs for one Target Language THEN the GitBook Translator SHALL continue processing remaining languages
5. WHEN all languages are processed THEN the GitBook Translator SHALL provide a summary report of successes and failures

### Requirement 16 / 要件16

**User Story / ユーザーストーリー:** As a documentation maintainer, I want clear error messages and logging, so that I can troubleshoot issues and monitor processing progress.

ドキュメント管理者として、明確なエラーメッセージとログを望む。そうすることで、問題をトラブルシュートし、処理の進捗を監視できるため。

#### Acceptance Criteria / 受け入れ基準

1. WHEN the GitBook Translator encounters an error THEN the GitBook Translator SHALL log the error with context including file path, language, and operation
2. WHEN processing files THEN the GitBook Translator SHALL log progress including current file, language, and stage
3. WHEN the Reviewer AI identifies issues THEN the GitBook Translator SHALL log all issues with severity, location, and description
4. WHEN processing completes THEN the GitBook Translator SHALL output a summary including files processed, translations created, and errors encountered
5. WHEN validation fails THEN the GitBook Translator SHALL provide actionable guidance for resolving the issue
