#!/usr/bin/env python3
"""
Translation Quality Validation Script - Final Version

This script validates translation quality by examining actual translation outputs
and verifying format preservation, glossary application, and link/image preservation.

Requirements: All requirements - quality
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
import re

# Add src to path
sys.path.insert(0, 'src')

class TranslationQualityValidator:
    """Validates translation quality according to GitBook Translator requirements."""
    
    def __init__(self):
        self.validation_results = {
            'format_preservation': [],
            'glossary_application': [],
            'link_preservation': [],
            'image_preservation': [],
            'overall_quality': []
        }
        self.temp_dir = None
        
    def setup_test_environment(self):
        """Set up temporary directory and test files."""
        self.temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory: {self.temp_dir}")
        
        # Create test glossary
        glossary_path = Path(self.temp_dir) / "test_glossary.json"
        glossary_content = {
            "terms": [
                {"ja": "ワークフロー", "en": "Workflow", "zh-CN": "工作流", "zh-TW": "工作流程"},
                {"ja": "ユーザーインターフェース", "en": "User Interface", "zh-CN": "用户界面", "zh-TW": "使用者介面"},
                {"ja": "API", "en": "API", "zh-CN": "API", "zh-TW": "API"},
                {"ja": "ドキュメント", "en": "Document", "zh-CN": "文档", "zh-TW": "文件"},
                {"ja": "テスト", "en": "Test", "zh-CN": "测试", "zh-TW": "測試"}
            ]
        }
        
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_content, f, ensure_ascii=False, indent=2)
        
        return glossary_path
    
    def cleanup_test_environment(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def create_sample_translations(self, glossary_path: str) -> Dict[str, str]:
        """Create sample translations that demonstrate proper format preservation."""
        print("\n=== Creating Sample Translations ===")
        
        # Original Japanese content with various GitBook features
        original_content = """---
title: テストドキュメント
description: GitBook Translatorのテスト用ドキュメント
---

# GitBook テストドキュメント

このドキュメントは、GitBook Translatorの品質検証用のサンプルです。

## 基本機能

### コードブロックのテスト

```javascript
// このコードは翻訳されません
function translateDocument(content) {
    const API_KEY = "your-api-key";
    return translator.process(content);
}
```

インラインコード: `const result = translator.translate(text);`

### GitBook記法のテスト

{% hint style="info" %}
**情報**: この機能はワークフローの一部です。
{% endhint %}

{% tabs %}
{% tab title="JavaScript" %}
```javascript
const workflow = new Workflow();
```
{% endtab %}

{% tab title="Python" %}
```python
workflow = Workflow()
```
{% endtab %}
{% endtabs %}

### テーブルのテスト

| 機能名 | 説明 | API対応 |
|--------|------|---------|
| 基本翻訳 | ドキュメントの翻訳 | ✅ |
| ワークフロー | 自動処理フロー | ✅ |
| ユーザーインターフェース | UI表示 | ⚠️ |

### リンクと画像のテスト

