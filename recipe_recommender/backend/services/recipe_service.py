"""
Recipe Service
=============
Business logic for:
- Searching recipes in DB
- Combining with AI results
- Analytics (popular ingredients, search logs)
"""

from typing import List, Optional
from models.recipe import Recipe
from database import (
    get_db_connection, search_recipes_by_ingredients
)
import json
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class RecipeService:
    def find_matching_recipes(self, ingredients: List[str], cuisine_type: Optional[str]=None, max_cook_time: Optional[int]=None, difficulty: Optional[int]=None, limit: int=10) -> List[dict]:
        """
        Find recipes in DB by ingredient matching and filters.
        """
        matches = search_recipes_by_ingredients(ingredients, limit=limit)
        results = []
        for row in matches:
            # Filter by cuisine_type, cook_time, difficulty
            if cuisine_type and row.get("cuisine_type") != cuisine_type:
                continue
            if max_cook_time and row.get("cook_time_minutes", 99) > max_cook_time:
                continue
            if difficulty and row.get("difficulty_level") != difficulty:
                continue
            results.append(Recipe.from_row(row).to_dict())
        logger.info(f"Found {len(results)} DB recipe matches for {ingredients}")
        return results

    def combine_and_rank_recipes(self, ai_recipes, db_recipes, ingredients: List[str]) -> List[dict]:
        """
        Combine, dedupe, and rank AI and DB recipes by ingredient overlap.
        AI recipes get a boost due to novelty/confidence.
        """
        all_recipes = []
        seen_names = set()
        # DB recipes first
        for r in db_recipes:
            key = (r['name'].strip().lower(), r.get('cuisine_type',''))
            if key in seen_names:
                continue
            r['score'] = self._ingredient_score(r['ingredients'], ingredients)
            seen_names.add(key)
            all_recipes.append(r)
        # AI recipes, adjust scoring
        for r in ai_recipes:
            key = (r['name'].strip().lower(), r.get('cuisine_type',''))
            if key in seen_names:
                continue
            r['score'] = self._ingredient_score(r['ingredients'], ingredients) + 1.5  # boost
            seen_names.add(key)
            all_recipes.append(r)
        # Sort by score, then popularity_score if present
        all_recipes.sort(key=lambda r: (-r['score'], -r.get('popularity_score',0)))
        return all_recipes

    def _ingredient_score(self, recipe_ingredients, input_ingredients):
        """Ingredient overlap score for ranking (simple count overlap)"""
        if isinstance(recipe_ingredients, str):
            try:
                recipe_ingredients = json.loads(recipe_ingredients)
            except Exception:
                recipe_ingredients = [i.strip() for i in recipe_ingredients.split(',') if i.strip()]
        matches = set(map(str.lower, recipe_ingredients)) & set(map(str.lower, input_ingredients))
        return len(matches)

    def log_search(self, ingredients: List[str], result_count: int, cuisine_preference: Optional[str]=None, session_id: Optional[str]=None):
        """
        Log a recipe search for analytics.
        """
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO search_logs (ingredients, results_count, cuisine_preference, session_id) VALUES (?, ?, ?, ?)',
                (json.dumps(ingredients), result_count, cuisine_preference, session_id)
            )

    def get_popular_ingredients(self, limit=20) -> List[str]:
        """
        Analyze logs to return popular search ingredients this month.
        """
        counter = Counter()
        with get_db_connection() as conn:
            logs = conn.execute(
                "SELECT ingredients FROM search_logs WHERE search_timestamp > datetime('now', '-30 days')"
            ).fetchall()
            for row in logs:
                try:
                    ings = json.loads(row['ingredients'])
                    if isinstance(ings, list):
                        counter.update(ing.strip().lower() for ing in ings)
                except Exception:
                    continue
        return [item for item,_ in counter.most_common(limit)]