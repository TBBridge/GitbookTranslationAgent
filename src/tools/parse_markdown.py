"""Tool for parsing Markdown with protected region detection."""

import json
import re
from typing import List, Dict, Any, Tuple, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..models.markdown_models import (
    Segment,
    SegmentType,
    SegmentMetadata,
    StructureInfo,
    ParsedMarkdown
)


class ParseMarkdownInput(BaseModel):
    """Input schema for ParseMarkdownTool."""

    content: str = Field(description="Markdown content to parse")


class ParseMarkdownTool(BaseTool):
    """Tool for parsing Markdown and detecting protected regions."""

    name: str = "parse_markdown"
    description: str = """
    Parses Markdown content and identifies protected regions (code blocks, inline code,
    YAML frontmatter, GitBook tags, HTML tags, links, images).
    Input should be a JSON with: content (markdown string).
    Returns parsed segments with translatable and protected regions, plus structure info.
    """
    args_schema: type[BaseModel] = ParseMarkdownInput

    def _run(self, content: str) -> str:
        """Execute the tool to parse markdown content.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            JSON string containing parsed segments and structure information
        """
        try:
            parsed = self.parse(content)
            
            # Convert to JSON-serializable format
            result_data = {
                "success": True,
                "segments": [
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
                    for seg in parsed.segments
                ],
                "structure": {
                    "line_breaks": parsed.structure.line_breaks,
                    "indentation": {str(k): v for k, v in parsed.structure.indentation.items()},
                    "whitespace": {str(k): v for k, v in parsed.structure.whitespace.items()}
                }
            }
            
            return json.dumps(result_data, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "error": f"Failed to parse markdown: {str(e)}",
                "segments": [],
                "structure": {"line_breaks": [], "indentation": {}, "whitespace": {}}
            })

    def parse(self, content: str) -> ParsedMarkdown:
        """Parse markdown content into segments and structure.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            ParsedMarkdown with segments and structure information
        """
        lines = content.split('\n')
        
        # Capture structure information
        structure = self._capture_structure(lines)
        
        # Detect all protected regions
        protected_regions = self._detect_protected_regions(content, lines)
        
        # Build segments from protected regions
        segments = self._build_segments(content, lines, protected_regions)
        
        return ParsedMarkdown(segments=segments, structure=structure)

    def _capture_structure(self, lines: List[str]) -> StructureInfo:
        """Capture structure information from markdown lines.
        
        Args:
            lines: List of markdown lines
            
        Returns:
            StructureInfo with line breaks, indentation, and whitespace patterns
        """
        structure = StructureInfo()
        
        for line_num, line in enumerate(lines):
            # Record line breaks (empty lines)
            if line.strip() == '':
                structure.line_breaks.append(line_num)
            
            # Record indentation (leading spaces/tabs)
            if line and line[0] in (' ', '\t'):
                indent_match = re.match(r'^([ \t]+)', line)
                if indent_match:
                    structure.indentation[line_num] = len(indent_match.group(1))
            
            # Record whitespace patterns (for lines with mixed whitespace)
            whitespace_match = re.match(r'^([ \t]+)', line)
            if whitespace_match:
                structure.whitespace[line_num] = whitespace_match.group(1)
        
        return structure

    def _detect_protected_regions(
        self,
        content: str,
        lines: List[str]
    ) -> List[Tuple[int, int, str, Optional[Dict[str, str]]]]:
        """Detect all protected regions in markdown.
        
        Args:
            content: Full markdown content
            lines: List of markdown lines
            
        Returns:
            List of tuples: (start_pos, end_pos, protection_reason, metadata)
        """
        protected_regions = []
        
        # Detect YAML frontmatter
        protected_regions.extend(self._detect_yaml_frontmatter(content))
        
        # Detect fenced code blocks
        protected_regions.extend(self._detect_fenced_code_blocks(content))
        
        # Detect GitBook tags
        protected_regions.extend(self._detect_gitbook_tags(content))
        
        # Detect HTML tags
        protected_regions.extend(self._detect_html_tags(content))
        
        # Detect links and images (these need special handling)
        protected_regions.extend(self._detect_links_and_images(content))
        
        # Detect inline code (must be after links to avoid conflicts)
        protected_regions.extend(self._detect_inline_code(content))
        
        # Sort by start position
        protected_regions.sort(key=lambda x: x[0])
        
        # Merge overlapping regions
        protected_regions = self._merge_overlapping_regions(protected_regions)
        
        return protected_regions

    def _detect_yaml_frontmatter(self, content: str) -> List[Tuple[int, int, str, None]]:
        """Detect YAML frontmatter (--- to ---).
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions
        """
        regions = []
        pattern = r'^---\n(.*?)\n---\n'
        
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            regions.append((match.start(), match.end(), 'yaml-frontmatter', None))
        
        return regions

    def _detect_fenced_code_blocks(self, content: str) -> List[Tuple[int, int, str, None]]:
        """Detect fenced code blocks (``` to ```).
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions
        """
        regions = []
        pattern = r'```[^\n]*\n(.*?)\n```'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            regions.append((match.start(), match.end(), 'code-block', None))
        
        return regions

    def _detect_inline_code(self, content: str) -> List[Tuple[int, int, str, None]]:
        """Detect inline code (`...`).
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions
        """
        regions = []
        # Match backticks that are not part of fenced code blocks
        pattern = r'(?<!`)`([^`\n]+?)`(?!`)'
        
        for match in re.finditer(pattern, content):
            regions.append((match.start(), match.end(), 'inline-code', None))
        
        return regions

    def _detect_gitbook_tags(self, content: str) -> List[Tuple[int, int, str, None]]:
        """Detect GitBook tags ({% ... %} and {{ ... }}).
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions
        """
        regions = []
        
        # Detect {% ... %} tags
        pattern1 = r'\{%.*?%\}'
        for match in re.finditer(pattern1, content, re.DOTALL):
            regions.append((match.start(), match.end(), 'gitbook-tag', None))
        
        # Detect {{ ... }} expressions
        pattern2 = r'\{\{.*?\}\}'
        for match in re.finditer(pattern2, content, re.DOTALL):
            regions.append((match.start(), match.end(), 'gitbook-expression', None))
        
        return regions

    def _detect_html_tags(self, content: str) -> List[Tuple[int, int, str, None]]:
        """Detect HTML tags and attributes.
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions
        """
        regions = []
        
        # Detect HTML tags (both opening and closing)
        pattern = r'<[^>]+>'
        
        for match in re.finditer(pattern, content):
            regions.append((match.start(), match.end(), 'html-tag', None))
        
        return regions

    def _detect_links_and_images(
        self,
        content: str
    ) -> List[Tuple[int, int, str, Optional[Dict[str, str]]]]:
        """Detect Markdown links and images, protecting URLs and paths.
        
        Args:
            content: Markdown content
            
        Returns:
            List of protected regions with metadata
        """
        regions = []
        
        # Detect images: ![alt](path)
        image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        for match in re.finditer(image_pattern, content):
            # Protect the entire image syntax
            url_start = match.start(2)
            url_end = match.end(2)
            metadata = {
                'link_url': match.group(2),
                'alt_text': match.group(1)
            }
            regions.append((url_start, url_end, 'image-path', metadata))
        
        # Detect links: [text](URL)
        link_pattern = r'(?<!!)\[([^\]]+)\]\(([^\)]+)\)'
        for match in re.finditer(link_pattern, content):
            # Protect only the URL part
            url_start = match.start(2)
            url_end = match.end(2)
            metadata = {
                'link_url': match.group(2)
            }
            regions.append((url_start, url_end, 'link-url', metadata))
        
        return regions

    def _merge_overlapping_regions(
        self,
        regions: List[Tuple[int, int, str, Optional[Dict[str, str]]]]
    ) -> List[Tuple[int, int, str, Optional[Dict[str, str]]]]:
        """Merge overlapping protected regions.
        
        Args:
            regions: List of protected regions sorted by start position
            
        Returns:
            List of merged regions
        """
        if not regions:
            return []
        
        merged = [regions[0]]
        
        for current in regions[1:]:
            last = merged[-1]
            
            # Check if current overlaps with last
            if current[0] < last[1]:
                # Merge by extending the last region
                merged[-1] = (
                    last[0],
                    max(last[1], current[1]),
                    last[2],  # Keep first protection reason
                    last[3]   # Keep first metadata
                )
            else:
                merged.append(current)
        
        return merged

    def _build_segments(
        self,
        content: str,
        lines: List[str],
        protected_regions: List[Tuple[int, int, str, Optional[Dict[str, str]]]]
    ) -> List[Segment]:
        """Build segments from protected regions.
        
        Args:
            content: Full markdown content
            lines: List of markdown lines
            protected_regions: List of protected regions
            
        Returns:
            List of segments
        """
        segments = []
        current_pos = 0
        
        for start_pos, end_pos, reason, metadata in protected_regions:
            # Add translatable segment before protected region
            if current_pos < start_pos:
                translatable_content = content[current_pos:start_pos]
                if translatable_content:  # Add all segments including whitespace-only
                    start_line = self._get_line_number(content, current_pos)
                    end_line = self._get_line_number(content, start_pos)
                    
                    segments.append(Segment(
                        type=SegmentType.TRANSLATABLE,
                        content=translatable_content,
                        start_line=start_line,
                        end_line=end_line,
                        metadata=None
                    ))
            
            # Add protected segment
            protected_content = content[start_pos:end_pos]
            start_line = self._get_line_number(content, start_pos)
            end_line = self._get_line_number(content, end_pos)
            
            seg_metadata = SegmentMetadata(
                protection_reason=reason,
                link_url=metadata.get('link_url') if metadata else None,
                alt_text=metadata.get('alt_text') if metadata else None
            )
            
            segments.append(Segment(
                type=SegmentType.PROTECTED,
                content=protected_content,
                start_line=start_line,
                end_line=end_line,
                metadata=seg_metadata
            ))
            
            current_pos = end_pos
        
        # Add final translatable segment
        if current_pos < len(content):
            translatable_content = content[current_pos:]
            if translatable_content:  # Add all segments including whitespace-only
                start_line = self._get_line_number(content, current_pos)
                end_line = len(lines) - 1
                
                segments.append(Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=translatable_content,
                    start_line=start_line,
                    end_line=end_line,
                    metadata=None
                ))
        
        return segments

    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for a character position in content.
        
        Args:
            content: Full content string
            position: Character position
            
        Returns:
            Line number (0-indexed)
        """
        return content[:position].count('\n')

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
