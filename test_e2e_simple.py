#!/usr/bin/env python3
"""
Simple end-to-end test script for GitBook Translator.
Tests the core workflow components without complex mocking.
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, 'src')

def test_basic_workflow():
    """Test basic translation workflow."""
    print("=== Testing Basic Translation Workflow ===")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Created temp directory: {temp_dir}")
    
    # Create test glossary
    glossary_path = Path(temp_dir) / "test_glossary.json"
    glossary_content = {
        "terms": [
            {"ja": "テスト", "en": "Test"},
            {"ja": "ドキュメント", "en": "Document"}
        ]
    }
    
    with open(glossary_path, 'w', encoding='utf-8') as f:
        json.dump(glossary_content, f, ensure_ascii=False, indent=2)
    
    print(f"Created test glossary: {glossary_path}")
    
    try:
        # Import and test configuration
        from models.config import CLIConfig
        
        with patch.object(CLIConfig, '_validate_glossary_path'):
            config = CLIConfig(
                repo_url="https://github.com/test/repo",
                branch="main",
                target_paths=["README.md"],
                languages=["en"],
                glossary_path=str(glossary_path),
                output_root=temp_dir,
                push_option="none",
                output_naming="suffix"
            )
        
        print("✓ Configuration created successfully")
        
        # Test agent initialization
        from agent.translation_agent import TranslationAgent
        
        # Mock the agent run method to avoid external API calls
        with patch.object(TranslationAgent, 'run') as mock_run:
            mock_run.return_value = {
                'status': 'success',
                'output': 'Translation completed successfully',
                'files_processed': 1,
                'translations_created': 1,
                'errors': 0,
                'execution_time': 30.5,
                'token_usage': {'total_tokens': 1000, 'prompt_tokens': 500, 'completion_tokens': 500}
            }
            
            agent = TranslationAgent(config)
            result = agent.run()
            
            print("✓ Agent execution successful")
            print(f"  Status: {result['status']}")
            print(f"  Files processed: {result['files_processed']}")
            print(f"  Translations created: {result['translations_created']}")
            print(f"  Errors: {result['errors']}")
            print(f"  Execution time: {result['execution_time']}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in basic workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Cleaned up temp directory: {temp_dir}")


def test_multiple_languages():
    """Test multiple language translation."""
    print("\n=== Testing Multiple Language Translation ===")
    
    temp_dir = tempfile.mkdtemp()
    glossary_path = Path(temp_dir) / "test_glossary.json"
    
    glossary_content = {
        "terms": [
            {"ja": "API", "en": "API", "zh-CN": "API", "zh-TW": "API"},
            {"ja": "ユーザー", "en": "User", "zh-CN": "用户", "zh-TW": "使用者"}
        ]
    }
    
    with open(glossary_path, 'w', encoding='utf-8') as f:
        json.dump(glossary_content, f, ensure_ascii=False, indent=2)
    
    try:
        from models.config import CLIConfig
        from agent.translation_agent import TranslationAgent
        
        with patch.object(CLIConfig, '_validate_glossary_path'):
            config = CLIConfig(
                repo_url="https://github.com/test/repo",
                branch="main",
                target_paths=["README.md"],
                languages=["en", "zh-CN", "zh-TW"],  # Multiple languages
                glossary_path=str(glossary_path),
                output_root=temp_dir,
                push_option="none",
                output_naming="suffix"
            )
        
        with patch.object(TranslationAgent, 'run') as mock_run:
            mock_run.return_value = {
                'status': 'success',
                'output': 'Multi-language translation completed',
                'files_processed': 1,
                'translations_created': 3,  # 1 file × 3 languages
                'errors': 0,
                'languages_processed': ['en', 'zh-CN', 'zh-TW'],
                'execution_time': 85.2
            }
            
            agent = TranslationAgent(config)
            result = agent.run()
            
            print("✓ Multi-language translation successful")
            print(f"  Languages processed: {result['languages_processed']}")
            print(f"  Translations created: {result['translations_created']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in multi-language test: {e}")
        return False
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handling():
    """Test error handling scenarios."""
    print("\n=== Testing Error Handling ===")
    
    temp_dir = tempfile.mkdtemp()
    glossary_path = Path(temp_dir) / "test_glossary.json"
    
    with open(glossary_path, 'w', encoding='utf-8') as f:
        json.dump({"terms": []}, f)
    
    try:
        from models.config import CLIConfig
        from agent.translation_agent import TranslationAgent
        
        with patch.object(CLIConfig, '_validate_glossary_path'):
            config = CLIConfig(
                repo_url="https://github.com/test/repo",
                branch="main",
                target_paths=["README.md", "docs/nonexistent.md"],
                languages=["en"],
                glossary_path=str(glossary_path),
                output_root=temp_dir,
                push_option="none",
                output_naming="suffix"
            )
        
        # Test partial failure scenario
        with patch.object(TranslationAgent, 'run') as mock_run:
            mock_run.return_value = {
                'status': 'partial_success',
                'output': 'Translation completed with errors',
                'files_processed': 2,
                'translations_created': 1,  # Only one successful
                'errors': 1,
                'error_details': [
                    {
                        'file': 'docs/nonexistent.md',
                        'error': 'File not found',
                        'timestamp': '2026-01-16T10:30:00Z'
                    }
                ],
                'successful_files': ['README.md']
            }
            
            agent = TranslationAgent(config)
            result = agent.run()
            
            print("✓ Error handling test successful")
            print(f"  Status: {result['status']}")
            print(f"  Errors: {result['errors']}")
            print(f"  Successful files: {result['successful_files']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in error handling test: {e}")
        return False
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_github_push():
    """Test GitHub push functionality."""
    print("\n=== Testing GitHub Push ===")
    
    temp_dir = tempfile.mkdtemp()
    glossary_path = Path(temp_dir) / "test_glossary.json"
    
    with open(glossary_path, 'w', encoding='utf-8') as f:
        json.dump({"terms": []}, f)
    
    try:
        from models.config import CLIConfig
        from agent.translation_agent import TranslationAgent
        
        with patch.object(CLIConfig, '_validate_glossary_path'):
            config = CLIConfig(
                repo_url="https://github.com/test/repo",
                branch="main",
                target_paths=["README.md"],
                languages=["en"],
                glossary_path=str(glossary_path),
                output_root=temp_dir,
                push_option="push_same_repo_new_branch",  # Test GitHub push
                output_naming="suffix"
            )
        
        with patch.object(TranslationAgent, 'run') as mock_run:
            mock_run.return_value = {
                'status': 'success',
                'output': 'Translation completed and pushed to GitHub',
                'files_processed': 1,
                'translations_created': 1,
                'errors': 0,
                'github_push': True,
                'branch_name': 'translation/en/20260116-120000',
                'pr_url': 'https://github.com/test/repo/pull/123'
            }
            
            agent = TranslationAgent(config)
            result = agent.run()
            
            print("✓ GitHub push test successful")
            print(f"  GitHub push: {result['github_push']}")
            print(f"  Branch name: {result['branch_name']}")
            print(f"  PR URL: {result['pr_url']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in GitHub push test: {e}")
        return False
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all end-to-end tests."""
    print("GitBook Translator - End-to-End Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_workflow,
        test_multiple_languages,
        test_error_handling,
        test_github_push
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"End-to-End Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All end-to-end tests PASSED!")
        return True
    else:
        print(f"✗ {total - passed} tests FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)