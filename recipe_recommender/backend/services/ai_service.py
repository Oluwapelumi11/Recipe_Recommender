#!/usr/bin/env python3
"""
AI Recipe Service using OpenAI API
==================================
Intelligent recipe generation with cultural awareness and dietary considerations.

Features:
- OpenAI GPT integration with optimized prompts
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
import openai
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
    """Simple rate limiter for OpenAI API calls"""
    
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
    AI-powered recipe recommendation service using OpenAI API
    """
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize AI service with OpenAI configuration
        
        Args:
            api_key (str): OpenAI API key
            model (str): OpenAI model to use
        """
        if not api_key or not api_key.startswith('sk-'):
            raise ValueError("Valid OpenAI API key required")
            
        openai.api_key = api_key
        self.model = model
        self.rate_limiter = RateLimiter(max_calls_per_minute=15)  # Conservative limit
        
        # Cache for repeated queries (simple in-memory cache)
        self._cache = {}
        self._cache_max_size = 100
        
        logger.info(f"AI Recipe Service initialized with model: {model}")
    
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
            str: Formatted prompt for OpenAI
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
    def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """
        Make rate-limited call to OpenAI API with error handling
        
        Args:
            prompt (str): Recipe generation prompt
            
        Returns:
            Dict: OpenAI API response
            
        Raises:
            Exception: If API call fails after retries
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional chef and recipe expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,  # Limit tokens to control costs
                temperature=0.7,  # Balance creativity and consistency
                timeout=30  # 30 second timeout
            )
            
            return response
            
        except openai.error.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            time.sleep(60)  # Wait 1 minute for rate limit reset
            raise
            
        except openai.error.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise ValueError("Invalid OpenAI API key")
            
        except openai.error.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            raise
    
    def _parse_ai_response(self, response_text: str) -> List[RecipeSuggestion]:
        """
        Parse and validate OpenAI response into structured format
        
        Args:
            response_text (str): Raw response from OpenAI
            
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
            # Generate prompt and call OpenAI
            prompt = self._create_recipe_prompt(ingredients, cuisine_preference, dietary_restrictions, difficulty)
            
            logger.info(f"Requesting AI recipe suggestions for: {ingredients}")
            response = self._call_openai_api(prompt)
            
            # Parse response
            suggestions = self._parse_ai_response(response.choices[0].message.content)
            
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

            response = self._call_openai_api(prompt)
            result = json.loads(response.choices[0].message.content)
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
    
    def analyze_recipe_complexity(self, ingredients: List[str], instructions: str) -> Dict[str, Any]:
        """
        Analyze recipe complexity and provide insights
        
        Args:
            ingredients: Recipe ingredients
            instructions: Cooking instructions
            
        Returns:
            Dict: Complexity analysis with recommendations
        """
        # Simple complexity analysis based on ingredients and instruction length
        ingredient_count = len(ingredients)
        instruction_length = len(instructions.split('.'))
        
        # Calculate complexity score
        complexity_score = 1
        if ingredient_count > 10:
            complexity_score += 1
        if instruction_length > 8:
            complexity_score += 1
        if any(word in instructions.lower() for word in ['marinate', 'ferment', 'overnight', 'hours']):
            complexity_score += 1
        if any(word in instructions.lower() for word in ['blend', 'whisk', 'fold', 'knead']):
            complexity_score += 1
        
        complexity_score = min(complexity_score, 5)
        
        complexity_labels = {
            1: 'Very Easy',
            2: 'Easy', 
            3: 'Medium',
            4: 'Hard',
            5: 'Very Hard'
        }
        
        return {
            'complexity_score': complexity_score,
            'complexity_label': complexity_labels[complexity_score],
            'ingredient_count': ingredient_count,
            'estimated_steps': instruction_length,
            'time_intensive': 'hours' in instructions.lower() or 'overnight' in instructions.lower(),
            'special_techniques': bool(re.search(r'\b(marinate|ferment|fold|knead|whisk)\b', instructions.lower()))
        }
    
    def get_cooking_tips(self, recipe_name: str, cuisine_type: str) -> List[str]:
        """
        Get AI-generated cooking tips for a specific recipe
        
        Args:
            recipe_name: Name of the recipe
            cuisine_type: Type of cuisine
            
        Returns:
            List[str]: Cooking tips and suggestions
        """
        try:
            prompt = f"""Provide 3-4 practical cooking tips for making "{recipe_name}" ({cuisine_type} cuisine).
            
Focus on:
- Key techniques for best results
- Common mistakes to avoid
- Ingredient preparation tips
- Serving suggestions

