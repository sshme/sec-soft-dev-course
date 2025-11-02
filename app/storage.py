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
                "owner_id": "demo-user",
                "created_at": datetime(2024, 1, 15, 10, 30, 0),
                "updated_at": datetime(2024, 1, 15, 10, 30, 0),
            },
            2: {
                "id": 2,
                "text": "In the middle of difficulty lies opportunity.",
                "source": "Albert Einstein",
                "tags": ["opportunity", "challenges", "philosophy", "einstein"],
                "owner_id": "demo-user",
                "created_at": datetime(2024, 1, 20, 14, 15, 0),
                "updated_at": datetime(2024, 1, 20, 14, 15, 0),
            },
        }
        self._next_id = 3

    def get_all(self, owner_id: Optional[str] = None) -> List[dict]:
        if owner_id is None:
            return list(self._highlights.values())
        return [h for h in self._highlights.values() if h.get("owner_id") == owner_id]

    def get_by_id(
        self, highlight_id: int, owner_id: Optional[str] = None
    ) -> Optional[dict]:
        highlight = self._highlights.get(highlight_id)
        if highlight and owner_id is not None:
            if highlight.get("owner_id") != owner_id:
                return None
        return highlight

    def get_by_tag(self, tag: str, owner_id: Optional[str] = None) -> List[dict]:
        tag_lower = tag.lower()
        results = [h for h in self._highlights.values() if tag_lower in h["tags"]]
        if owner_id is not None:
            results = [h for h in results if h.get("owner_id") == owner_id]
        return results

    def create(self, text: str, source: str, tags: List[str], owner_id: str) -> dict:
        now = datetime.now()
        new_highlight = {
            "id": self._next_id,
            "text": text,
            "source": source,
            "tags": tags,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        self._highlights[self._next_id] = new_highlight
        self._next_id += 1
        return new_highlight

    def update(
        self, highlight_id: int, update_data: dict, owner_id: Optional[str] = None
    ) -> Optional[dict]:
        if highlight_id not in self._highlights:
            return None

        highlight = self._highlights[highlight_id]
        if owner_id is not None and highlight.get("owner_id") != owner_id:
            return None

        if update_data:
            highlight.update(update_data)
            highlight["updated_at"] = datetime.now()
        return highlight

    def delete(
        self, highlight_id: int, owner_id: Optional[str] = None
    ) -> Optional[dict]:
        highlight = self._highlights.get(highlight_id)
        if highlight and owner_id is not None:
            if highlight.get("owner_id") != owner_id:
                return None
        return self._highlights.pop(highlight_id, None)

    def exists(self, highlight_id: int) -> bool:
        return highlight_id in self._highlights


storage = HighlightStorage()
