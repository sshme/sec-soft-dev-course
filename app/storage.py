from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class HighlightStorage:
    """In-memory storage for highlights"""

    _highlights: Dict[int, dict] = field(default_factory=dict)
    _next_id: int = 1

    def __post_init__(self):
        self.reset_to_default()

    def reset_to_default(self) -> None:
        self._highlights = {
            1: {
                "id": 1,
                "text": (
                    "The only way to do great work is to love what you do. "
                    "If you haven't found it yet, keep looking. Don't settle."
                ),
                "source": "Steve Jobs - Stanford Commencement Address 2005",
                "tags": ["motivation", "career", "passion", "steve-jobs"],
                "created_at": datetime(2024, 1, 15, 10, 30, 0),
                "updated_at": datetime(2024, 1, 15, 10, 30, 0),
            },
            2: {
                "id": 2,
                "text": "In the middle of difficulty lies opportunity.",
                "source": "Albert Einstein",
                "tags": ["opportunity", "challenges", "philosophy", "einstein"],
                "created_at": datetime(2024, 1, 20, 14, 15, 0),
                "updated_at": datetime(2024, 1, 20, 14, 15, 0),
            },
        }
        self._next_id = 3

    def get_all(self) -> List[dict]:
        return list(self._highlights.values())

    def get_by_id(self, highlight_id: int) -> Optional[dict]:
        return self._highlights.get(highlight_id)

    def get_by_tag(self, tag: str) -> List[dict]:
        tag_lower = tag.lower()
        return [h for h in self._highlights.values() if tag_lower in h["tags"]]

    def create(self, text: str, source: str, tags: List[str]) -> dict:
        now = datetime.now()
        new_highlight = {
            "id": self._next_id,
            "text": text,
            "source": source,
            "tags": tags,
            "created_at": now,
            "updated_at": now,
        }
        self._highlights[self._next_id] = new_highlight
        self._next_id += 1
        return new_highlight

    def update(self, highlight_id: int, update_data: dict) -> Optional[dict]:
        if highlight_id not in self._highlights:
            return None

        highlight = self._highlights[highlight_id]
        if update_data:
            highlight.update(update_data)
            highlight["updated_at"] = datetime.now()
        return highlight

    def delete(self, highlight_id: int) -> Optional[dict]:
        return self._highlights.pop(highlight_id, None)

    def exists(self, highlight_id: int) -> bool:
        return highlight_id in self._highlights


storage = HighlightStorage()
