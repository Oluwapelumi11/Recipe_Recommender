/**
 * Recipe Recommender Frontend JavaScript
 * =====================================
 * Modern vanilla JavaScript with optimized performance and accessibility
 * 
 * Features:
 * - Recipe search and filtering
 * - Pantry management
 * - Real-time ingredient suggestions
 * - Progressive enhancement
 * - Offline support
 * - Accessibility compliance
 */

class RecipeRecommender {
    constructor() {
        this.selectedIngredients = new Set();
        this.pantryItems = new Set();
        this.recipeCache = new Map();
        this.currentRecipes = [];
        this.isLoading = false;
        
        // API endpoints
        this.endpoints = {
            search: '/api/recipes/search',
            pantry: '/api/pantry',
            ingredients: '/api/ingredients/suggestions'
        };
        
        // Initialize the application
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        this.bindEventListeners();
        this.loadPantryItems();
        this.setupIngredientSuggestions();
        this.setupKeyboardShortcuts();
        this.loadCommonIngredients();
        
        console.log('🍽️ Recipe Recommender initialized successfully');
    }
    
    /**
     * Bind all event listeners
     */
    bindEventListeners() {
        // Ingredient input and management
        const ingredientInput = document.getElementById('ingredientInput');
        const addIngredientBtn = document.getElementById('addIngredientBtn');
        const searchBtn = document.getElementById('searchRecipesBtn');
        
        // Search functionality
        ingredientInput?.addEventListener('keydown', this.handleIngredientKeydown.bind(this));
        addIngredientBtn?.addEventListener('click', this.addIngredientFromInput.bind(this));
        searchBtn?.addEventListener('click', this.searchRecipes.bind(this));
        
        // Pantry management
        const pantryToggle = document.getElementById('pantryToggle');
        const closePantryBtn = document.getElementById('closePantryBtn');
        const addToPantryBtn = document.getElementById('addToPantryBtn');
        const pantryItemInput = document.getElementById('pantryItemInput');
        
        pantryToggle?.addEventListener('click', () => this.toggleModal('pantryModal'));
        closePantryBtn?.addEventListener('click', () => this.closeModal('pantryModal'));
        addToPantryBtn?.addEventListener('click', this.addToPantry.bind(this));
        pantryItemInput?.addEventListener('keydown', this.handlePantryKeydown.bind(this));
        
        // Modal management
        const recipeModal = document.getElementById('recipeModal');
        const pantryModal = document.getElementById('pantryModal');
        
        recipeModal?.addEventListener('click', (e) => {
            if (e.target === recipeModal) this.closeModal('recipeModal');
        });
        pantryModal?.addEventListener('click', (e) => {
            if (e.target === pantryModal) this.closeModal('pantryModal');
        });
        
        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        themeToggle?.addEventListener('click', this.toggleTheme.bind(this));
        
        // Load more recipes
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        loadMoreBtn?.addEventListener('click', this.loadMoreRecipes.bind(this));
        
        // Dietary restrictions handling
        document.querySelectorAll('.dietary-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', this.updateDietaryPreferences.bind(this));
        });
    }
    
    /**
     * Handle keyboard input for ingredient entry
     */
    handleIngredientKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.addIngredientFromInput();
        } else if (e.key === 'Escape') {
            this.hideIngredientSuggestions();
        }
    }
    
    /**
     * Handle keyboard input for pantry items
     */
    handlePantryKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.addToPantry();
        }
    }
    
    /**
     * Setup keyboard shortcuts for power users
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for quick search focus
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('ingredientInput')?.focus();
            }
            
            // Ctrl/Cmd + P for pantry
            if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
                e.preventDefault();
                this.toggleModal('pantryModal');
            }
            
            // Escape to close any open modal
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }
    
    /**
     * Add ingredient from input field
     */
    addIngredientFromInput() {
        const input = document.getElementById('ingredientInput');
        const ingredient = input.value.trim().toLowerCase();
        
        if (ingredient && !this.selectedIngredients.has(ingredient)) {
            this.addIngredient(ingredient);
            input.value = '';
            input.focus();
        }
    }
    
    /**
     * Add ingredient to selected list
     */
    addIngredient(ingredient) {
        this.selectedIngredients.add(ingredient);
        this.renderIngredientTags();
        this.validateSearchButton();
        
        // Analytics tracking
        this.trackUserAction('ingredient_added', { ingredient });
        
        // Accessibility announcement
        if (window.announceToScreenReader) {
            window.announceToScreenReader(`Added ${ingredient} to ingredients list`);
        }
    }
    
    /**
     * Remove ingredient from selected list
     */
    removeIngredient(ingredient) {
        this.selectedIngredients.delete(ingredient);
        this.renderIngredientTags();
        this.validateSearchButton();
        
        // Analytics tracking
        this.trackUserAction('ingredient_removed', { ingredient });
        
        // Accessibility announcement
        if (window.announceToScreenReader) {
            window.announceToScreenReader(`Removed ${ingredient} from ingredients list`);
        }
    }
    
    /**
     * Render ingredient tags in the UI
     */
    renderIngredientTags() {
        const container = document.getElementById('ingredientTags');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.selectedIngredients.forEach(ingredient => {
            const tag = document.createElement('div');
            tag.className = 'flex items-center space-x-2 bg-primary-100 text-primary-800 px-3 py-1 rounded-full text-sm font-medium animate-slide-up';
            tag.innerHTML = `
                <span>${this.capitalizeFirst(ingredient)}</span>
                <button 
                    type="button" 
                    onclick="recipeApp.removeIngredient('${ingredient}')"
                    class="text-primary-600 hover:text-primary-800 font-bold text-lg leading-none"
                    aria-label="Remove ${ingredient}"
                >
                    ×
                </button>
            `;
            container.appendChild(tag);
        });
        
        // Show placeholder if no ingredients
        if (this.selectedIngredients.size === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm italic">No ingredients selected. Add some ingredients above to get started!</p>';
        }
    }
    
    /**
     * Validate search button state
     */
    validateSearchButton() {
        const searchBtn = document.getElementById('searchRecipesBtn');
        const hasIngredients = this.selectedIngredients.size > 0;
        
        if (searchBtn) {
            searchBtn.disabled = !hasIngredients || this.isLoading;
            searchBtn.classList.toggle('opacity-50', !hasIngredients || this.isLoading);
        }
    }
    
    /**
     * Setup ingredient auto-suggestions
     */
    setupIngredientSuggestions() {
        const input = document.getElementById('ingredientInput');
        if (!input) return;
        
        let debounceTimer;
        
        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = e.target.value.trim();
                if (query.length >= 2) {
                    this.showIngredientSuggestions(query);
                } else {
                    this.hideIngredientSuggestions();
                }
            }, 300);
        });
        
        input.addEventListener('blur', () => {
            // Hide suggestions after a brief delay to allow for clicks
            setTimeout(() => this.hideIngredientSuggestions(), 150);
        });
    }
    
    /**
     * Show ingredient suggestions
     */
    async showIngredientSuggestions(query) {
        const container = document.getElementById('ingredientSuggestions');
        if (!container) return;
        
        try {
            // Use cached common ingredients for suggestions
            const commonIngredients = this.getCommonIngredients();
            const suggestions = commonIngredients
                .filter(ingredient => 
                    ingredient.toLowerCase().includes(query.toLowerCase()) &&
                    !this.selectedIngredients.has(ingredient.toLowerCase())
                )
                .slice(0, 8);
            
            if (suggestions.length > 0) {
                container.innerHTML = suggestions.map(ingredient => 
                    `<button 
                        type="button"
                        onclick="recipeApp.addIngredient('${ingredient.toLowerCase()}')"
                        class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm transition-colors duration-200"
                    >
                        ${this.capitalizeFirst(ingredient)}
                    </button>`
                ).join('');
                container.classList.remove('hidden');
            } else {
                this.hideIngredientSuggestions();
            }
        } catch (error) {
            console.error('Error showing suggestions:', error);
            this.hideIngredientSuggestions();
        }
    }
    
    /**
     * Hide ingredient suggestions
     */
    hideIngredientSuggestions() {
        const container = document.getElementById('ingredientSuggestions');
        if (container) {
            container.classList.add('hidden');
            container.innerHTML = '';
        }
    }
    
    /**
     * Get common ingredients for suggestions
     */
    getCommonIngredients() {
        return [
            'chicken', 'beef', 'pork', 'fish', 'eggs', 'tofu',
            'tomatoes', 'onions', 'garlic', 'carrots', 'potatoes', 'spinach',
            'rice', 'pasta', 'bread', 'flour', 'quinoa',
            'olive oil', 'butter', 'salt', 'pepper', 'cumin', 'paprika',
            'lemon', 'lime', 'ginger', 'basil', 'parsley',
            // Sudanese ingredients
            'fava beans', 'sorghum flour', 'peanuts', 'sesame seeds', 'tamarind',
            'okra', 'collard greens', 'cardamom', 'cinnamon'
        ];
    }
    
    /**
     * Load common ingredients for quick add buttons
     */
    loadCommonIngredients() {
        const container = document.getElementById('commonIngredients');
        if (!container) return;
        
        const commonIngredients = [
            'chicken', 'beef', 'tomatoes', 'onions', 'garlic', 'rice',
            'pasta', 'potatoes', 'carrots', 'spinach', 'eggs', 'cheese'
        ];
        
        container.innerHTML = commonIngredients.map(ingredient => 
            `<button 
                type="button"
                onclick="recipeApp.addToPantryItem('${ingredient}')"
                class="px-3 py-1 bg-gray-100 hover:bg-sudanese-100 text-gray-700 hover:text-sudanese-700 rounded-full text-sm transition-colors duration-200"
            >
                ${this.capitalizeFirst(ingredient)}
            </button>`
        ).join('');
    }
    
    /**
     * Search for recipes based on selected ingredients and preferences
     */
    async searchRecipes() {
        if (this.selectedIngredients.size === 0 || this.isLoading) return;
        
        this.setLoadingState(true);
        
        try {
            // Build search parameters
            const searchParams = {
                ingredients: Array.from(this.selectedIngredients),
                cuisine_preference: document.getElementById('cuisineSelect')?.value || 'any',
                difficulty: parseInt(document.getElementById('difficultySelect')?.value || '3'),
                max_cook_time: parseInt(document.getElementById('maxTimeSelect')?.value || '60'),
                dietary_restrictions: this.getDietaryRestrictions()
            };
            
            // Check cache first
            const cacheKey = JSON.stringify(searchParams);
            if (this.recipeCache.has(cacheKey)) {
                console.log('Using cached recipe results');
                this.displayRecipes(this.recipeCache.get(cacheKey));
                this.setLoadingState(false);
                return;
            }
            
            // Make API request
            console.log('Searching for recipes with params:', searchParams);
            
            const response = await fetch(this.endpoints.search, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchParams)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Cache the results
            this.recipeCache.set(cacheKey, data);
            
            // Display results
            this.displayRecipes(data);
            
            // Analytics tracking
            this.trackUserAction('recipe_search', {
                ingredient_count: searchParams.ingredients.length,
                cuisine: searchParams.cuisine_preference,
                results_count: data.recipes?.length || 0
            });
            
            // Accessibility announcement
            if (window.announceToScreenReader) {
                const count = data.recipes?.length || 0;
                window.announceToScreenReader(`Found ${count} recipe${count !== 1 ? 's' : ''}`);
            }
            
        } catch (error) {
            console.error('Recipe search error:', error);
            this.showErrorToast(error.message || 'Failed to search recipes. Please try again.');
            
            // Show fallback recipes if available
            this.showFallbackRecipes();
        } finally {
            this.setLoadingState(false);
        }
    }
    
    /**
     * Display recipe search results
     */
    displayRecipes(data) {
        const resultsSection = document.getElementById('recipeResults');
        const recipeGrid = document.getElementById('recipeGrid');
        const resultStats = document.getElementById('resultStats');
        
        if (!resultsSection || !recipeGrid) return;
        
        this.currentRecipes = data.recipes || [];
        
        // Show results section
        resultsSection.classList.remove('hidden');
        
        // Update stats
        if (resultStats) {
            const count = this.currentRecipes.length;
            const totalFound = data.total_found || count;
            resultStats.textContent = `Found ${totalFound} recipe${totalFound !== 1 ? 's' : ''}`;
        }
        
        // Clear previous results
        recipeGrid.innerHTML = '';
        
        // Display recipes
        if (this.currentRecipes.length === 0) {
            recipeGrid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <div class="text-6xl mb-4">🍳</div>
                    <h3 class="text-xl font-semibold text-gray-900 mb-2">No recipes found</h3>
                    <p class="text-gray-600 mb-4">Try adjusting your ingredients or preferences</p>
                    <button onclick="recipeApp.showSuggestedIngredients()" class="text-primary-500 hover:text-primary-600 font-medium">
                        Get ingredient suggestions →
                    </button>
                </div>
            `;
        } else {
            this.currentRecipes.forEach((recipe, index) => {
                const recipeCard = this.createRecipeCard(recipe, index);
                recipeGrid.appendChild(recipeCard);
            });
        }
        
        // Smooth scroll to results
        resultsSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
    
    /**
     * Create a recipe card element
     */
    createRecipeCard(recipe, index) {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden cursor-pointer recipe-card transform hover:scale-105';
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `View recipe for ${recipe.name}`);
        card.setAttribute('data-track', 'recipe_card_click');
        
        // Calculate match percentage
        const matchPercentage = this.calculateIngredientMatch(recipe);
        
        // Get cuisine flag emoji
        const cuisineFlag = this.getCuisineFlag(recipe.cuisine_type);
        
        // Format dietary tags
        let dietaryTags = [];
        try {
            dietaryTags = typeof recipe.dietary_tags === 'string' 
                ? JSON.parse(recipe.dietary_tags) 
                : (recipe.dietary_tags || []);
        } catch (e) {
            dietaryTags = [];
        }
        
        card.innerHTML = `
            <div class="relative">
                <!-- Recipe Image Placeholder -->
                <div class="h-48 bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
                    <div class="text-4xl text-white">
                        ${this.getRecipeEmoji(recipe.cuisine_type, recipe.name)}
                    </div>
                </div>
                
                <!-- Match Badge -->
                <div class="absolute top-2 right-2 bg-white bg-opacity-90 backdrop-blur-sm px-2 py-1 rounded-full text-xs font-semibold text-gray-700">
                    ${matchPercentage}% match
                </div>
                
                <!-- Cuisine Badge -->
                <div class="absolute top-2 left-2 bg-white bg-opacity-90 backdrop-blur-sm px-2 py-1 rounded-full text-xs font-medium">
                    ${cuisineFlag} ${this.capitalizeFirst(recipe.cuisine_type)}
                </div>
            </div>
            
            <div class="p-6">
                <h4 class="text-lg font-bold text-gray-900 mb-2 line-clamp-2">${recipe.name}</h4>
                
                <!-- Recipe Meta -->
                <div class="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                    <div class="flex items-center space-x-1">
                        <span>⏱️</span>
                        <span>${recipe.cook_time_minutes || 30} min</span>
                    </div>
                    <div class="flex items-center space-x-1">
                        <span>👥</span>
                        <span>${recipe.serving_size || 4} servings</span>
                    </div>
                    <div class="flex items-center space-x-1">
                        <span>${this.getDifficultyEmoji(recipe.difficulty_level)}</span>
                        <span>${this.getDifficultyText(recipe.difficulty_level)}</span>
                    </div>
                </div>
                
                <!-- Dietary Tags -->
                ${dietaryTags.length > 0 ? `
                    <div class="flex flex-wrap gap-1 mb-3">
                        ${dietaryTags.slice(0, 3).map(tag => 
                            `<span class="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">${this.formatDietaryTag(tag)}</span>`
                        ).join('')}
                        ${dietaryTags.length > 3 ? `<span class="text-xs text-gray-500">+${dietaryTags.length - 3} more</span>` : ''}
                    </div>
                ` : ''}
                
                <!-- Ingredients Preview -->
                <div class="text-sm text-gray-600 mb-4">
                    <p class="line-clamp-2">
                        <span class="font-medium">Ingredients:</span> 
                        ${this.formatIngredientsPreview(recipe.ingredients)}
                    </p>
                </div>
                
                <!-- Action Button -->
                <button 
                    onclick="recipeApp.showRecipeDetails(${index})"
                    class="w-full bg-gradient-to-r from-primary-500 to-primary-600 text-white py-2 px-4 rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all duration-200 font-medium"
                >
                    View Recipe
                </button>
            </div>
        `;
        
        // Add click handler for card
        card.addEventListener('click', () => this.showRecipeDetails(index));
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.showRecipeDetails(index);
            }
        });
        
        return card;
    }
    
    /**
     * Calculate ingredient match percentage
     */
    calculateIngredientMatch(recipe) {
        if (!recipe.ingredients) return 0;
        
        let recipeIngredients = [];
        try {
            recipeIngredients = typeof recipe.ingredients === 'string' 
                ? JSON.parse(recipe.ingredients) 
                : recipe.ingredients;
        } catch (e) {
            return 0;
        }
        
        const selectedArray = Array.from(this.selectedIngredients);
        const matchCount = recipeIngredients.filter(ingredient => 
            selectedArray.some(selected => 
                ingredient.toLowerCase().includes(selected) || 
                selected.includes(ingredient.toLowerCase())
            )
        ).length;
        
        return Math.round((matchCount / Math.max(recipeIngredients.length, 1)) * 100);
    }
    
    /**
     * Get cuisine flag emoji
     */
    getCuisineFlag(cuisineType) {
        const flags = {
            'sudanese': '🇸🇩',
            'italian': '🇮🇹',
            'chinese': '🇨🇳',
            'indian': '🇮🇳',
            'mexican': '🇲🇽',
            'french': '🇫🇷',
            'japanese': '🇯🇵',
            'thai': '🇹🇭',
            'mediterranean': '🌊',
            'american': '🇺🇸',
            'global': '🌍'
        };
        return flags[cuisineType] || '🌍';
    }
    
    /**
     * Get recipe emoji based on cuisine and name
     */
    getRecipeEmoji(cuisineType, recipeName) {
        const name = recipeName.toLowerCase();
        
        // Specific dish emojis
        if (name.includes('pasta') || name.includes('spaghetti')) return '🍝';
        if (name.includes('pizza')) return '🍕';
        if (name.includes('burger')) return '🍔';
        if (name.includes('soup') || name.includes('stew')) return '🍲';
        if (name.includes('salad')) return '🥗';
        if (name.includes('rice')) return '🍚';
        if (name.includes('bread')) return '🍞';
        if (name.includes('chicken')) return '🍗';
        if (name.includes('fish')) return '🐟';
        if (name.includes('curry')) return '🍛';
        if (name.includes('sandwich')) return '🥪';
        
        // Cuisine-based emojis
        const cuisineEmojis = {
            'sudanese': '🫘',
            'italian': '🍝',
            'chinese': '🥢',
            'indian': '🍛',
            'mexican': '🌮',
            'japanese': '🍱',
            'thai': '🍜',
            'american': '🍔'
        };
        
        return cuisineEmojis[cuisineType] || '🍽️';
    }
    
    /**
     * Get difficulty emoji
     */
    getDifficultyEmoji(difficulty) {
        const emojis = {
            1: '🟢',
            2: '🟡',
            3: '🟠',
            4: '🔴',
            5: '⚫'
        };
        return emojis[difficulty] || '🟠';
    }
    
    /**
     * Get difficulty text
     */
    getDifficultyText(difficulty) {
        const texts = {
            1: 'Very Easy',
            2: 'Easy',
            3: 'Medium',
            4: 'Hard',
            5: 'Expert'
        };
        return texts[difficulty] || 'Medium';
    }
    
    /**
     * Format dietary tag for display
     */
    formatDietaryTag(tag) {
        const tagMap = {
            'vegetarian': '🌱 Vegetarian',
            'vegan': '🌿 Vegan',
            'gluten-free': '🌾 Gluten-Free',
            'dairy-free': '🥛 Dairy-Free',
            'low-carb': '🥗 Low-Carb',
            'keto': '🥑 Keto',
            'paleo': '🦴 Paleo',
            'high-protein': '💪 High Protein',
            'quick': '⚡ Quick',
            'one-pan': '🍳 One Pan'
        };
        return tagMap[tag] || this.capitalizeFirst(tag);
    }
    
    /**
     * Format ingredients preview
     */
    formatIngredientsPreview(ingredients) {
        if (!ingredients) return 'No ingredients listed';
        
        let ingredientList = [];
        try {
            ingredientList = typeof ingredients === 'string' 
                ? JSON.parse(ingredients) 
                : ingredients;
        } catch (e) {
            return 'Ingredients not available';
        }
        
        if (ingredientList.length === 0) return 'No ingredients listed';
        
        const preview = ingredientList
            .slice(0, 4)
            .map(ing => this.capitalizeFirst(ing))
            .join(', ');
        
        return ingredientList.length > 4 
            ? `${preview}, +${ingredientList.length - 4} more`
            : preview;
    }
    
    /**
     * Show recipe details in modal
     */
    showRecipeDetails(index) {
        const recipe = this.currentRecipes[index];
        if (!recipe) return;
        
        const modal = document.getElementById('recipeModal');
        const content = document.getElementById('recipeModalContent');
        
        if (!modal || !content) return;
        
        // Parse ingredients and dietary tags
        let ingredients = [];
        let dietaryTags = [];
        
        try {
            ingredients = typeof recipe.ingredients === 'string' 
                ? JSON.parse(recipe.ingredients) 
                : (recipe.ingredients || []);
            dietaryTags = typeof recipe.dietary_tags === 'string'
                ? JSON.parse(recipe.dietary_tags)
                : (recipe.dietary_tags || []);
        } catch (e) {
            console.error('Error parsing recipe data:', e);
        }
        
        // Format instructions
        const instructions = recipe.instructions || 'Instructions not available';
        const steps = instructions.split(/\d+\.\s/).filter(step => step.trim());
        
        content.innerHTML = `
            <!-- Modal Header -->
            <div class="flex justify-between items-start p-6 border-b border-gray-200">
                <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-2">
                        <div class="text-2xl">${this.getRecipeEmoji(recipe.cuisine_type, recipe.name)}</div>
                        <h2 class="text-2xl font-bold text-gray-900">${recipe.name}</h2>
                    </div>
                    
                    <div class="flex items-center space-x-4 text-sm text-gray-600">
                        <span class="flex items-center space-x-1">
                            <span>${this.getCuisineFlag(recipe.cuisine_type)}</span>
                            <span>${this.capitalizeFirst(recipe.cuisine_type)} Cuisine</span>
                        </span>
                        <span class="flex items-center space-x-1">
                            <span>⏱️</span>
                            <span>${recipe.cook_time_minutes || 30} minutes</span>
                        </span>
                        <span class="flex items-center space-x-1">
                            <span>👥</span>
                            <span>${recipe.serving_size || 4} servings</span>
                        </span>
                        <span class="flex items-center space-x-1">
                            <span>${this.getDifficultyEmoji(recipe.difficulty_level)}</span>
                            <span>${this.getDifficultyText(recipe.difficulty_level)}</span>
                        </span>
                    </div>
                </div>
                
                <button 
                    onclick="recipeApp.closeModal('recipeModal')"
                    class="text-gray-400 hover:text-gray-600 text-2xl font-bold p-1"
                    aria-label="Close recipe details"
                >
                    ×
                </button>
            </div>
            
            <!-- Modal Body -->
            <div class="p-6 max-h-[70vh] overflow-y-auto">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <!-- Ingredients Section -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
                            <span>🛒</span>
                            <span>Ingredients</span>
                            <span class="text-sm font-normal text-gray-500">(${ingredients.length} items)</span>
                        </h3>
                        
                        <ul class="space-y-2 mb-6">
                            ${ingredients.map(ingredient => `
                                <li class="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 transition-colors duration-200">
                                    <span class="w-4 h-4 border-2 border-gray-300 rounded flex-shrink-0"></span>
                                    <span class="text-gray-700">${this.capitalizeFirst(ingredient)}</span>
                                    ${this.selectedIngredients.has(ingredient.toLowerCase()) ? 
                                        '<span class="ml-auto text-green-500 text-sm">✓ Have it</span>' : 
                                        '<button onclick="recipeApp.addIngredient(\''+ingredient.toLowerCase()+'\')" class="ml-auto text-primary-500 hover:text-primary-600 text-sm">+ Add</button>'
                                    }
                                </li>
                            `).join('')}
                        </ul>
                        
                        <!-- Dietary Tags -->
                        ${dietaryTags.length > 0 ? `
                            <div class="mb-6">
                                <h4 class="text-md font-medium text-gray-900 mb-2">Dietary Information</h4>
                                <div class="flex flex-wrap gap-2">
                                    ${dietaryTags.map(tag => 
                                        `<span class="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">${this.formatDietaryTag(tag)}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        <!-- Nutritional Info (if available) -->
                        ${recipe.calories_per_serving ? `
                            <div class="bg-gray-50 rounded-lg p-4">
                                <h4 class="text-md font-medium text-gray-900 mb-2">Nutritional Info (per serving)</h4>
                                <div class="text-sm text-gray-600">
                                    <span class="font-medium">${recipe.calories_per_serving} calories</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    
                    <!-- Instructions Section -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
                            <span>👨‍🍳</span>
                            <span>Instructions</span>
                        </h3>
                        
                        <div class="space-y-4">
                            ${steps.length > 1 ? 
                                steps.map((step, i) => `
                                    <div class="flex space-x-4 p-4 bg-gray-50 rounded-lg">
                                        <div class="flex-shrink-0 w-8 h-8 bg-primary-500 text-white rounded-full flex items-center justify-center text-sm font-semibold">
                                            ${i + 1}
                                        </div>
                                        <p class="text-gray-700 leading-relaxed">${step.trim()}</p>
                                    </div>
                                `).join('') :
                                `<div class="p-4 bg-gray-50 rounded-lg">
                                    <p class="text-gray-700 leading-relaxed whitespace-pre-line">${instructions}</p>
                                </div>`
                            }
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Modal Footer -->
            <div class="flex justify-between items-center p-6 border-t border-gray-200 bg-gray-50">
                <div class="flex items-center space-x-4 text-sm text-gray-600">
                    <span class="flex items-center space-x-1">
                        <span>📊</span>
                        <span>${this.calculateIngredientMatch(recipe)}% ingredient match</span>
                    </span>
                    <span class="flex items-center space-x-1">
                        <span>🤖</span>
                        <span>AI-${recipe.source || 'generated'}</span>
                    </span>
                </div>
                
                <div class="flex space-x-3">
                    <button 
                        onclick="recipeApp.saveRecipe(${index})"
                        class="flex items-center space-x-2 px-4 py-2 bg-sudanese-500 text-white rounded-lg hover:bg-sudanese-600 transition-colors duration-200"
                    >
                        <span>💾</span>
                        <span>Save Recipe</span>
                    </button>
                    
                    <button 
                        onclick="recipeApp.shareRecipe(${index})"
                        class="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors duration-200"
                    >
                        <span>📤</span>
                        <span>Share</span>
                    </button>
                </div>
            </div>
        `;
        
        // Show modal
        modal.classList.remove('hidden');
        modal.classList.add('modal-open');
        
        // Focus management
        const firstFocusable = content.querySelector('button, [href], input, select, textarea');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
        
        // Analytics tracking
        this.trackUserAction('recipe_detail_view', {
            recipe_name: recipe.name,
            cuisine_type: recipe.cuisine_type
        });
    }
    
    /**
     * Pantry Management Functions
     */
    async loadPantryItems() {
        // For demo purposes, load from localStorage
        // In production, this would load from the backend
        try {
            const saved = localStorage.getItem('pantryItems');
            if (saved) {
                this.pantryItems = new Set(JSON.parse(saved));
                this.renderPantryItems();
            }
        } catch (error) {
            console.error('Error loading pantry items:', error);
        }
    }
    
    async savePantryItems() {
        try {
            localStorage.setItem('pantryItems', JSON.stringify(Array.from(this.pantryItems)));
        } catch (error) {
            console.error('Error saving pantry items:', error);
        }
    }
    
    addToPantry() {
        const input = document.getElementById('pantryItemInput');
        const item = input.value.trim().toLowerCase();
        
        if (item && !this.pantryItems.has(item)) {
            this.pantryItems.add(item);
            this.renderPantryItems();
            this.savePantryItems();
            input.value = '';
            
            this.showSuccessToast(`Added ${this.capitalizeFirst(item)} to pantry`);
            this.trackUserAction('pantry_item_added', { item });
        }
    }
    
    addToPantryItem(item) {
        if (!this.pantryItems.has(item)) {
            this.pantryItems.add(item);
            this.renderPantryItems();
            this.savePantryItems();
            
            this.showSuccessToast(`Added ${this.capitalizeFirst(item)} to pantry`);
        }
    }
    
    removePantryItem(item) {
        this.pantryItems.delete(item);
        this.renderPantryItems();
        this.savePantryItems();
        
        this.showSuccessToast(`Removed ${this.capitalizeFirst(item)} from pantry`);
        this.trackUserAction('pantry_item_removed', { item });
    }
    
    renderPantryItems() {
        const container = document.getElementById('pantryItemsList');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.pantryItems.size === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <div class="text-4xl mb-2">🛒</div>
                    <p>Your pantry is empty</p>
                    <p class="text-sm">Add ingredients you frequently use</p>
                </div>
            `;
            return;
        }
        
        this.pantryItems.forEach(item => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200';
            itemDiv.innerHTML = `
                <span class="text-gray-700">${this.capitalizeFirst(item)}</span>
                <div class="flex space-x-2">
                    <button 
                        onclick="recipeApp.addIngredient('${item}')"
                        class="text-primary-500 hover:text-primary-600 text-sm px-2 py-1 rounded"
                        title="Add to search"
                    >
                        + Use
                    </button>
                    <button 
                        onclick="recipeApp.removePantryItem('${item}')"
                        class="text-red-500 hover:text-red-600 text-sm px-2 py-1 rounded"
                        title="Remove from pantry"
                    >
                        Remove
                    </button>
                </div>
            `;
            container.appendChild(itemDiv);
        });
    }
    
    /**
     * Utility Functions
     */
    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    setLoadingState(loading) {
        this.isLoading = loading;
        const searchBtn = document.getElementById('searchRecipesBtn');
        const searchText = document.getElementById('searchBtnText');
        const searchSpinner = document.getElementById('searchSpinner');
        
        if (searchBtn) {
            searchBtn.disabled = loading;
            searchBtn.classList.toggle('opacity-50', loading);
        }
        
        if (searchText && searchSpinner) {
            searchText.classList.toggle('hidden', loading);
            searchSpinner.classList.toggle('hidden', !loading);
        }
        
        this.validateSearchButton();
    }
    
    getDietaryRestrictions() {
        const checkboxes = document.querySelectorAll('.dietary-checkbox:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    updateDietaryPreferences() {
        // Could save preferences here
        this.trackUserAction('dietary_preferences_updated', {
            restrictions: this.getDietaryRestrictions()
        });
    }
    
    toggleModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const isHidden = modal.classList.contains('hidden');
            if (isHidden) {
                modal.classList.remove('hidden');
                modal.classList.add('modal-open');
            } else {
                modal.classList.add('hidden');
                modal.classList.remove('modal-open');
            }
        }
    }
    
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('modal-open');
        }
    }
    
    closeAllModals() {
        this.closeModal('pantryModal');
        this.closeModal('recipeModal');
    }
    
    showSuccessToast(message) {
        const toast = document.getElementById('successToast');
        const messageEl = document.getElementById('toastMessage');
        
        if (toast && messageEl) {
            messageEl.textContent = message;
            toast.classList.remove('hidden');
            
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 3000);
        }
    }
    
    showErrorToast(message) {
        const toast = document.getElementById('errorToast');
        const messageEl = document.getElementById('errorMessage');
        
        if (toast && messageEl) {
            messageEl.textContent = message;
            toast.classList.remove('hidden');
            
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 5000);
        }
    }
    
    showFallbackRecipes() {
        // Show some basic fallback recipes when API fails
        const fallbackRecipes = {
            recipes: [
                {
                    name: "Simple Stir-fry",
                    ingredients: JSON.stringify(Array.from(this.selectedIngredients).slice(0, 5)),
                    instructions: "1. Heat oil in a large pan. 2. Add ingredients one by one, starting with those that take longest to cook. 3. Stir frequently and season with salt and pepper. 4. Serve hot.",
                    cuisine_type: "global",
                    difficulty_level: 2,
                    cook_time_minutes: 15,
                    serving_size: 2,
                    dietary_tags: JSON.stringify(["quick", "easy"]),
                    source: "fallback"
                }
            ],
            total_found: 1
        };
        
        this.displayRecipes(fallbackRecipes);
    }
    
    toggleTheme() {
        // Simple dark mode toggle
        document.body.classList.toggle('dark');
        const isDark = document.body.classList.contains('dark');
        
        localStorage.setItem('darkMode', isDark);
        this.trackUserAction('theme_toggled', { dark_mode: isDark });
    }
    
    saveRecipe(index) {
        const recipe = this.currentRecipes[index];
        if (!recipe) return;
        
        // Save to localStorage for demo
        try {
            let savedRecipes = JSON.parse(localStorage.getItem('savedRecipes') || '[]');
            
            if (!savedRecipes.find(r => r.name === recipe.name)) {
                savedRecipes.push(recipe);
                localStorage.setItem('savedRecipes', JSON.stringify(savedRecipes));
                this.showSuccessToast('Recipe saved successfully!');
            } else {
                this.showSuccessToast('Recipe already saved');
            }
        } catch (error) {
            console.error('Error saving recipe:', error);
            this.showErrorToast('Failed to save recipe');
        }
        
        this.trackUserAction('recipe_saved', { recipe_name: recipe.name });
    }
    
    shareRecipe(index) {
        const recipe = this.currentRecipes[index];
        if (!recipe) return;
        
        if (navigator.share) {
            navigator.share({
                title: recipe.name,
                text: `Check out this ${recipe.cuisine_type} recipe: ${recipe.name}`,
                url: window.location.href
            });
        } else {
            // Fallback to clipboard
            const shareText = `${recipe.name}\n\nIngredients: ${this.formatIngredientsPreview(recipe.ingredients)}\n\nFind more recipes at ${window.location.href}`;
            
            navigator.clipboard.writeText(shareText).then(() => {
                this.showSuccessToast('Recipe copied to clipboard!');
            }).catch(() => {
                this.showErrorToast('Failed to copy recipe');
            });
        }
        
        this.trackUserAction('recipe_shared', { recipe_name: recipe.name });
    }
    
    loadMoreRecipes() {
        // Placeholder for loading more recipes
        this.showSuccessToast('Loading more recipes...');
    }
    
    showSuggestedIngredients() {
        const suggestions = [
            'chicken', 'onions', 'garlic', 'tomatoes', 'rice',
            'olive oil', 'salt', 'pepper', 'carrots', 'potatoes'
        ];
        
        suggestions.forEach(ingredient => {
            if (!this.selectedIngredients.has(ingredient)) {
                this.addIngredient(ingredient);
            }
        });
    }
    
    trackUserAction(action, data = {}) {
        // Simple analytics tracking
        console.log('User Action:', action, data);
        
        // In production, this would send to analytics service
        if (window.gtag) {
            window.gtag('event', action, data);
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create global instance
    window.recipeApp = new RecipeRecommender();
    
    // Load dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark');
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RecipeRecommender;
}