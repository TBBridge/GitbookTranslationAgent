"""Property-based tests for LoadGlossaryTool."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from hypothesis import given, settings, strategies as st

from src.tools.load_glossary import LoadGlossaryTool


# Custom strategies for generating glossary data
@st.composite
def glossary_terms(draw):
    """Generate glossary term entries."""
    # Generate Japanese term
    ja_term = draw(st.text(
        alphabet=st.characters(
            blacklist_categories=('Cc', 'Cs'),
            blacklist_characters='\n\r\t'
        ),
        min_size=1,
        max_size=50
    ))
    
    # Generate translations for multiple languages
    languages = ['en', 'zh-CN', 'zh-TW', 'ko']
    translations = {}
    
    for lang in draw(st.lists(st.sampled_from(languages), min_size=1, max_size=4, unique=True)):
        translation = draw(st.text(
            alphabet=st.characters(
                blacklist_categories=('Cc', 'Cs'),
                blacklist_characters='\n\r\t'
            ),
            min_size=1,
            max_size=50
        ))
        translations[lang] = translation
    
    return {
        "ja": ja_term,
        **translations
    }


@st.composite
def glossary_json_data(draw):
    """Generate valid glossary JSON data."""
    terms = draw(st.lists(glossary_terms(), min_size=1, max_size=10, unique_by=lambda t: t['ja']))
    return {"terms": terms}


class TestGlossaryTermConsistency:
    """
    Feature: gitbook-translator, Property 10: Glossary term consistency
    
    Property: For any text containing a glossary term, all occurrences of that term 
    should be translated to the exact same target language translation specified in the glossary.
    
    Validates: Requirements 8.3, 8.4
    """

    @given(glossary_json_data())
    @settings(max_examples=100, deadline=None)
    def test_glossary_term_consistency(self, glossary_data):
        """Test that glossary terms are loaded consistently.
        
        For any glossary data, when loaded, each term should have exactly one
        translation per language, and that translation should be consistent
        across multiple loads.
        """
        with TemporaryDirectory() as tmpdir:
            glossary_path = Path(tmpdir) / "glossary.json"
            
            # Write glossary to file
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False)
            
            # Load glossary
            tool = LoadGlossaryTool()
            glossary = tool.load_glossary(str(glossary_path))
            
            # Verify consistency: each term should have consistent translations
            for term_entry in glossary_data["terms"]:
                ja_term = term_entry["ja"]
                
                # Verify term exists in mappings
                assert ja_term in glossary.mappings, f"Term '{ja_term}' not found in glossary"
                
                # Verify each language translation is consistent
                for lang, expected_translation in term_entry.items():
                    if lang != "ja":
                        # Verify the translation matches exactly
                        assert lang in glossary.mappings[ja_term], \
                            f"Language '{lang}' not found for term '{ja_term}'"
                        
                        actual_translation = glossary.mappings[ja_term][lang]
                        assert actual_translation == expected_translation, \
                            f"Translation mismatch for '{ja_term}' in '{lang}': " \
                            f"expected '{expected_translation}', got '{actual_translation}'"

    @given(glossary_json_data())
    @settings(max_examples=100, deadline=None)
    def test_glossary_term_consistency_multiple_loads(self, glossary_data):
        """Test that loading the same glossary multiple times produces identical results.
        
        For any glossary data, loading it multiple times should produce
        identical term mappings (idempotency).
        """
        with TemporaryDirectory() as tmpdir:
            glossary_path = Path(tmpdir) / "glossary.json"
            
            # Write glossary to file
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False)
            
            # Load glossary multiple times
            tool = LoadGlossaryTool()
            glossary1 = tool.load_glossary(str(glossary_path))
            glossary2 = tool.load_glossary(str(glossary_path))
            
            # Verify both loads produce identical mappings
            assert glossary1.mappings == glossary2.mappings, \
                "Multiple loads of the same glossary produced different results"
            
            # Verify all terms are present in both
            assert set(glossary1.mappings.keys()) == set(glossary2.mappings.keys()), \
                "Term sets differ between loads"


class TestMultiLanguageGlossaryApplication:
    """
    Feature: gitbook-translator, Property 17: Multi-language glossary application
    
    Property: For any text translated to multiple target languages, each language 
    should use its corresponding glossary mappings from the glossary file.
    
    Validates: Requirements 15.2
    """

    @given(glossary_json_data())
    @settings(max_examples=100)
    def test_multi_language_glossary_application(self, glossary_data):
        """Test that glossary supports multiple language mappings correctly.
        
        For any glossary with multiple languages, each term should have
        independent translations for each language.
        """
        with TemporaryDirectory() as tmpdir:
            glossary_path = Path(tmpdir) / "glossary.json"
            
            # Write glossary to file
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False)
            
            # Load glossary
            tool = LoadGlossaryTool()
            glossary = tool.load_glossary(str(glossary_path))
            
            # Verify each term has translations for all specified languages
            for term_entry in glossary_data["terms"]:
                ja_term = term_entry["ja"]
                
                # Get all languages specified for this term (excluding 'ja')
                specified_languages = {k for k in term_entry.keys() if k != "ja"}
                
                # Verify all specified languages are in the glossary
                loaded_languages = set(glossary.mappings[ja_term].keys())
                assert loaded_languages == specified_languages, \
                    f"Language mismatch for term '{ja_term}': " \
                    f"expected {specified_languages}, got {loaded_languages}"

    @given(glossary_json_data())
    @settings(max_examples=100)
    def test_glossary_language_independence(self, glossary_data):
        """Test that translations for different languages are independent.
        
        For any glossary, translations for different languages should not
        affect each other - changing one language's translation should not
        affect other languages.
        """
        with TemporaryDirectory() as tmpdir:
            glossary_path = Path(tmpdir) / "glossary.json"
            
            # Write glossary to file
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False)
            
            # Load glossary
            tool = LoadGlossaryTool()
            glossary = tool.load_glossary(str(glossary_path))
            
            # Verify that each language translation is unique and independent
            for term_entry in glossary_data["terms"]:
                ja_term = term_entry["ja"]
                
                # Get all translations for this term
                translations = glossary.mappings[ja_term]
                
                # Verify each language has a translation
                for lang in translations:
                    assert lang in term_entry, \
                        f"Language '{lang}' in glossary but not in source data"
                    
                    # Verify the translation is not empty
                    assert translations[lang], \
                        f"Empty translation for '{ja_term}' in language '{lang}'"
                    
                    # Verify the translation matches the source
                    assert translations[lang] == term_entry[lang], \
                        f"Translation mismatch for '{ja_term}' in '{lang}'"

    @given(glossary_json_data())
    @settings(max_examples=100)
    def test_glossary_preserves_all_languages(self, glossary_data):
        """Test that all language mappings are preserved during loading.
        
        For any glossary with multiple languages, all language mappings
        should be preserved exactly as specified.
        """
        with TemporaryDirectory() as tmpdir:
            glossary_path = Path(tmpdir) / "glossary.json"
            
            # Write glossary to file
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False)
            
            # Load glossary
            tool = LoadGlossaryTool()
            glossary = tool.load_glossary(str(glossary_path))
            
            # Count total languages across all terms
            all_languages = set()
            for term_entry in glossary_data["terms"]:
                for lang in term_entry.keys():
                    if lang != "ja":
                        all_languages.add(lang)
            
            # Verify all languages are represented in loaded glossary
            loaded_languages = set()
            for term_mappings in glossary.mappings.values():
                for lang in term_mappings.keys():
                    loaded_languages.add(lang)
            
            assert loaded_languages == all_languages, \
                f"Language mismatch: expected {all_languages}, got {loaded_languages}"
