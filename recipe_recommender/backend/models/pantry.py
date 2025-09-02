"""
PantryItem Model
================
Represents a user's saved pantry ingredient with metadata.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class PantryItem:
    id: Optional[int] = None
    user_id: int = 0
    ingredient_name: str = ""
    quantity: Optional[str] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    added_at: Optional[str] = None

    @staticmethod
    def from_row(row: Dict[str, Any]) -> "PantryItem":
        return PantryItem(
            id=row.get("id"),
            user_id=row.get("user_id", 0),
            ingredient_name=row["ingredient_name"],
            quantity=row.get("quantity"),
            unit=row.get("unit"),
            expiry_date=row.get("expiry_date"),
            added_at=row.get("added_at")
        )

    def to_dict(self) -> dict:
        return asdict(self)