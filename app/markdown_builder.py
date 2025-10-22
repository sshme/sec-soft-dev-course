from datetime import datetime
from typing import List, Optional


class MarkdownBuilder:
    """Builder pattern for generating Markdown content from highlights"""

    def __init__(self):
        self._content: List[str] = []
        self._highlights_count: int = 0

    def add_title(self, title: str) -> "MarkdownBuilder":
        self._content.append(f"# {title}")
        self._content.append("")
        return self

    def add_subtitle(self, subtitle: str) -> "MarkdownBuilder":
        self._content.append(f"## {subtitle}")
        self._content.append("")
        return self

    def add_highlight(
        self, text: str, source: str, tags: List[str], created_at: datetime
    ) -> "MarkdownBuilder":
        self._content.append(f"## {source}")
        self._content.append("")

        self._content.append(f"> {text}")
        self._content.append("")

        if tags:
            tags_formatted = ", ".join([f"#{tag}" for tag in tags])
            self._content.append(f"**Tags:** {tags_formatted}")
            self._content.append("")

        timestamp = created_at.strftime("%Y-%m-%d %H:%M")
        self._content.append(f"*Added: {timestamp}*")
        self._content.append("")

        self._content.append("---")
        self._content.append("")

        self._highlights_count += 1
        return self

    def add_metadata(self, key: str, value: str) -> "MarkdownBuilder":
        self._content.append(f"**{key}:** {value}")
        self._content.append("")
        return self

    def add_line_break(self) -> "MarkdownBuilder":
        self._content.append("")
        return self

    def add_horizontal_rule(self) -> "MarkdownBuilder":
        self._content.append("---")
        self._content.append("")
        return self

    def add_raw_text(self, text: str) -> "MarkdownBuilder":
        self._content.append(text)
        return self

    def build(self) -> str:
        return "\n".join(self._content)

    def get_highlights_count(self) -> int:
        return self._highlights_count

    def reset(self) -> "MarkdownBuilder":
        self._content = []
        self._highlights_count = 0
        return self


class HighlightsMarkdownExporter:
    @staticmethod
    def export(
        highlights: List[dict], filter_tag: Optional[str] = None
    ) -> tuple[str, int]:
        """
        Export highlights to Markdown format

        Args:
            highlights: List of highlight dictionaries
            filter_tag: Optional tag for filtering (for display purposes)

        Returns:
            Tuple of (markdown_content, total_highlights)
        """
        builder = MarkdownBuilder()

        builder.add_title("Reading Highlights")

        if filter_tag:
            builder.add_metadata("Filtered by tag", f"#{filter_tag}")
            builder.add_line_break()

        sorted_highlights = sorted(highlights, key=lambda x: x["created_at"])

        for highlight in sorted_highlights:
            builder.add_highlight(
                text=highlight["text"],
                source=highlight["source"],
                tags=highlight["tags"],
                created_at=highlight["created_at"],
            )

        if not sorted_highlights:
            builder.add_raw_text("*No highlights found.*")

        return builder.build(), builder.get_highlights_count()
