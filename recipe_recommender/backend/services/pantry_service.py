"""
Pantry Service
=============
Manages user's pantry (ingredients storage)
"""

from typing import List, Optional
from backend.models.pantry import PantryItem
from backend.database import get_db_connection

class PantryService:
    def get_pantry(self, user_id: int) -> List[dict]:
        with get_db_connection() as conn:
            rows = conn.execute('SELECT * FROM pantry_items WHERE user_id = ?', (user_id,)).fetchall()
            return [PantryItem.from_row(dict(row)).to_dict() for row in rows]

    def add_or_update_item(self, user_id: int, ingredient_name: str, quantity: Optional[str]=None, unit: Optional[str]=None, expiry_date: Optional[str]=None) -> dict:
        with get_db_connection() as conn:
            # Insert or update
            conn.execute('''
                INSERT INTO pantry_items (user_id, ingredient_name, quantity, unit, expiry_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, ingredient_name) DO UPDATE SET
                   quantity = excluded.quantity, unit = excluded.unit, expiry_date = excluded.expiry_date, added_at = CURRENT_TIMESTAMP
                ''', (user_id, ingredient_name, quantity, unit, expiry_date))
            row = conn.execute('SELECT * FROM pantry_items WHERE user_id = ? AND ingredient_name = ?', (user_id, ingredient_name)).fetchone()
            return PantryItem.from_row(dict(row)).to_dict() if row else None

    def remove_item(self, user_id: int, ingredient_name: str) -> bool:
        with get_db_connection() as conn:
            conn.execute('DELETE FROM pantry_items WHERE user_id = ? AND ingredient_name = ?', (user_id, ingredient_name))
            return True

    def get_expiring_items(self, user_id: int, days: int = 3) -> List[dict]:
        with get_db_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM pantry_items 
                WHERE user_id = ? AND expiry_date IS NOT NULL AND expiry_date <= date('now', ?)
            ''', (user_id, f'+{days} days')).fetchall()
            return [PantryItem.from_row(dict(row)).to_dict() for row in rows]