"""
User Model
==========
Represents a user/session for pantry and search logs.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json

@dataclass
class User:
    id: Optional[int] = None
    session_id: str = ""
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    preferences: Optional[dict] = None

    @staticmethod
    def from_row(row: Dict[str, Any]) -> "User":
        return User(
            id=row.get("id"),
            session_id=row["session_id"],
            created_at=row.get("created_at"),
            last_active=row.get("last_active"),
            preferences=json.loads(row["preferences"]) if row.get("preferences") else None
        )
    def to_dict(self) -> dict:
        data = asdict(self)
        if self.preferences is not None and isinstance(self.preferences, dict):
            data["preferences"] = self.preferences
        return data