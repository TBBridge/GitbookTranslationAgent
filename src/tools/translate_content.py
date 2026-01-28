"""Tool for translating content."""

import os
import json
import time
from typing import List, Dict, Any, Optional

from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field
from openai import APIError, APITimeoutError, RateLimitError

from ..models.translation_models import TranslationRequest, TranslationResult
from ..models.markdown_models import Segment, SegmentType, StructureInfo
from ..models.glossary_models import Glossary


class TranslateContentInput(BaseModel):
    """Input schema for TranslateContentTool."""

    segments: List[Dict[str, Any]] = Field(description="List of segments to translate")
    target_language: str = Field(description="Target language code (e.g., 'en', 'zh-CN')")
    glossary: Dict[str, Any] = Field(description="Glossary with term mappings")
    structure: Dict[str, Any] = Field(description="Structure information for reconstruction")


class TranslateContentTool(BaseTool):
    """Tool for translating content using LLM."""

    name: str = "translate_content"
    description: str = """
    Translates Japanese text segments to target language using LLM.
    Input should be a JSON with: segments (list), target_language (string), glossary (dict), structure (dict).
    Returns translated segments and reconstructed content.
    """
    args_schema: type[BaseModel] = TranslateContentInput

    # LLM client (initialized in __init__)
    llm: Optional[ChatOpenAI] = None
    
    # Retry configuration
    max_manual_retries: int = 2  # Additional retries for invalid response format
    retry_delay_base: int = 2  # Base delay in seconds for exponential backoff

    def __init__(self, **kwargs):
        """Initialize the tool with LLM client."""
        super().__init__(**kwargs)
        
        # Initialize LangChain ChatOpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Try alternative environment variable
            api_key = os.environ.get("OPENAI_API_KEY")
        
        # Initialize with retry logic and timeout
        # LangChain's built-in retry mechanism handles:
        # - Exponential backoff for rate limits
        # - Automatic retries for transient failures
        # - Timeout handling
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,  # Lower temperature for more consistent translations
            max_retries=3,  # Retry up to 3 times with exponential backoff
            request_timeout=120,  # 120 second timeout for translation requests
            api_key=api_key
        )

    def _run(
        self,
        segments: List[Dict[str, Any]],
        target_language: str,
        glossary: Dict[str, Any],
        structure: Dict[str, Any]
    ) -> str:
        """Execute the tool to translate content.
        
        Args:
            segments: List of segment dictionaries
            target_language: Target language code
            glossary: Glossary dictionary with term mappings
            structure: Structure information dictionary
            
        Returns:
            JSON string containing translated segments and reconstructed content
        """
        try:
            # Convert dictionaries back to dataclass objects
            segment_objects = self._parse_segments(segments)
            glossary_obj = self._parse_glossary(glossary)
            structure_obj = self._parse_structure(structure)
            
            # Create translation request
            request = TranslationRequest(
                segments=segment_objects,
                target_language=target_language,
                glossary=glossary_obj,
                structure=structure_obj
            )
            
            # Perform translation
            result = self.translate(request)
            
            # Convert result to JSON-serializable format
            result_data = {
                "success": True,
                "translated_segments": [
                    {
                        "type": seg.type.value,
                        "content": seg.content,
                        "start_line": seg.start_line,
                        "end_line": seg.end_line,
                        "metadata": {
                            "protection_reason": seg.metadata.protection_reason if seg.metadata else None,
                            "link_url": seg.metadata.link_url if seg.metadata else None,
                            "alt_text": seg.metadata.alt_text if seg.metadata else None
                        } if seg.metadata else None
                    }
                    for seg in result.translated_segments
                ],
                "reconstructed_content": result.reconstructed_content
            }
            
            return json.dumps(result_data, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Translation failed: {str(e)}",
                "translated_segments": [],
                "reconstructed_content": ""
            })

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate content using LLM with retry logic and error handling.
        
        Args:
            request: Translation request with segments, language, glossary, structure
            
        Returns:
            TranslationResult with translated segments and reconstructed content
            
        Raises:
            Exception: If translation fails after all retry attempts
        """
        # Build glossary terms string for prompt
        glossary_terms = self._format_glossary_for_prompt(
            request.glossary,
            request.target_language
        )
        
        # Build structure information string for prompt
        structure_info = self._format_structure_for_prompt(request.structure)
        
        # Build translation prompt with comprehensive format preservation rules
        translation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator specializing in technical documentation for GitBook-formatted content.

Task: Translate the following Japanese text segments to {target_language}.

CRITICAL FORMAT PRESERVATION RULES (HIGHEST PRIORITY):
1. Preserve ALL line breaks, blank lines, indentation, and spacing EXACTLY as in the original
2. Preserve ALL GitBook-specific syntax:
   - YAML frontmatter (--- to ---): Keep structure and keys unchanged
   - GitBook blocks: {{% hint %}}, {{% tabs %}}, {{% tab %}}, {{% endtab %}}, {{% endtabs %}}, {{% include %}}, {{% embed %}}, {{% file %}} - DO NOT MODIFY
   - Template expressions: {{{{ ... }}}} and {{% ... %}} - DO NOT MODIFY
   - HTML tags and attributes - DO NOT MODIFY
3. Preserve ALL code blocks and inline code:
   - Fenced code blocks (``` to ```) - DO NOT TRANSLATE CONTENT
   - Inline code (`...`) - DO NOT TRANSLATE CONTENT
4. Preserve ALL links and paths:
   - Link URLs: [text](URL) - Translate text ONLY, keep URL unchanged
   - Image paths: ![alt](path) - Translate alt ONLY, keep path unchanged
   - Relative paths, anchors (#...), file references - DO NOT MODIFY
5. Preserve ALL table structure:
   - Keep pipe characters (|) and alignment markers (:--:) unchanged
   - Maintain exact column count and structure
   - Translate cell content ONLY

TRANSLATION RULES:
1. Translate ONLY Japanese text (Hiragana, Katakana, Kanji)
2. Keep non-Japanese text (English, numbers, symbols) unchanged
3. Use formal, polite, business-appropriate tone suitable for professional documentation
4. Maintain semantic accuracy and faithfulness to the original meaning
5. Ensure clarity in procedural content, steps, warnings, and notices
6. Apply glossary terms EXACTLY as specified - no variations allowed
7. Preserve punctuation usage and positioning

GLOSSARY TERMS (Use these exact translations):
{glossary_terms}

STRUCTURE INFORMATION:
{structure_info}

OUTPUT REQUIREMENTS:
- Return ONLY the translated text for each segment
- Preserve the exact structure and formatting
- Do NOT add explanations, comments, or notes
- Ensure output is valid Markdown compatible with GitBook"""),
            ("user", """Segments to Translate:
{segments}

Translate each segment following ALL format preservation rules above. Return results in the same order.""")
        ])
        
        # Extract translatable segments only
        translatable_segments = [
            seg for seg in request.segments
            if seg.type == SegmentType.TRANSLATABLE
        ]
        
        if not translatable_segments:
            # No translatable content, return original segments
            return TranslationResult(
                translated_segments=request.segments,
                reconstructed_content=self._reconstruct_content(request.segments)
            )
        
        # Format segments for prompt
        segments_text = self._format_segments_for_prompt(translatable_segments)
        
        # Retry loop for handling invalid response format
        last_error = None
        for attempt in range(self.max_manual_retries + 1):
            try:
                # Invoke LLM with built-in retry logic
                prompt_value = translation_prompt.format_messages(
                    target_language=request.target_language,
                    glossary_terms=glossary_terms,
                    structure_info=structure_info,
                    segments=segments_text
                )
                
                response = self.llm.invoke(prompt_value)
                translated_text = response.content
                
                # Validate response is not empty
                if not translated_text or not translated_text.strip():
                    raise ValueError("LLM returned empty response")
                
                # Parse translated segments from response
                translated_segments = self._parse_translation_response(
                    translated_text,
                    translatable_segments,
                    request.segments
                )
                
                # Validate that we got translations for all segments
                if len(translated_segments) != len(request.segments):
                    raise ValueError(
                        f"Segment count mismatch: expected {len(request.segments)}, "
                        f"got {len(translated_segments)}"
                    )
                
                # Reconstruct full content
                reconstructed_content = self._reconstruct_content(translated_segments)
                
                return TranslationResult(
                    translated_segments=translated_segments,
                    reconstructed_content=reconstructed_content
                )
                
            except APITimeoutError as e:
                # Handle timeout errors with exponential backoff
                last_error = e
                if attempt < self.max_manual_retries:
                    delay = self.retry_delay_base ** (attempt + 1)
                    print(f"Translation timeout (attempt {attempt + 1}/{self.max_manual_retries + 1}). "
                          f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"Translation failed after {self.max_manual_retries + 1} attempts due to timeout: {str(e)}"
                    ) from e
                    
            except RateLimitError as e:
                # Handle rate limit errors (LangChain should handle this, but just in case)
                last_error = e
                if attempt < self.max_manual_retries:
                    delay = self.retry_delay_base ** (attempt + 2)  # Longer delay for rate limits
                    print(f"Rate limit exceeded (attempt {attempt + 1}/{self.max_manual_retries + 1}). "
                          f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"Translation failed after {self.max_manual_retries + 1} attempts due to rate limit: {str(e)}"
                    ) from e
                    
            except (ValueError, OutputParserException) as e:
                # Handle invalid response format
                last_error = e
                if attempt < self.max_manual_retries:
                    delay = self.retry_delay_base ** attempt
                    print(f"Invalid response format (attempt {attempt + 1}/{self.max_manual_retries + 1}). "
                          f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"Translation failed after {self.max_manual_retries + 1} attempts due to invalid response format: {str(e)}"
                    ) from e
                    
            except APIError as e:
                # Handle general API errors
                last_error = e
                if attempt < self.max_manual_retries:
                    delay = self.retry_delay_base ** (attempt + 1)
                    print(f"API error (attempt {attempt + 1}/{self.max_manual_retries + 1}). "
                          f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"Translation failed after {self.max_manual_retries + 1} attempts due to API error: {str(e)}"
                    ) from e
                    
            except Exception as e:
                # Handle unexpected errors
                last_error = e
                if attempt < self.max_manual_retries:
                    delay = self.retry_delay_base ** attempt
                    print(f"Unexpected error (attempt {attempt + 1}/{self.max_manual_retries + 1}): {str(e)}. "
                          f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"Translation failed after {self.max_manual_retries + 1} attempts: {str(e)}"
                    ) from e
        
        # Should never reach here, but just in case
        raise Exception(f"Translation failed: {str(last_error)}")

    def _format_glossary_for_prompt(
        self,
        glossary: Glossary,
        target_language: str
    ) -> str:
        """Format glossary terms for inclusion in prompt.
        
        Args:
            glossary: Glossary object
            target_language: Target language code
            
        Returns:
            Formatted glossary string
        """
        if not glossary.mappings:
            return "No glossary terms provided."
        
        glossary_lines = []
        for term, translations in glossary.mappings.items():
            if target_language in translations:
                translation = translations[target_language]
                glossary_lines.append(f"- {term} → {translation}")
        
        if not glossary_lines:
            return f"No glossary terms available for {target_language}."
        
        return "\n".join(glossary_lines)

    def _format_structure_for_prompt(self, structure: StructureInfo) -> str:
        """Format structure information for inclusion in prompt.
        
        Args:
            structure: StructureInfo object with line breaks, indentation, whitespace
            
        Returns:
            Formatted structure information string
        """
        structure_lines = []
        
        # Add line break information
        if structure.line_breaks:
            structure_lines.append(f"Line breaks at lines: {', '.join(map(str, structure.line_breaks[:10]))}")
            if len(structure.line_breaks) > 10:
                structure_lines.append(f"  ... and {len(structure.line_breaks) - 10} more")
        
        # Add indentation information
        if structure.indentation:
            indent_summary = {}
            for line, indent_level in structure.indentation.items():
                indent_summary[indent_level] = indent_summary.get(indent_level, 0) + 1
            
            indent_info = ", ".join([f"{count} lines at indent {level}" for level, count in sorted(indent_summary.items())])
            structure_lines.append(f"Indentation: {indent_info}")
        
        # Add whitespace pattern information
        if structure.whitespace:
            ws_count = len(structure.whitespace)
            structure_lines.append(f"Special whitespace patterns: {ws_count} lines")
        
        if not structure_lines:
            return "No special structure information."
        
        structure_lines.insert(0, "Preserve these structural elements:")
        return "\n".join(structure_lines)

    def _format_segments_for_prompt(self, segments: List[Segment]) -> str:
        """Format segments for inclusion in prompt.
        
        Args:
            segments: List of translatable segments
            
        Returns:
            Formatted segments string
        """
        segment_lines = []
        for i, seg in enumerate(segments, 1):
            segment_lines.append(f"[Segment {i}]")
            segment_lines.append(seg.content)
            segment_lines.append("")  # Blank line between segments
        
        return "\n".join(segment_lines)

    def _parse_translation_response(
        self,
        translated_text: str,
        translatable_segments: List[Segment],
        all_segments: List[Segment]
    ) -> List[Segment]:
        """Parse LLM response and reconstruct segments.
        
        Args:
            translated_text: LLM response with translated text
            translatable_segments: Original translatable segments
            all_segments: All segments (translatable and protected)
            
        Returns:
            List of segments with translations applied
        """
        # Split response by segment markers
        segment_pattern = r'\[Segment \d+\]\s*\n(.*?)(?=\[Segment \d+\]|$)'
        import re
        matches = re.findall(segment_pattern, translated_text, re.DOTALL)
        
        # If parsing fails, try simple split
        if not matches or len(matches) != len(translatable_segments):
            # Fallback: split by double newlines
            parts = translated_text.split('\n\n')
            matches = [p.strip() for p in parts if p.strip()]
        
        # Create mapping of translatable segments to translations
        translation_map = {}
        for i, seg in enumerate(translatable_segments):
            if i < len(matches):
                translation_map[id(seg)] = matches[i].strip()
        
        # Reconstruct all segments with translations
        result_segments = []
        for seg in all_segments:
            if seg.type == SegmentType.TRANSLATABLE and id(seg) in translation_map:
                # Create new segment with translated content
                translated_seg = Segment(
                    type=seg.type,
                    content=translation_map[id(seg)],
                    start_line=seg.start_line,
                    end_line=seg.end_line,
                    metadata=seg.metadata
                )
                result_segments.append(translated_seg)
            else:
                # Keep protected segments unchanged
                result_segments.append(seg)
        
        return result_segments

    def _reconstruct_content(self, segments: List[Segment]) -> str:
        """Reconstruct full content from segments.
        
        Args:
            segments: List of segments
            
        Returns:
            Reconstructed content string
        """
        return "".join(seg.content for seg in segments)

    def _parse_segments(self, segments_data: List[Dict[str, Any]]) -> List[Segment]:
        """Parse segment dictionaries into Segment objects.
        
        Args:
            segments_data: List of segment dictionaries
            
        Returns:
            List of Segment objects
        """
        from ..models.markdown_models import SegmentMetadata
        
        segments = []
        for seg_data in segments_data:
            metadata = None
            if seg_data.get("metadata"):
                metadata = SegmentMetadata(
                    protection_reason=seg_data["metadata"].get("protection_reason"),
                    link_url=seg_data["metadata"].get("link_url"),
                    alt_text=seg_data["metadata"].get("alt_text")
                )
            
            segment = Segment(
                type=SegmentType(seg_data["type"]),
                content=seg_data["content"],
                start_line=seg_data["start_line"],
                end_line=seg_data["end_line"],
                metadata=metadata
            )
            segments.append(segment)
        
        return segments

    def _parse_glossary(self, glossary_data: Dict[str, Any]) -> Glossary:
        """Parse glossary dictionary into Glossary object.
        
        Args:
            glossary_data: Glossary dictionary
            
        Returns:
            Glossary object
        """
        return Glossary(
            format=glossary_data.get("format", "auto-detected"),
            mappings=glossary_data.get("mappings", {})
        )

    def _parse_structure(self, structure_data: Dict[str, Any]) -> StructureInfo:
        """Parse structure dictionary into StructureInfo object.
        
        Args:
            structure_data: Structure dictionary
            
        Returns:
            StructureInfo object
        """
        return StructureInfo(
            line_breaks=structure_data.get("line_breaks", []),
            indentation={
                int(k): v for k, v in structure_data.get("indentation", {}).items()
            },
            whitespace={
                int(k): v for k, v in structure_data.get("whitespace", {}).items()
            }
        )

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