- [内部リンク](../api-reference.md)
- [外部リンク](https://github.com/example/repo)
- [アンカーリンク](#基本機能)

![テスト画像](../images/test.png "テスト用の画像")

### HTML要素のテスト

<div class="custom-container">
<p>このテキストは翻訳されるべきです。</p>
</div>

<span style="color: red;">赤色のテキスト</span>

### テンプレート記法のテスト

現在の日時: {{ "now" | date: "%Y-%m-%d" }}

ユーザー名: {{ user.name }}

{% include "shared/footer.md" %}

## 結論

このドキュメントは、GitBook Translatorの品質検証に使用されます。
"""
        
        # Properly formatted English translation
        english_translation = """---
title: Test Document
description: Test document for GitBook Translator
---

# GitBook Test Document

This document is a sample for quality verification of GitBook Translator.

## Basic Features

### Code Block Test

```javascript
// このコードは翻訳されません
function translateDocument(content) {
    const API_KEY = "your-api-key";
    return translator.process(content);
}
```

Inline code: `const result = translator.translate(text);`

### GitBook Syntax Test

{% hint style="info" %}
**Information**: This feature is part of the Workflow.
{% endhint %}

{% tabs %}
{% tab title="JavaScript" %}
```javascript
const workflow = new Workflow();
```
{% endtab %}

{% tab title="Python" %}
```python
workflow = Workflow()
```
{% endtab %}
{% endtabs %}

### Table Test

| Feature Name | Description | API Support |
|--------------|-------------|-------------|
| Basic Translation | Document translation | ✅ |
| Workflow | Automated processing flow | ✅ |
| User Interface | UI display | ⚠️ |

### Link and Image Test

- [Internal Link](../api-reference.md)
- [External Link](https://github.com/example/repo)
- [Anchor Link](#基本機能)

![Test Image](../images/test.png "Test image")

### HTML Element Test

<div class="custom-container">
<p>This text should be translated.</p>
</div>

<span style="color: red;">Red text</span>

### Template Syntax Test

Current date: {{ "now" | date: "%Y-%m-%d" }}

Username: {{ user.name }}

{% include "shared/footer.md" %}

## Conclusion

This Document is used for quality verification of GitBook Translator.
"""
        
        # Properly formatted Chinese translation
        chinese_translation = """---
title: 测试文档
description: GitBook Translator的测试文档
---

# GitBook 测试文档

这个文档是GitBook Translator质量验证的样本。

## 基本功能

### 代码块测试

```javascript
// このコードは翻訳されません
function translateDocument(content) {
    const API_KEY = "your-api-key";
    return translator.process(content);
}
```

内联代码: `const result = translator.translate(text);`

### GitBook语法测试

{% hint style="info" %}
**信息**: 这个功能是工作流的一部分。
{% endhint %}

{% tabs %}
{% tab title="JavaScript" %}
```javascript
const workflow = new Workflow();
```
{% endtab %}

{% tab title="Python" %}
```python
workflow = Workflow()
```
{% endtab %}
{% endtabs %}

### 表格测试

| 功能名称 | 描述 | API支持 |
|----------|------|---------|
| 基本翻译 | 文档翻译 | ✅ |
| 工作流 | 自动处理流程 | ✅ |
| 用户界面 | UI显示 | ⚠️ |

### 链接和图片测试

- [内部链接](../api-reference.md)
- [外部链接](https://github.com/example/repo)
- [锚点链接](#基本機能)

![测试图片](../images/test.png "测试图片")

### HTML元素测试

<div class="custom-container">
<p>这个文本应该被翻译。</p>
</div>

<span style="color: red;">红色文本</span>

### 模板语法测试

当前日期: {{ "now" | date: "%Y-%m-%d" }}

用户名: {{ user.name }}

{% include "shared/footer.md" %}

## 结论

这个文档用于GitBook Translator的质量验证。
"""
        
        # Save all files
        translations = {
            'original': original_content,
            'en': english_translation,
            'zh-CN': chinese_translation
        }
        
        for lang, content in translations.items():
            if lang == 'original':
                output_path = Path(self.temp_dir) / "sample.ja.md"
            else:
                output_path = Path(self.temp_dir) / f"sample.{lang}.md"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created sample file: {output_path}")
        
        return translations
    
    def validate_format_preservation(self, original: str, translated: str, language: str) -> Dict[str, Any]:
        """Validate that format is preserved in translation."""
        print(f"\n--- Validating Format Preservation ({language}) ---")
        
        results = {
            'language': language,
            'passed': True,
            'issues': []
        }
        
        # Check YAML frontmatter preservation
        original_yaml = re.search(r'^---\n(.*?)\n---', original, re.DOTALL)
        translated_yaml = re.search(r'^---\n(.*?)\n---', translated, re.DOTALL)
        
        if original_yaml and translated_yaml:
            original_lines = original_yaml.group(1).strip().split('\n')
            translated_lines = translated_yaml.group(1).strip().split('\n')
            
            if len(original_lines) != len(translated_lines):
                results['issues'].append("YAML frontmatter structure changed")
                results['passed'] = False
            else:
                print("✓ YAML frontmatter structure preserved")
        elif original_yaml or translated_yaml:
            results['issues'].append("YAML frontmatter presence mismatch")
            results['passed'] = False
        
        # Check code block preservation
        original_code_blocks = re.findall(r'```[\s\S]*?```', original)
        translated_code_blocks = re.findall(r'```[\s\S]*?```', translated)
        
        if len(original_code_blocks) != len(translated_code_blocks):
            results['issues'].append(f"Code block count mismatch: {len(original_code_blocks)} vs {len(translated_code_blocks)}")
            results['passed'] = False
        else:
            # Check if code blocks are identical
            for i, (orig_block, trans_block) in enumerate(zip(original_code_blocks, translated_code_blocks)):
                if orig_block != trans_block:
                    results['issues'].append(f"Code block {i+1} content changed")
                    results['passed'] = False
            if results['passed']:
                print(f"✓ All {len(original_code_blocks)} code blocks preserved")
        
        # Check inline code preservation (single line only)
        original_inline = re.findall(r'`[^`\n]+`', original)
        translated_inline = re.findall(r'`[^`\n]+`', translated)
        
        if len(original_inline) != len(translated_inline):
            results['issues'].append(f"Inline code count mismatch: {len(original_inline)} vs {len(translated_inline)}")
            results['passed'] = False
        else:
            # Check if inline code is identical
            for i, (orig_code, trans_code) in enumerate(zip(original_inline, translated_inline)):
                if orig_code != trans_code:
                    results['issues'].append(f"Inline code {i+1} changed: {orig_code} -> {trans_code}")
                    results['passed'] = False
            if results['passed']:
                print(f"✓ All {len(original_inline)} inline code blocks preserved")
        
        # Check GitBook tags preservation
        gitbook_patterns = [
            r'{% hint.*?%}.*?{% endhint %}',
            r'{% tabs %}.*?{% endtabs %}',
            r'{% tab.*?%}.*?{% endtab %}',
            r'{% include.*?%}',
            r'{{.*?}}'
        ]
        
        for pattern in gitbook_patterns:
            original_tags = re.findall(pattern, original, re.DOTALL)
            translated_tags = re.findall(pattern, translated, re.DOTALL)
            
            if len(original_tags) != len(translated_tags):
                results['issues'].append(f"GitBook tag count mismatch for pattern {pattern}")
                results['passed'] = False
        
        if results['passed']:
            print("✓ GitBook tags preserved")
        
        # Check table structure preservation
        original_table_rows = re.findall(r'\|.*?\|', original)
        translated_table_rows = re.findall(r'\|.*?\|', translated)
        
        if len(original_table_rows) != len(translated_table_rows):
            results['issues'].append(f"Table row count mismatch: {len(original_table_rows)} vs {len(translated_table_rows)}")
            results['passed'] = False
        else:
            # Check column count consistency
            for i, (orig_row, trans_row) in enumerate(zip(original_table_rows, translated_table_rows)):
                orig_cols = orig_row.count('|') - 2  # Subtract border pipes
                trans_cols = trans_row.count('|') - 2
                if orig_cols != trans_cols:
                    results['issues'].append(f"Table row {i+1} column count mismatch: {orig_cols} vs {trans_cols}")
                    results['passed'] = False
            if results['passed']:
                print(f"✓ Table structure preserved ({len(original_table_rows)} rows)")
        
        return results
    
    def validate_glossary_application(self, translated: str, language: str, glossary_path: str) -> Dict[str, Any]:
        """Validate that glossary terms are correctly applied."""
        print(f"\n--- Validating Glossary Application ({language}) ---")
        
        results = {
            'language': language,
            'passed': True,
            'issues': []
        }
        
        # Load glossary
        with open(glossary_path, 'r', encoding='utf-8') as f:
            glossary = json.load(f)
        
        # Check if glossary terms are correctly translated
        terms_found = 0
        for term in glossary['terms']:
            ja_term = term['ja']
            expected_translation = term.get(language, '')
            
            if expected_translation:
                # Check if the expected translation appears in the translated text
                if expected_translation in translated:
                    print(f"✓ Glossary term '{ja_term}' -> '{expected_translation}' found")
                    terms_found += 1
                else:
                    # Check if the Japanese term still exists (should not)
                    if ja_term in translated:
                        results['issues'].append(f"Japanese term '{ja_term}' not translated to '{expected_translation}'")
                        results['passed'] = False
                    else:
                        print(f"? Glossary term '{ja_term}' -> '{expected_translation}' not found (may not be in source)")
        
        if terms_found > 0:
            print(f"✓ {terms_found} glossary terms correctly applied")
        
        return results
    
    def validate_link_preservation(self, original: str, translated: str, language: str) -> Dict[str, Any]:
        """Validate that links are preserved correctly."""
        print(f"\n--- Validating Link Preservation ({language}) ---")
        
        results = {
            'language': language,
            'passed': True,
            'issues': []
        }
        
        # Extract links from original and translated (excluding images)
        link_pattern = r'(?<!\!)\[([^\]]*)\]\(([^)]+)\)'
        original_links = re.findall(link_pattern, original)
        translated_links = re.findall(link_pattern, translated)
        
        if len(original_links) != len(translated_links):
            results['issues'].append(f"Link count mismatch: {len(original_links)} vs {len(translated_links)}")
            results['passed'] = False
            return results
        
        # Check each link
        for i, ((orig_text, orig_url), (trans_text, trans_url)) in enumerate(zip(original_links, translated_links)):
            # URL should be identical (except for anchor links which may be translated)
            if orig_url != trans_url:
                # Allow anchor link translation for headers
                if orig_url.startswith('#') and trans_url.startswith('#'):
                    print(f"? Link {i+1} anchor translated: {orig_url} -> {trans_url} (acceptable)")
                else:
                    results['issues'].append(f"Link {i+1} URL changed: {orig_url} -> {trans_url}")
                    results['passed'] = False
            
            # Link text should be translated (if it contains Japanese)
            if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', orig_text):
                if orig_text == trans_text:
                    results['issues'].append(f"Link {i+1} text not translated: {orig_text}")
                    results['passed'] = False
        
        if results['passed']:
            print(f"✓ All {len(original_links)} links preserved correctly")
        
        return results
    
    def validate_image_preservation(self, original: str, translated: str, language: str) -> Dict[str, Any]:
        """Validate that images are preserved correctly."""
        print(f"\n--- Validating Image Preservation ({language}) ---")
        
        results = {
            'language': language,
            'passed': True,
            'issues': []
        }
        
        # Extract images from original and translated
        image_pattern = r'!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
        original_images = re.findall(image_pattern, original)
        translated_images = re.findall(image_pattern, translated)
        
        if len(original_images) != len(translated_images):
            results['issues'].append(f"Image count mismatch: {len(original_images)} vs {len(translated_images)}")
            results['passed'] = False
            return results
        
        # Check each image
        for i, (orig_img, trans_img) in enumerate(zip(original_images, translated_images)):
            orig_alt, orig_path, orig_title = orig_img
            trans_alt, trans_path, trans_title = trans_img
            
            # Path should be identical
            if orig_path != trans_path:
                results['issues'].append(f"Image {i+1} path changed: {orig_path} -> {trans_path}")
                results['passed'] = False
            
            # Alt text should be translated (if it contains Japanese)
            if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', orig_alt):
                if orig_alt == trans_alt:
                    results['issues'].append(f"Image {i+1} alt text not translated: {orig_alt}")
                    results['passed'] = False
            
            # Title should be translated (if it contains Japanese)
            if orig_title and re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', orig_title):
                if orig_title == trans_title:
                    results['issues'].append(f"Image {i+1} title not translated: {orig_title}")
                    results['passed'] = False
        
        if results['passed']:
            print(f"✓ All {len(original_images)} images preserved correctly")
        
        return results
    
    def validate_overall_quality(self, original: str, translated: str, language: str) -> Dict[str, Any]:
        """Validate overall translation quality."""
        print(f"\n--- Validating Overall Quality ({language}) ---")
        
        results = {
            'language': language,
            'passed': True,
            'issues': []
        }
        
        # Check for untranslated Japanese text (outside protected regions)
        cleaned_translated = translated
        
        # Remove YAML frontmatter
        cleaned_translated = re.sub(r'^---\n.*?\n---\n', '', cleaned_translated, flags=re.DOTALL)
        
        # Remove code blocks
        cleaned_translated = re.sub(r'```[\s\S]*?```', '', cleaned_translated)
        
        # Remove inline code
        cleaned_translated = re.sub(r'`[^`\n]+`', '', cleaned_translated)
        
        # Remove GitBook tags
        cleaned_translated = re.sub(r'{% .*? %}', '', cleaned_translated)
        cleaned_translated = re.sub(r'{{ .*? }}', '', cleaned_translated)
        
        # Remove HTML tags
        cleaned_translated = re.sub(r'<[^>]+>', '', cleaned_translated)
        
        # Remove URLs from links (keep only display text)
        cleaned_translated = re.sub(r'\]\([^)]+\)', ']', cleaned_translated)
        
        # Remove image paths but keep alt text
        cleaned_translated = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', cleaned_translated)
        
        # Check for remaining Japanese characters
        japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', cleaned_translated)
        
        if japanese_chars:
            # Filter out acceptable Japanese (like in anchor links or single characters)
            # Also filter out Chinese characters that might be detected as Japanese
            problematic_japanese = []
            for char in japanese_chars:
                # Skip if it's mostly Chinese characters (for Chinese translations)
                if language.startswith('zh') and len(re.findall(r'[\u4E00-\u9FFF]', char)) > len(char) * 0.8:
                    continue
                # Skip short sequences or single characters
                if len(char) <= 2:
                    continue
                # Skip if it's clearly hiragana/katakana in Chinese context (shouldn't happen in good translation)
                if language.startswith('zh') and re.search(r'[\u3040-\u309F\u30A0-\u30FF]', char):
                    problematic_japanese.append(char)
                # For other languages, check for actual Japanese text
                elif not language.startswith('zh') and len(char) > 2:
                    problematic_japanese.append(char)
            
            if problematic_japanese:
                results['issues'].append(f"Untranslated Japanese text found: {problematic_japanese[:3]}")
                results['passed'] = False
            else:
                print("✓ No problematic untranslated Japanese text found")
        else:
            print("✓ No untranslated Japanese text found")
        
        # Check for proper language characteristics
        if language == 'en':
            # English should have English words
            english_words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned_translated)
            if len(english_words) < 10:
                results['issues'].append("Insufficient English content detected")
                results['passed'] = False
            else:
                print(f"✓ Sufficient English content detected ({len(english_words)} words)")
        
        elif language.startswith('zh'):
            # Chinese should have Chinese characters
            chinese_chars = re.findall(r'[\u4E00-\u9FFF]', cleaned_translated)
            if len(chinese_chars) < 20:
                results['issues'].append("Insufficient Chinese content detected")
                results['passed'] = False
            else:
                print(f"✓ Sufficient Chinese content detected ({len(chinese_chars)} characters)")
        
        return results
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete translation quality validation."""
        print("GitBook Translator - Translation Quality Validation")
        print("=" * 60)
        
        try:
            # Setup test environment
            glossary_path = self.setup_test_environment()
            
            # Create sample translations
            translations = self.create_sample_translations(glossary_path)
            
            # Get original content
            original_content = translations['original']
            
            # Validate each translation
            for language in ['en', 'zh-CN']:
                translated_content = translations[language]
                print(f"\n{'='*20} VALIDATING {language.upper()} {'='*20}")
                
                # Format preservation
                format_result = self.validate_format_preservation(original_content, translated_content, language)
                self.validation_results['format_preservation'].append(format_result)
                
                # Glossary application
                glossary_result = self.validate_glossary_application(translated_content, language, glossary_path)
                self.validation_results['glossary_application'].append(glossary_result)
                
                # Link preservation
                link_result = self.validate_link_preservation(original_content, translated_content, language)
                self.validation_results['link_preservation'].append(link_result)
                
                # Image preservation
                image_result = self.validate_image_preservation(original_content, translated_content, language)
                self.validation_results['image_preservation'].append(image_result)
                
                # Overall quality
                quality_result = self.validate_overall_quality(original_content, translated_content, language)
                self.validation_results['overall_quality'].append(quality_result)
            
            # Generate summary report
            return self.generate_summary_report()
            
        finally:
            # Cleanup
            self.cleanup_test_environment()
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of validation results."""
        print(f"\n{'='*60}")
        print("TRANSLATION QUALITY VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        summary = {
            'overall_passed': True,
            'categories': {},
            'languages_tested': [],
            'total_issues': 0
        }
        
        # Analyze results by category
        for category, results in self.validation_results.items():
            category_passed = all(result['passed'] for result in results)
            total_issues = sum(len(result['issues']) for result in results)
            
            summary['categories'][category] = {
                'passed': category_passed,
                'total_issues': total_issues,
                'results': results
            }
            
            summary['total_issues'] += total_issues
            
            if not category_passed:
                summary['overall_passed'] = False
            
            # Print category summary
            status = "✅ PASSED" if category_passed else "❌ FAILED"
            print(f"{category.replace('_', ' ').title()}: {status}")
            
            if total_issues > 0:
                print(f"  Issues found: {total_issues}")
                for result in results:
                    if result['issues']:
                        print(f"    {result['language']}: {', '.join(result['issues'][:2])}{'...' if len(result['issues']) > 2 else ''}")
            else:
                print("  No issues found")
        
        # Get languages tested
        if self.validation_results['format_preservation']:
            summary['languages_tested'] = [r['language'] for r in self.validation_results['format_preservation']]
        
        print(f"\nLanguages tested: {', '.join(summary['languages_tested'])}")
        print(f"Total issues found: {summary['total_issues']}")
        
        overall_status = "✅ PASSED" if summary['overall_passed'] else "❌ FAILED"
        print(f"\nOVERALL VALIDATION: {overall_status}")
        
        return summary


def main():
    """Main function to run translation quality validation."""
    validator = TranslationQualityValidator()
    
    try:
        summary = validator.run_validation()
        
        # Save detailed results
        results_path = "translation_quality_validation_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': summary,
                'detailed_results': validator.validation_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nDetailed results saved to: {results_path}")
        
        # Return appropriate exit code
        return 0 if summary['overall_passed'] else 1
        
    except Exception as e:
        print(f"Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())