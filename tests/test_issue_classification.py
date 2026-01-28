"""Test issue classification logic in ReviewTranslationTool."""

import pytest
from src.tools.review_translation import ReviewTranslationTool


@pytest.fixture
def review_tool():
    """Create a ReviewTranslationTool instance."""
    return ReviewTranslationTool()


class TestIssueClassification:
    """Test the _classify_issue_severity method."""

    def test_classify_structural_damage_as_blocker(self, review_tool):
        """Test that structural damage is classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="The table structure is broken and columns are misaligned"
        )
        assert severity == "BLOCKER"

    def test_classify_code_block_damage_as_blocker(self, review_tool):
        """Test that code block damage is classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="Code block formatting is damaged, missing backticks"
        )
        assert severity == "BLOCKER"

    def test_classify_link_corruption_as_blocker(self, review_tool):
        """Test that link corruption is classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="links",
            description="Link URL was modified from original"
        )
        assert severity == "BLOCKER"

    def test_classify_broken_link_as_blocker(self, review_tool):
        """Test that broken links are classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="links",
            description="The anchor reference is broken"
        )
        assert severity == "BLOCKER"

    def test_classify_missing_content_as_blocker(self, review_tool):
        """Test that missing content is classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="completeness",
            description="Several lines are missing from the translation"
        )
        assert severity == "BLOCKER"

    def test_classify_code_modification_as_blocker(self, review_tool):
        """Test that code modification is classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="Inline code was modified during translation"
        )
        assert severity == "BLOCKER"

    def test_classify_protected_region_change_as_blocker(self, review_tool):
        """Test that protected region changes are classified as BLOCKER (Requirement 11.2)."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="Protected region content was altered"
        )
        assert severity == "BLOCKER"

    def test_classify_glossary_violation_as_major(self, review_tool):
        """Test that glossary violations are classified as MAJOR (Requirement 11.3)."""
        severity = review_tool._classify_issue_severity(
            category="terminology",
            description="Glossary term not used correctly"
        )
        assert severity == "MAJOR"

    def test_classify_terminology_issue_as_major(self, review_tool):
        """Test that terminology issues are classified as MAJOR (Requirement 11.3)."""
        severity = review_tool._classify_issue_severity(
            category="terminology",
            description="Inconsistent terminology usage"
        )
        assert severity == "MAJOR"

    def test_classify_semantic_error_as_major(self, review_tool):
        """Test that semantic errors are classified as MAJOR (Requirement 11.3)."""
        severity = review_tool._classify_issue_severity(
            category="completeness",
            description="Semantic error in translation, meaning is incorrect"
        )
        assert severity == "MAJOR"

    def test_classify_untranslated_text_as_major(self, review_tool):
        """Test that untranslated text is classified as MAJOR (Requirement 11.3)."""
        severity = review_tool._classify_issue_severity(
            category="completeness",
            description="Untranslated Japanese text found in paragraph"
        )
        assert severity == "MAJOR"

    def test_classify_mistranslation_as_major(self, review_tool):
        """Test that mistranslations are classified as MAJOR (Requirement 11.3)."""
        severity = review_tool._classify_issue_severity(
            category="style",
            description="Mistranslation detected, incorrect meaning"
        )
        assert severity == "MAJOR"

    def test_classify_style_improvement_as_minor(self, review_tool):
        """Test that stylistic improvements are classified as MINOR (Requirement 11.4)."""
        severity = review_tool._classify_issue_severity(
            category="style",
            description="Consider using more formal language"
        )
        assert severity == "MINOR"

    def test_classify_phrasing_suggestion_as_minor(self, review_tool):
        """Test that phrasing suggestions are classified as MINOR (Requirement 11.4)."""
        severity = review_tool._classify_issue_severity(
            category="style",
            description="This phrasing could be more natural"
        )
        assert severity == "MINOR"

    def test_classify_formatting_preference_as_minor(self, review_tool):
        """Test that formatting preferences are classified as MINOR (Requirement 11.4)."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="Consider adding more spacing for readability"
        )
        assert severity == "MINOR"

    def test_classify_yaml_frontmatter_damage_as_blocker(self, review_tool):
        """Test that YAML frontmatter damage is classified as BLOCKER."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="YAML frontmatter structure is corrupted"
        )
        assert severity == "BLOCKER"

    def test_classify_markdown_syntax_error_as_blocker(self, review_tool):
        """Test that Markdown syntax errors are classified as BLOCKER."""
        severity = review_tool._classify_issue_severity(
            category="format",
            description="Markdown syntax error makes document invalid"
        )
        assert severity == "BLOCKER"

    def test_classify_relative_path_change_as_blocker(self, review_tool):
        """Test that relative path changes are classified as BLOCKER."""
        severity = review_tool._classify_issue_severity(
            category="links",
            description="Relative path reference was changed"
        )
        assert severity == "BLOCKER"

    def test_classify_incomplete_translation_as_blocker(self, review_tool):
        """Test that incomplete translations are classified as BLOCKER."""
        severity = review_tool._classify_issue_severity(
            category="completeness",
            description="Translation is incomplete, content is truncated"
        )
        assert severity == "BLOCKER"

    def test_classify_inconsistent_glossary_as_major(self, review_tool):
        """Test that inconsistent glossary usage is classified as MAJOR."""
        severity = review_tool._classify_issue_severity(
            category="terminology",
            description="Term should use glossary definition consistently"
        )
        assert severity == "MAJOR"

    def test_classify_inaccurate_translation_as_major(self, review_tool):
        """Test that inaccurate translations are classified as MAJOR."""
        severity = review_tool._classify_issue_severity(
            category="completeness",
            description="Translation is inaccurate and doesn't match original meaning"
        )
        assert severity == "MAJOR"
