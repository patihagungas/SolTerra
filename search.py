"""
search.py - Search & filter helpers for SolTerra Drawing Manager.
Wraps db.DatabaseManager.search() with convenience methods.
"""
from __future__ import annotations
from db import DatabaseManager


class SearchManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def search(
        self,
        query: str = "",
        project_id: int | None = None,
        category_id: int | None = None,
        status: str | None = None,
        file_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        """Return drawings matching all provided criteria."""
        return self.db.search(
            query=query,
            project_id=project_id,
            category_id=category_id,
            status=status,
            file_type=file_type,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
        )

    def get_file_types(self) -> list[str]:
        """Return distinct file types present in the database."""
        rows = self.db.get_all_drawings()
        seen: set[str] = set()
        result: list[str] = []
        for r in rows:
            ft = (r["file_type"] or "").upper()
            if ft and ft not in seen:
                seen.add(ft)
                result.append(ft)
        return sorted(result)
