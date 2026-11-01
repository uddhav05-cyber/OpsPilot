"""Loads and validates synthetic IT runbooks from JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional


@dataclass
class Runbook:
    """A single IT runbook entry."""

    runbook_id: str
    title: str
    category: str
    content: str
    tags: list[str]

    REQUIRED_FIELDS: ClassVar[list[str]] = [
        "runbook_id",
        "title",
        "category",
        "content",
    ]

    @classmethod
    def from_dict(cls, data: dict) -> Runbook:
        """Create Runbook from dictionary, validating required fields."""
        missing = [field for field in cls.REQUIRED_FIELDS if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        return cls(
            runbook_id=data["runbook_id"],
            title=data["title"],
            category=data["category"],
            content=data["content"],
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "runbook_id": self.runbook_id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "tags": self.tags,
        }


class KnowledgeBase:
    """Container for runbooks with lookup capabilities."""

    def __init__(self, runbooks: list[Runbook]):
        self._runbooks = runbooks
        self._by_id = {rb.runbook_id: rb for rb in runbooks}
        self._by_category: dict[str, list[Runbook]] = {}
        for rb in runbooks:
            self._by_category.setdefault(rb.category, []).append(rb)

    @classmethod
    def from_json_file(cls, path: str | Path) -> KnowledgeBase:
        """Load knowledge base from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON root must be a list of runbooks")

        runbooks = [Runbook.from_dict(item) for item in data]
        return cls(runbooks)

    def __contains__(self, runbook_id: str) -> bool:
        """Check if runbook exists by ID."""
        return runbook_id in self._by_id

    def get(self, runbook_id: str) -> Optional[Runbook]:
        """Get runbook by ID."""
        return self._by_id.get(runbook_id)

    @property
    def by_category(self) -> dict[str, list[Runbook]]:
        """Runbooks grouped by category."""
        return self._by_category

    @property
    def categories(self) -> list[str]:
        """List of all categories."""
        return list(self._by_category.keys())

    @property
    def runbooks(self) -> list[Runbook]:
        """All runbooks."""
        return self._runbooks

    def __len__(self) -> int:
        return len(self._runbooks)

    def __iter__(self):
        return iter(self._runbooks)