"""Tool for loading glossary."""

import json
import csv
from pathlib import Path
from typing import Dict, Any, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..models.glossary_models import Glossary


class LoadGlossaryInput(BaseModel):
    """Input schema for LoadGlossaryTool."""

    glossary_path: str = Field(description="Path to glossary file (JSON or CSV)")
    target_language: Optional[str] = Field(default=None, description="Target language code for language-specific glossaries")


class LoadGlossaryTool(BaseTool):
    """Tool for loading and parsing glossary file."""

    name: str = "load_glossary"
    description: str = """
    Loads a glossary file (JSON or CSV) and parses term mappings.
    Supports both unified glossary format and language-specific glossary files.
    If target_language is provided, will try to load language-specific glossary first.
    Input should be a JSON with: glossary_path (string), target_language (optional string).
    Returns glossary with term mappings for multiple languages.
    """
    args_schema: type[BaseModel] = LoadGlossaryInput

    def _run(self, glossary_path: str, target_language: Optional[str] = None) -> str:
        """Execute the tool to load and parse glossary.
        
        Args:
            glossary_path: Path to glossary file
            target_language: Target language code for language-specific glossaries
            
        Returns:
            JSON string containing glossary data
        """
        try:
            glossary = self.load_glossary(glossary_path, target_language)
            
            result_data = {
                "success": True,
                "format": glossary.format,
                "mappings": glossary.mappings,
                "term_count": len(glossary.mappings)
            }
            
            return json.dumps(result_data, ensure_ascii=False)
            
        except FileNotFoundError as e:
            return json.dumps({
                "success": False,
                "error": f"Glossary file not found: {glossary_path}",
                "mappings": {}
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to load glossary: {str(e)}",
                "mappings": {}
            })

    def load_glossary(self, glossary_path: str, target_language: str = None) -> Glossary:
        """Load and parse glossary file.
        
        Args:
            glossary_path: Path to glossary file or base path for language-specific files
            target_language: Target language code (e.g., 'en', 'zh-CN') for language-specific glossaries
            
        Returns:
            Glossary object with term mappings
            
        Raises:
            FileNotFoundError: If glossary file doesn't exist
            ValueError: If glossary format is invalid
        """
        # Check if language-specific glossaries exist
        base_path_obj = Path(glossary_path)
        base_dir = base_path_obj.parent
        base_name = base_path_obj.stem
        
        # Look for language-specific glossary files
        language_specific_files = []
        for pattern in ["glossary_*.json", "dictionary_*.json"]:
            language_specific_files.extend(base_dir.glob(pattern))
        
        if language_specific_files:
            # Load all language-specific glossaries and merge them
            return self._load_all_language_specific_glossaries(base_dir, base_name)
        
        # If target_language is provided, try to load language-specific glossary
        if target_language:
            language_specific_path = self._get_language_specific_path(glossary_path, target_language)
            if language_specific_path and language_specific_path.exists():
                return self._load_language_specific_glossary(language_specific_path, target_language)
        
        # Fall back to original glossary file
        path = Path(glossary_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Glossary file not found: {glossary_path}")
        
        # Detect format based on file extension
        if path.suffix.lower() == '.json':
            return self._load_json_glossary(path)
        elif path.suffix.lower() == '.csv':
            return self._load_csv_glossary(path)
        else:
            # Try to auto-detect format by reading content
            return self._auto_detect_and_load(path)

    def _load_json_glossary(self, path: Path) -> Glossary:
        """Load glossary from JSON file.
        
        Args:
            path: Path to JSON glossary file
            
        Returns:
            Glossary object
            
        Raises:
            ValueError: If JSON format is invalid
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse JSON glossary format
        mappings = self._parse_json_format(data)
        
        return Glossary(format="auto-detected", mappings=mappings)

    def _load_csv_glossary(self, path: Path) -> Glossary:
        """Load glossary from CSV file.
        
        Args:
            path: Path to CSV glossary file
            
        Returns:
            Glossary object
            
        Raises:
            ValueError: If CSV format is invalid
        """
        mappings: Dict[str, Dict[str, str]] = {}
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")
            
            # First column is the term, rest are language translations
            for row in reader:
                if not row:
                    continue
                
                # Get term from first column
                term = None
                term_value = None
                
                for key, value in row.items():
                    if term is None:
                        term = key
                        term_value = value
                        break
                
                if not term_value:
                    continue
                
                # Create mapping for this term
                term_mappings: Dict[str, str] = {}
                
                for lang, translation in row.items():
                    if lang != term and translation:
                        term_mappings[lang] = translation
                
                if term_mappings:
                    mappings[term_value] = term_mappings
        
        return Glossary(format="auto-detected", mappings=mappings)

    def _get_language_specific_path(self, base_path: str, target_language: str) -> Optional[Path]:
        """Get language-specific glossary file path.
        
        Args:
            base_path: Base glossary path (e.g., 'glossary.json')
            target_language: Target language code (e.g., 'en', 'zh-CN')
            
        Returns:
            Path to language-specific glossary file or None if not found
        """
        base_path_obj = Path(base_path)
        base_dir = base_path_obj.parent
        base_name = base_path_obj.stem  # filename without extension
        
        # Try different naming patterns for language-specific glossaries
        patterns = [
            f"{base_name}_{target_language}.json",  # glossary_en.json
            f"{base_name}-{target_language}.json",  # glossary-en.json
            f"dictionary_{target_language}.json",   # dictionary_en.json (existing pattern)
        ]
        
        for pattern in patterns:
            lang_specific_path = base_dir / pattern
            if lang_specific_path.exists():
                return lang_specific_path
        
        return None

    def _load_language_specific_glossary(self, path: Path, target_language: str) -> Glossary:
        """Load language-specific glossary file.
        
        Args:
            path: Path to language-specific glossary file
            target_language: Target language code
            
        Returns:
            Glossary object with term mappings
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Language-specific glossaries use flat format: {"japanese_term": "translation"}
        mappings: Dict[str, Dict[str, str]] = {}
        
        if isinstance(data, dict):
            for japanese_term, translation in data.items():
                if isinstance(translation, str):
                    mappings[japanese_term] = {target_language: translation}
        
        return Glossary(format="language-specific", mappings=mappings)

    def _load_all_language_specific_glossaries(self, base_dir: Path, base_name: str) -> Glossary:
        """Load all language-specific glossary files and merge them.
        
        Args:
            base_dir: Directory containing glossary files
            base_name: Base name for glossary files
            
        Returns:
            Glossary object with merged term mappings from all languages
        """
        merged_mappings: Dict[str, Dict[str, str]] = {}
        
        # Look for language-specific files with different patterns
        patterns = [
            f"{base_name}_*.json",      # glossary_en.json
            f"{base_name}-*.json",      # glossary-en.json  
            "dictionary_*.json",        # dictionary_en.json
        ]
        
        for pattern in patterns:
            for file_path in base_dir.glob(pattern):
                # Extract language code from filename
                filename = file_path.stem
                if "_" in filename:
                    lang_code = filename.split("_")[-1]
                elif "-" in filename:
                    lang_code = filename.split("-")[-1]
                else:
                    continue
                
                try:
                    # Load the language-specific glossary
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict):
                        for japanese_term, translation in data.items():
                            if isinstance(translation, str):
                                if japanese_term not in merged_mappings:
                                    merged_mappings[japanese_term] = {}
                                merged_mappings[japanese_term][lang_code] = translation
                                
                except Exception as e:
                    # Skip files that can't be loaded
                    print(f"Warning: Could not load {file_path}: {e}")
                    continue
        
        return Glossary(format="merged-language-specific", mappings=merged_mappings)

    def _auto_detect_and_load(self, path: Path) -> Glossary:
        """Auto-detect glossary format and load.
        
        Args:
            path: Path to glossary file
            
        Returns:
            Glossary object
            
        Raises:
            ValueError: If format cannot be detected
        """
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Try JSON first
        if content.startswith('{') or content.startswith('['):
            try:
                data = json.loads(content)
                mappings = self._parse_json_format(data)
                return Glossary(format="auto-detected", mappings=mappings)
            except json.JSONDecodeError:
                pass
        
        # Try CSV
        try:
            lines = content.split('\n')
            if len(lines) > 0:
                # Check if it looks like CSV (has commas)
                if ',' in lines[0]:
                    path.seek(0) if hasattr(path, 'seek') else None
                    return self._load_csv_glossary(path)
        except Exception:
            pass
        
        raise ValueError(f"Unable to detect glossary format for file: {path}")

    def _parse_json_format(self, data: Any) -> Dict[str, Dict[str, str]]:
        """Parse JSON glossary format.
        
        Supports formats like:
        {
          "terms": [
            {
              "ja": "term",
              "en": "translation",
              "zh-CN": "translation"
            }
          ]
        }
        
        Or flat format:
        {
          "term": {
            "en": "translation",
            "zh-CN": "translation"
          }
        }
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Dictionary mapping terms to language translations
            
        Raises:
            ValueError: If JSON format is invalid
        """
        mappings: Dict[str, Dict[str, str]] = {}
        
        if isinstance(data, dict):
            # Check if it has "terms" key (array format)
            if "terms" in data and isinstance(data["terms"], list):
                for term_entry in data["terms"]:
                    if isinstance(term_entry, dict):
                        # Extract term and translations
                        # Assume first key is the source language (usually "ja")
                        term_key = None
                        term_value = None
                        translations: Dict[str, str] = {}
                        
                        for lang, value in term_entry.items():
                            if term_key is None:
                                term_key = lang
                                term_value = value
                            else:
                                translations[lang] = value
                        
                        if term_value and translations:
                            mappings[term_value] = translations
            else:
                # Flat format: term -> {lang -> translation}
                for term, translations in data.items():
                    if isinstance(translations, dict):
                        # Filter out non-string values
                        filtered_translations = {
                            lang: str(trans)
                            for lang, trans in translations.items()
                            if isinstance(trans, (str, int, float))
                        }
                        if filtered_translations:
                            mappings[term] = filtered_translations
        
        return mappings

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
