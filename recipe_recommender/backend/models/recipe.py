"""
Recipe Model
============
Define Recipe data structure and helpers for serialization and db-row mapping
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json

@dataclass
class Recipe:
    id: Optional[int] = None
    name: str = ""
    ingredients: List[str] = field(default_factory=list)
    instructions: str = ""
    cuisine_type: str = "global"
    difficulty_level: int = 3
    cook_time_minutes: int = 30
    serving_size: int = 4
    calories_per_serving: Optional[int] = None
    dietary_tags: List[str] = field(default_factory=list)
    source: str = "ai_generated"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    popularity_score: float = 0.0
    avg_rating: Optional[float] = None
    rating_count: Optional[int] = None

    @staticmethod
    def from_row(row: Dict[str, Any]) -> "Recipe":
        """
        Create a Recipe instance from a sqlite row (dict)
        """
        return Recipe(
            id=row.get("id"),
            name=row["name"],
            ingredients=json.loads(row["ingredients"]) if row.get("ingredients") else [],
            instructions=row["instructions"],
            cuisine_type=row.get("cuisine_type", "global"),
            difficulty_level=row.get("difficulty_level", 3),
            cook_time_minutes=row.get("cook_time_minutes", 30),
            serving_size=row.get("serving_size", 4),
            calories_per_serving=row.get("calories_per_serving"),
            dietary_tags=json.loads(row["dietary_tags"]) if row.get("dietary_tags") else [],
            source=row.get("source", "ai_generated"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            popularity_score=row.get("popularity_score", 0.0),
            avg_rating=row.get("avg_rating"),
            rating_count=row.get("rating_count")
        )

    def to_dict(self, include_id=True) -> dict:
        data = asdict(self)
        data["ingredients"] = self.ingredients
        data["dietary_tags"] = self.dietary_tags
        if not include_id and "id" in data:
            data.pop("id")
        return data

    @staticmethod
    def from_api_payload(payload: Dict[str, Any]) -> "Recipe":
        return Recipe(
            name=payload["name"],
            ingredients=payload.get("ingredients", []),
            instructions=payload.get("instructions", ""),
            cuisine_type=payload.get("cuisine_type", "global"),
            difficulty_level=payload.get("difficulty_level", 3),
            cook_time_minutes=payload.get("cook_time_minutes", 30),
            serving_size=payload.get("serving_size", 4),
            calories_per_serving=payload.get("calories_per_serving"),
            dietary_tags=payload.get("dietary_tags", []),
            source=payload.get("source", "user_submitted")
        )