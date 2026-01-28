"""Performance tests for GitBook Translator.

Tests execution time, token usage, memory consumption, and identifies bottlenecks.

Requirements: All requirements - performance
"""

import time
import psutil
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.models import CLIConfig
from src.agent import TranslationAgent


class TestPerformanceMetrics:
    """Performance testing for GitBook Translator."""

    @pytest.fixture
    def performance_config(self, temp_output_dir):
        """Configuration for performance testing."""
        return CLIConfig(
            repo_url="https://github.com/test/large-repo",
            branch="main",
            target_paths=["**/*.md"],
            languages=["en", "zh-CN"],
            glossary_path="tests/fixtures/test_glossary.json",
            output_root=temp_output_dir,
            push_option="none",
            output_naming="suffix"
        )

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def large_file_content(self):
        """Generate large file content for performance testing."""
        # Create a large Japanese document (approximately 50KB)
        base_content = """# 大規模ドキュメントのテスト

このドキュメントは、GitBook Translatorのパフォーマンステスト用に作成された大規模なファイルです。

## セクション1: 基本機能の説明

GitBook Translatorは、GitBook形式のMarkdownドキュメントを自動翻訳するツールです。
このツールは、以下の特徴を持っています：

- **フォーマット保持**: 元のレイアウトを完全に維持
- **保護領域の検出**: コードブロックやURLを自動的に除外
- **用語集対応**: 専門用語の一貫した翻訳
- **差分検出**: 変更されたファイルのみを処理

### サブセクション1.1: 技術仕様

システムは以下の技術を使用しています：

```python
# サンプルコード
def translate_document(content, target_language):
    parser = MarkdownParser()
    segments = parser.parse(content)
    
    translator = AITranslator(target_language)
    translated_segments = []
    
    for segment in segments:
        if segment.type == SegmentType.TRANSLATABLE:
            translated = translator.translate(segment.content)
            translated_segments.append(translated)
        else:
            translated_segments.append(segment.content)
    
    return reconstruct_document(translated_segments)
```

### サブセクション1.2: 使用方法

基本的な使用方法は以下の通りです：

1. **リポジトリの指定**: GitHub URLとブランチを指定
2. **対象ファイルの選択**: glob パターンで対象ファイルを指定
3. **言語の選択**: 翻訳先言語を指定
4. **用語集の設定**: 専門用語辞書を指定
5. **実行**: コマンドを実行して翻訳を開始

## セクション2: 高度な機能

### サブセクション2.1: 多言語対応

システムは以下の言語をサポートしています：

| 言語 | コード | 対応状況 |
|------|--------|----------|
| 英語 | en | ✅ 完全対応 |
| 中国語（簡体字） | zh-CN | ✅ 完全対応 |
| 中国語（繁体字） | zh-TW | ✅ 完全対応 |
| 韓国語 | ko | ✅ 完全対応 |
| フランス語 | fr | 🔄 開発中 |
| ドイツ語 | de | 🔄 開発中 |

### サブセクション2.2: パフォーマンス最適化

システムは以下の最適化を実装しています：

- **キャッシュメカニズム**: 前回の処理結果を保存
- **差分検出**: 変更されたファイルのみを処理
- **並列処理**: 複数ファイルの同時処理（将来実装予定）
- **トークン最適化**: 不要な翻訳を回避

## セクション3: トラブルシューティング

### よくある問題と解決方法

問題が発生した場合は、以下の手順で解決を試してください。
"""
        
        # Repeat content to create a larger file
        large_content = base_content
        for i in range(10):  # Repeat 10 times to create ~500KB file
            large_content += f"\n\n## 繰り返しセクション {i+1}\n\n" + base_content
        
        return large_content

    @pytest.fixture
    def large_repository_files(self, large_file_content):
        """Simulate a large repository with multiple files."""
        files = []
        for i in range(20):  # Create 20 large files
            files.append({
                'path': f'docs/section_{i:02d}.md',
                'content': large_file_content,
                'commit_hash': f'abc123{i:02d}',
                'last_modified': '2024-01-01T00:00:00Z'
            })
        return files

    def test_large_file_processing_time(self, performance_config, large_file_content):
        """Test execution time for processing large files."""
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            # Mock fetching a single large file
            mock_fetch.return_value = [{
                'path': 'docs/large_file.md',
                'content': large_file_content,
                'commit_hash': 'abc123',
                'last_modified': '2024-01-01T00:00:00Z'
            }]
            
            with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                mock_translate.return_value = {
                    'translated_content': large_file_content.replace('日本語', 'Japanese'),
                    'segments_translated': 100
                }
                
                agent = TranslationAgent(config=performance_config)
                
                # Measure execution time
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                result = agent.run()
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                # Performance assertions
                assert execution_time < 60.0, f"Large file processing took {execution_time:.2f}s, expected < 60s"
                assert memory_used < 500, f"Memory usage {memory_used:.2f}MB, expected < 500MB"
                
                print(f"Large file processing: {execution_time:.2f}s, Memory: {memory_used:.2f}MB")

    def test_multiple_files_processing_time(self, performance_config, large_repository_files):
        """Test execution time for processing multiple large files."""
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            mock_fetch.return_value = large_repository_files
            
            with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                mock_translate.return_value = {
                    'translated_content': 'Translated content',
                    'segments_translated': 50
                }
                
                agent = TranslationAgent(config=performance_config)
                
                # Measure execution time for multiple files
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                result = agent.run()
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                # Performance assertions for multiple files
                files_per_second = len(large_repository_files) / execution_time
                assert files_per_second > 0.1, f"Processing rate {files_per_second:.3f} files/s too slow"
                assert memory_used < 1000, f"Memory usage {memory_used:.2f}MB too high for multiple files"
                
                print(f"Multiple files processing: {execution_time:.2f}s, Rate: {files_per_second:.3f} files/s")

    def test_token_usage_measurement(self, performance_config, large_file_content):
        """Test and measure LLM token usage."""
        token_count = 0
        
        def mock_translate_with_token_count(*args, **kwargs):
            nonlocal token_count
            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            content = kwargs.get('content', '')
            estimated_tokens = len(content) // 4
            token_count += estimated_tokens
            
            return {
                'translated_content': content.replace('日本語', 'Japanese'),
                'segments_translated': 10,
                'tokens_used': estimated_tokens
            }
        
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            mock_fetch.return_value = [{
                'path': 'docs/test.md',
                'content': large_file_content,
                'commit_hash': 'abc123',
                'last_modified': '2024-01-01T00:00:00Z'
            }]
            
            with patch('src.tools.translate_content.TranslateContentTool._run', side_effect=mock_translate_with_token_count):
                agent = TranslationAgent(config=performance_config)
                result = agent.run()
                
                # Token usage assertions
                content_size_kb = len(large_file_content) / 1024
                tokens_per_kb = token_count / content_size_kb
                
                assert token_count > 0, "Token count should be measured"
                assert tokens_per_kb < 1000, f"Token usage {tokens_per_kb:.0f} tokens/KB seems excessive"
                
                print(f"Token usage: {token_count} tokens, {tokens_per_kb:.0f} tokens/KB")

    def test_memory_usage_scaling(self, performance_config):
        """Test memory usage scaling with different file sizes."""
        memory_measurements = []
        
        for file_size_multiplier in [1, 2, 5, 10]:
            # Create content of different sizes
            base_content = "これは日本語のテストコンテンツです。" * 1000
            test_content = base_content * file_size_multiplier
            
            with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
                mock_fetch.return_value = [{
                    'path': f'docs/test_{file_size_multiplier}.md',
                    'content': test_content,
                    'commit_hash': 'abc123',
                    'last_modified': '2024-01-01T00:00:00Z'
                }]
                
                with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                    mock_translate.return_value = {
                        'translated_content': test_content.replace('日本語', 'Japanese'),
                        'segments_translated': 10
                    }
                    
                    # Measure memory before and after
                    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    
                    agent = TranslationAgent(config=performance_config)
                    result = agent.run()
                    
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    memory_used = end_memory - start_memory
                    
                    content_size_mb = len(test_content) / 1024 / 1024
                    memory_measurements.append({
                        'content_size_mb': content_size_mb,
                        'memory_used_mb': memory_used,
                        'memory_ratio': memory_used / content_size_mb if content_size_mb > 0 else 0
                    })
        
        # Analyze memory scaling
        for i, measurement in enumerate(memory_measurements):
            print(f"Size: {measurement['content_size_mb']:.2f}MB, "
                  f"Memory: {measurement['memory_used_mb']:.2f}MB, "
                  f"Ratio: {measurement['memory_ratio']:.2f}")
        
        # Memory should scale reasonably (not exponentially)
        if len(memory_measurements) >= 2:
            first_ratio = memory_measurements[0]['memory_ratio']
            last_ratio = memory_measurements[-1]['memory_ratio']
            scaling_factor = last_ratio / first_ratio if first_ratio > 0 else 1
            
            assert scaling_factor < 5.0, f"Memory scaling factor {scaling_factor:.2f} too high"

    def test_bottleneck_identification(self, performance_config, large_file_content):
        """Identify performance bottlenecks in the translation pipeline."""
        timing_data = {}
        
        def time_operation(operation_name, func, *args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            timing_data[operation_name] = end_time - start_time
            return result
        
        # Mock each major operation with timing
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            def timed_fetch(*args, **kwargs):
                return time_operation('github_fetch', lambda: [{
                    'path': 'docs/test.md',
                    'content': large_file_content,
                    'commit_hash': 'abc123',
                    'last_modified': '2024-01-01T00:00:00Z'
                }])
            mock_fetch.side_effect = timed_fetch
            
            with patch('src.tools.parse_markdown.ParseMarkdownTool._run') as mock_parse:
                def timed_parse(*args, **kwargs):
                    return time_operation('markdown_parse', lambda: {
                        'segments': [{'type': 'translatable', 'content': 'テスト'}],
                        'structure': {'line_breaks': [1, 2, 3]}
                    })
                mock_parse.side_effect = timed_parse
                
                with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                    def timed_translate(*args, **kwargs):
                        return time_operation('translation', lambda: {
                            'translated_content': large_file_content.replace('日本語', 'Japanese'),
                            'segments_translated': 50
                        })
                    mock_translate.side_effect = timed_translate
                    
                    with patch('src.tools.review_translation.ReviewTranslationTool._run') as mock_review:
                        def timed_review(*args, **kwargs):
                            return time_operation('review', lambda: {
                                'issues': [],
                                'approved': True
                            })
                        mock_review.side_effect = timed_review
                        
                        with patch('src.tools.save_translation.SaveTranslationTool._run') as mock_save:
                            def timed_save(*args, **kwargs):
                                return time_operation('file_save', lambda: {
                                    'saved_path': 'output/test.en.md',
                                    'success': True
                                })
                            mock_save.side_effect = timed_save
                            
                            agent = TranslationAgent(config=performance_config)
                            result = agent.run()
        
        # Analyze bottlenecks
        total_time = sum(timing_data.values())
        bottlenecks = []
        
        for operation, duration in timing_data.items():
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            print(f"{operation}: {duration:.3f}s ({percentage:.1f}%)")
            
            if percentage > 50:  # More than 50% of total time
                bottlenecks.append(operation)
        
        # Report bottlenecks
        if bottlenecks:
            print(f"Performance bottlenecks identified: {', '.join(bottlenecks)}")
        else:
            print("No major bottlenecks identified - processing time is well distributed")
        
        # Ensure no single operation dominates excessively
        max_percentage = max((duration / total_time) * 100 for duration in timing_data.values()) if total_time > 0 else 0
        assert max_percentage < 80, f"Single operation taking {max_percentage:.1f}% of time indicates bottleneck"

    def test_concurrent_language_processing_performance(self, performance_config, large_file_content):
        """Test performance when processing multiple languages concurrently."""
        # Test with multiple languages
        multi_lang_config = performance_config
        multi_lang_config.languages = ["en", "zh-CN", "zh-TW", "ko"]
        
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            mock_fetch.return_value = [{
                'path': 'docs/test.md',
                'content': large_file_content,
                'commit_hash': 'abc123',
                'last_modified': '2024-01-01T00:00:00Z'
            }]
            
            with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                mock_translate.return_value = {
                    'translated_content': large_file_content.replace('日本語', 'Japanese'),
                    'segments_translated': 50
                }
                
                agent = TranslationAgent(config=multi_lang_config)
                
                # Measure multi-language processing time
                start_time = time.time()
                result = agent.run()
                end_time = time.time()
                
                execution_time = end_time - start_time
                languages_per_second = len(multi_lang_config.languages) / execution_time
                
                print(f"Multi-language processing: {execution_time:.2f}s, "
                      f"Rate: {languages_per_second:.3f} languages/s")
                
                # Performance should scale reasonably with number of languages
                assert languages_per_second > 0.05, f"Multi-language processing too slow: {languages_per_second:.3f} lang/s"

    def test_cache_performance_impact(self, performance_config, large_file_content):
        """Test performance impact of caching mechanism."""
        cache_file = Path(performance_config.output_root) / '.gitbook-translator-cache.json'
        
        # First run (no cache)
        with patch('src.tools.fetch_github_files.FetchGitHubFilesTool._run') as mock_fetch:
            mock_fetch.return_value = [{
                'path': 'docs/test.md',
                'content': large_file_content,
                'commit_hash': 'abc123',
                'last_modified': '2024-01-01T00:00:00Z'
            }]
            
            with patch('src.tools.translate_content.TranslateContentTool._run') as mock_translate:
                mock_translate.return_value = {
                    'translated_content': large_file_content.replace('日本語', 'Japanese'),
                    'segments_translated': 50
                }
                
                agent = TranslationAgent(config=performance_config)
                
                # First run timing
                start_time = time.time()
                result1 = agent.run()
                first_run_time = time.time() - start_time
                
                # Second run timing (with cache)
                start_time = time.time()
                result2 = agent.run()
                second_run_time = time.time() - start_time
                
                print(f"First run: {first_run_time:.2f}s, Second run: {second_run_time:.2f}s")
                
                # Second run should be faster due to caching (if no changes)
                if second_run_time > 0:
                    speedup = first_run_time / second_run_time
                    print(f"Cache speedup: {speedup:.2f}x")
                    
                    # Cache should provide some performance benefit
                    assert speedup >= 1.0, f"Cache should not slow down processing (speedup: {speedup:.2f}x)"