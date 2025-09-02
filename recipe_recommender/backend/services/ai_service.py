#!/usr/bin/env python3
"""
AI Recipe Service using Gemini API
==================================
Intelligent recipe generation with cultural awareness and dietary considerations.

Features:
- Gemini API integration with optimized prompts
- Rate limiting and error handling
- Cultural recipe suggestions (Sudanese focus)
- Dietary restriction handling
- Cost-effective API usage
"""

import json
import logging
import time
from typing import List, Dict, Optional, Any
import re
from dataclasses import dataclass
import google.generativeai as genai
import os
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class RecipeSuggestion:
    """Data class for structured recipe suggestions"""
    name: str
    ingredients: List[str]
    instructions: str
    cuisine_type: str = "global"
    difficulty: int = 3
    cook_time: int = 30
    servings: int = 4
    dietary_tags: List[str] = None
    confidence_score: float = 0.8

class RateLimiter:
    """Simple rate limiter for Gemini API calls"""
    
    def __init__(self, max_calls_per_minute=20):
        self.max_calls = max_calls_per_minute
        self.calls = []
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.max_calls:
            sleep_time = 60 - (now - self.calls[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.calls.append(now)

def retry_on_failure(max_retries=3, delay=1):
    """Decorator for retrying failed API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class AIRecipeService:
    """
    AI-powered recipe recommendation service using Gemini API
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash"):
        """
        Initialize AI service with Gemini configuration
        Args:
            api_key (str): Gemini API key (optional, will use env if not provided)
            model (str): Gemini model to use (default: gemini-2.0-flash)
        """
        # Fetch Gemini API key from env if not provided
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Valid Gemini API key required. Set GEMINI_API_KEY in your environment.")
        genai.configure(api_key=self.api_key)
        self.model = model
        self.rate_limiter = RateLimiter(max_calls_per_minute=15)  # Conservative limit

        # Cache for repeated queries (simple in-memory cache)
        self._cache = {}
        self._cache_max_size = 100

        logger.info(f"AI Recipe Service initialized with Gemini model: {model}")
    
    def _generate_cache_key(self, ingredients: List[str], cuisine: str, dietary: List[str]) -> str:
        """Generate cache key for request deduplication"""
        key_data = f"{sorted(ingredients)}_{cuisine}_{sorted(dietary or [])}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[RecipeSuggestion]]:
        """Get cached result if available"""
        return self._cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, result: List[RecipeSuggestion]):
        """Cache result with size management"""
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = result
    
    def _create_recipe_prompt(self, ingredients: List[str], cuisine_preference: str, 
                             dietary_restrictions: List[str], difficulty: int) -> str:
        """
        Create optimized prompt for recipe generation
        
        Args:
            ingredients: Available ingredients
            cuisine_preference: Preferred cuisine type
            dietary_restrictions: List of dietary restrictions
            difficulty: Cooking difficulty level (1-5)
            
        Returns:
            str: Formatted prompt for Gemini
        """
        # Build dietary restrictions string
        dietary_text = ""
        if dietary_restrictions:
            dietary_text = f" The recipes must be {', '.join(dietary_restrictions)}."
        
        # Adjust complexity based on difficulty
        complexity_guide = {
            1: "very simple with minimal cooking steps",
            2: "simple with basic cooking techniques", 
            3: "moderate complexity with standard techniques",
            4: "advanced with multiple techniques",
            5: "expert level with complex techniques"
        }
        
        complexity = complexity_guide.get(difficulty, "moderate complexity")
        
        # Special handling for Sudanese cuisine
        cultural_context = ""
        if cuisine_preference == "sudanese":
            cultural_context = """
Focus on authentic Sudanese cuisine with traditional ingredients and cooking methods.
Include cultural context and traditional serving suggestions. Consider ingredients
like sorghum, fava beans, peanuts, sesame, tamarind, and traditional spices like
cardamom, cinnamon, and coriander. Mention traditional accompaniments.
"""
        elif cuisine_preference != "any":
            cultural_context = f"Focus on authentic {cuisine_preference} cuisine with traditional flavors and techniques."
        
        prompt = f"""You are an expert chef specializing in creating recipes from available ingredients.

INGREDIENTS AVAILABLE: {', '.join(ingredients)}

REQUIREMENTS:
- Create 3 unique, practical recipes using primarily these ingredients
- Recipes should be {complexity}
- {cuisine_preference.title()} cuisine preference{dietary_text}
- Include cooking time and serving size
- Provide clear, step-by-step instructions

{cultural_context}

RESPONSE FORMAT (JSON only):
{{
  "recipes": [
    {{
      "name": "Recipe Name",
      "ingredients": ["ingredient1", "ingredient2", ...],
      "instructions": "Step-by-step cooking instructions",
      "cuisine_type": "{cuisine_preference}",
      "difficulty": {difficulty},
      "cook_time_minutes": 30,
      "servings": 4,
      "dietary_tags": ["tag1", "tag2"],
      "tips": "Optional cooking tips or cultural notes"
    }}
  ]
}}

Important: Respond with valid JSON only. No additional text or formatting."""
        
        return prompt
    
    @retry_on_failure(max_retries=2, delay=2)
    def _call_gemini_api(self, prompt: str) -> str:
        """
        Make rate-limited call to Gemini API with error handling
        Args:
            prompt (str): Recipe generation prompt
        Returns:
            str: Gemini model text response
        Raises:
            Exception: If API call fails after retries
        """
        self.rate_limiter.wait_if_needed()
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            if hasattr(response, 'text'):
                return response.text
            elif response.parts:
                return ''.join([str(part.text) for part in response.parts if hasattr(part, 'text')])
            else:
                raise ValueError("No valid response from Gemini API.")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise
    
    def _parse_ai_response(self, response_text: str) -> List[RecipeSuggestion]:
        """
        Parse and validate Gemini response into structured format
        
        Args:
            response_text (str): Raw response from Gemini
            
        Returns:
            List[RecipeSuggestion]: Parsed recipe suggestions
        """
        try:
            # Clean response text (remove any non-JSON content)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group()
            
            data = json.loads(response_text)
            recipes_data = data.get('recipes', [])
            
            suggestions = []
            for recipe_data in recipes_data:
                try:
                    # Validate required fields
                    if not all(key in recipe_data for key in ['name', 'ingredients', 'instructions']):
                        logger.warning(f"Skipping incomplete recipe: {recipe_data.get('name', 'Unknown')}")
                        continue
                    
                    suggestion = RecipeSuggestion(
                        name=recipe_data['name'].strip(),
                        ingredients=[ing.strip().lower() for ing in recipe_data['ingredients']],
                        instructions=recipe_data['instructions'].strip(),
                        cuisine_type=recipe_data.get('cuisine_type', 'global'),
                        difficulty=max(1, min(5, recipe_data.get('difficulty', 3))),  # Clamp to 1-5
                        cook_time=max(5, recipe_data.get('cook_time_minutes', 30)),  # Minimum 5 minutes
                        servings=max(1, recipe_data.get('servings', 4)),  # Minimum 1 serving
                        dietary_tags=recipe_data.get('dietary_tags', []),
                        confidence_score=0.8  # AI-generated recipes get 0.8 confidence
                    )
                    
                    suggestions.append(suggestion)
                    
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error parsing recipe {recipe_data.get('name', 'Unknown')}: {e}")
                    continue
            
            if not suggestions:
                logger.warning("No valid recipes parsed from AI response")
            
            return suggestions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            return []
        
        except Exception as e:
            logger.error(f"Unexpected error parsing AI response: {e}")
            return []
    
    def get_recipe_suggestions(self, ingredients: List[str], 
                             cuisine_preference: str = "any",
                             dietary_restrictions: List[str] = None,
                             difficulty: int = 3) -> List[Dict[str, Any]]:
        """
        Get AI-powered recipe suggestions based on ingredients and preferences
        
        Args:
            ingredients: List of available ingredients
            cuisine_preference: Preferred cuisine type
            dietary_restrictions: List of dietary restrictions
            difficulty: Cooking difficulty level (1-5)
            
        Returns:
            List[Dict]: Recipe suggestions in dictionary format
        """
        if not ingredients:
            logger.warning("No ingredients provided for recipe suggestions")
            return []
        
        # Validate and clean inputs
        ingredients = [ing.strip().lower() for ing in ingredients if ing.strip()]
        dietary_restrictions = dietary_restrictions or []
        
        if not ingredients:
            return []
        
        # Check cache first
        cache_key = self._generate_cache_key(ingredients, cuisine_preference, dietary_restrictions)
        cached_result = self._get_cached_result(cache_key)
        
        if cached_result:
            logger.info(f"Returning cached AI recipe suggestions for ingredients: {ingredients}")
            return [self._suggestion_to_dict(suggestion) for suggestion in cached_result]
        
        try:
            # Generate prompt and call Gemini
            prompt = self._create_recipe_prompt(ingredients, cuisine_preference, dietary_restrictions, difficulty)
            
            logger.info(f"Requesting AI recipe suggestions for: {ingredients}")
            response_text = self._call_gemini_api(prompt)

            # Parse response
            suggestions = self._parse_ai_response(response_text)

            # Cache successful results
            if suggestions:
                self._cache_result(cache_key, suggestions)
                logger.info(f"Generated {len(suggestions)} AI recipe suggestions")
            else:
                logger.warning("No valid suggestions generated by AI")
            
            return [self._suggestion_to_dict(suggestion) for suggestion in suggestions]
            
        except Exception as e:
            logger.error(f"Failed to get AI recipe suggestions: {e}")
            # Return fallback suggestions for common ingredients
            return self._get_fallback_suggestions(ingredients, cuisine_preference)
    
    def _suggestion_to_dict(self, suggestion: RecipeSuggestion) -> Dict[str, Any]:
        """Convert RecipeSuggestion to dictionary format"""
        return {
            'name': suggestion.name,
            'ingredients': suggestion.ingredients,
            'instructions': suggestion.instructions,
            'cuisine_type': suggestion.cuisine_type,
            'difficulty_level': suggestion.difficulty,
            'cook_time_minutes': suggestion.cook_time,
            'serving_size': suggestion.servings,
            'dietary_tags': json.dumps(suggestion.dietary_tags),
            'source': 'ai_generated',
            'confidence_score': suggestion.confidence_score
        }
    
    def _get_fallback_suggestions(self, ingredients: List[str], cuisine: str) -> List[Dict[str, Any]]:
        """
        Provide fallback recipe suggestions when AI fails
        
        Args:
            ingredients: Available ingredients
            cuisine: Cuisine preference
            
        Returns:
            List[Dict]: Fallback recipe suggestions
        """
        logger.info("Generating fallback recipe suggestions")
        
        fallback_recipes = []
        
        # Common ingredient combinations for fallback recipes
        if any(protein in ingredients for protein in ['chicken', 'beef', 'lamb', 'fish']):
            proteins = [ing for ing in ingredients if ing in ['chicken', 'beef', 'lamb', 'fish']]
            vegetables = [ing for ing in ingredients if ing in ['onions', 'tomatoes', 'carrots', 'potatoes']]
            
            if proteins and vegetables:
                fallback_recipes.append({
                    'name': f'{proteins[0].title()} and Vegetable Stir-fry',
                    'ingredients': proteins + vegetables + ['oil', 'salt', 'pepper'],
                    'instructions': f'1. Cut {proteins[0]} and vegetables into bite-sized pieces. 2. Heat oil in a large pan. 3. Cook {proteins[0]} until browned. 4. Add vegetables and stir-fry until tender. 5. Season with salt and pepper. 6. Serve hot.',
                    'cuisine_type': 'global',
                    'difficulty_level': 2,
                    'cook_time_minutes': 25,
                    'serving_size': 4,
                    'dietary_tags': '["quick", "one-pan"]',
                    'source': 'fallback',
                    'confidence_score': 0.6
                })
        
        # Vegetarian fallback
        vegetables = [ing for ing in ingredients if ing in ['tomatoes', 'onions', 'carrots', 'potatoes', 'spinach', 'mushrooms']]
        if len(vegetables) >= 2:
            fallback_recipes.append({
                'name': 'Mixed Vegetable Curry',
                'ingredients': vegetables + ['oil', 'cumin', 'turmeric', 'salt'],
                'instructions': '1. Heat oil in a pot. 2. Add cumin and let it splutter. 3. Add chopped vegetables. 4. Add turmeric and salt. 5. Cover and cook until vegetables are tender. 6. Serve with rice or bread.',
                'cuisine_type': cuisine if cuisine in ['sudanese', 'indian'] else 'global',
                'difficulty_level': 2,
                'cook_time_minutes': 30,
                'serving_size': 4,
                'dietary_tags': '["vegetarian", "vegan"]',
                'source': 'fallback',
                'confidence_score': 0.6
            })
        
        # Sudanese-inspired fallback
        if cuisine == 'sudanese' and any(ing in ingredients for ing in ['beans', 'lentils', 'fava beans']):
            fallback_recipes.append({
                'name': 'Simple Sudanese Bean Stew',
                'ingredients': ['beans', 'onions', 'tomatoes', 'oil', 'cumin', 'salt'],
                'instructions': '1. Soak beans overnight if dried. 2. Cook beans until tender. 3. In another pot, fry onions in oil. 4. Add tomatoes and cook until soft. 5. Add cooked beans, cumin, and salt. 6. Simmer for 15 minutes. 7. Serve with bread.',
                'cuisine_type': 'sudanese',
                'difficulty_level': 2,
                'cook_time_minutes': 45,
                'serving_size': 6,
                'dietary_tags': '["vegetarian", "high-protein", "traditional"]',
                'source': 'fallback',
                'confidence_score': 0.7
            })
        
        return fallback_recipes[:2]  # Return up to 2 fallback recipes
    
    def get_ingredient_substitutions(self, ingredient: str, cuisine_type: str = "global") -> List[str]:
        """
        Get ingredient substitutions using AI
        
        Args:
            ingredient: Ingredient to find substitutions for
            cuisine_type: Cuisine context for substitutions
            
        Returns:
            List[str]: Suggested substitutions
        """
        try:
            prompt = f"""Suggest 3-5 common substitutions for "{ingredient}" in {cuisine_type} cooking.
            
Consider:
- Similar flavor profile
- Similar cooking properties  
- Common availability
- Cultural appropriateness for {cuisine_type} cuisine

Respond with JSON only:
{{"substitutions": ["substitute1", "substitute2", ...]}}"""

            response_text = self._call_gemini_api(prompt)
            result = json.loads(response_text)
            return result.get('substitutions', [])
            
        except Exception as e:
            logger.error(f"Failed to get ingredient substitutions: {e}")
            
            # Fallback substitutions
            common_substitutions = {
                'chicken': ['turkey', 'tofu', 'tempeh', 'mushrooms'],
                'beef': ['lamb', 'pork', 'lentils', 'mushrooms'],
                'butter': ['oil', 'margarine', 'coconut oil', 'ghee'],
                'milk': ['coconut milk', 'almond milk', 'soy milk', 'water'],
                'eggs': ['flax eggs', 'chia eggs', 'applesauce', 'banana'],
                'flour': ['rice flour', 'almond flour', 'coconut flour', 'oat flour']
            }
            return common_substitutions.get(ingredient.lower(), [])

# Export the main service class
__all__ = ['AIRecipeService', 'RecipeSuggestion']