Respond with JSON only:
{{"tips": ["tip1", "tip2", "tip3", ...]}}"""

            response = self._call_openai_api(prompt)
            result = json.loads(response.choices[0].message.content)
            return result.get('tips', [])
            
        except Exception as e:
            logger.error(f"Failed to get cooking tips: {e}")
            return [
                "Read through the entire recipe before starting",
                "Prepare all ingredients before you start cooking",
                "Taste and adjust seasoning as needed",
                "Let meat rest after cooking for better texture"
            ]
    
    def validate_recipe_safety(self, ingredients: List[str], instructions: str) -> Dict[str, Any]:
        """
        Basic recipe safety validation
        
        Args:
            ingredients: Recipe ingredients
            instructions: Cooking instructions
            
        Returns:
            Dict: Safety analysis with warnings
        """
        warnings = []
        safety_score = 100  # Start with perfect score
        
        # Check for potentially dangerous ingredients
        dangerous_ingredients = ['raw eggs', 'raw chicken', 'raw fish', 'raw pork', 'raw beef']
        for dangerous in dangerous_ingredients:
            if any(dangerous in ing.lower() for ing in ingredients):
                if 'cook' not in instructions.lower() and 'bake' not in instructions.lower():
                    warnings.append(f"Recipe contains {dangerous} - ensure proper cooking temperatures")
                    safety_score -= 20
        
        # Check for proper cooking instructions
        if any(meat in ' '.join(ingredients).lower() for meat in ['chicken', 'pork', 'beef', 'fish']):
            if not any(word in instructions.lower() for word in ['cook until', 'internal temperature', 'fully cooked']):
                warnings.append("Consider adding internal temperature guidance for meat safety")
                safety_score -= 10
        
        # Check for allergen warnings
        common_allergens = ['nuts', 'peanuts', 'shellfish', 'eggs', 'dairy', 'wheat', 'soy']
        allergens_present = []
        for allergen in common_allergens:
            if any(allergen in ing.lower() for ing in ingredients):
                allergens_present.append(allergen)
        
        if allergens_present:
            warnings.append(f"Contains common allergens: {', '.join(allergens_present)}")
        
        return {
            'safety_score': max(safety_score, 0),
            'warnings': warnings,
            'allergens': allergens_present,
            'safe_for_preparation': safety_score >= 70
        }
    
    def get_nutritional_estimate(self, ingredients: List[str], servings: int = 4) -> Dict[str, Any]:
        """
        Get rough nutritional estimates for recipe ingredients
        
        Args:
            ingredients: Recipe ingredients
            servings: Number of servings
            
        Returns:
            Dict: Nutritional estimates per serving
        """
        # Simple nutritional database (calories per 100g)
        nutrition_db = {
            'chicken': {'calories': 165, 'protein': 25, 'carbs': 0, 'fat': 7},
            'beef': {'calories': 250, 'protein': 22, 'carbs': 0, 'fat': 17},
            'fish': {'calories': 140, 'protein': 25, 'carbs': 0, 'fat': 3},
            'rice': {'calories': 130, 'protein': 3, 'carbs': 28, 'fat': 0.3},
            'pasta': {'calories': 220, 'protein': 8, 'carbs': 44, 'fat': 1.5},
            'potatoes': {'calories': 77, 'protein': 2, 'carbs': 17, 'fat': 0.1},
            'tomatoes': {'calories': 18, 'protein': 1, 'carbs': 4, 'fat': 0.2},
            'onions': {'calories': 40, 'protein': 1, 'carbs': 9, 'fat': 0.1},
            'oil': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100},
            'butter': {'calories': 717, 'protein': 1, 'carbs': 1, 'fat': 81}
        }
        
        total_nutrition = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
        
        for ingredient in ingredients:
            # Simple matching - look for key ingredients
            for key, nutrition in nutrition_db.items():
                if key in ingredient.lower():
                    # Assume 100g per main ingredient, 50g for vegetables, 20g for seasonings
                    portion = 100 if key in ['chicken', 'beef', 'fish', 'rice', 'pasta'] else 50
                    if key in ['oil', 'butter']:
                        portion = 20
                    
                    for nutrient in total_nutrition:
                        total_nutrition[nutrient] += nutrition[nutrient] * (portion / 100)
                    break
        
        # Calculate per serving
        per_serving = {
            nutrient: round(value / servings, 1) 
            for nutrient, value in total_nutrition.items()
        }
        
        return {
            'per_serving': per_serving,
            'total_recipe': total_nutrition,
            'servings': servings,
            'note': 'Estimates based on common ingredient values. Actual nutrition may vary.'
        }

# Export the main service class
__all__ = ['AIRecipeService', 'RecipeSuggestion']