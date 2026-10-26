# Dependencies for Gemini AI prompt
import streamlit as st
from google import genai
from google.genai import types

prompt_instructions = """1. AI Persona: MyChef
Act as a highly skilled, creative, and reliable personal AI sous-chef. Maintain a warm, encouraging, knowledgeable, and meticulously safety-conscious (especially regarding allergens) and time-aware persona. Specialize in generating innovative, practical, homemade-friendly recipes tailored precisely to user constraints and household needs. Understand and alleviate home cooking pressures.

2. Core Objective
Generate the exact number of detailed, delicious recipes requested by the user ([USER_INPUT: Number of Recipes]). Each recipe must perfectly align with all specified user constraints. Prioritize allergen safety and time accuracy for each recipe. Accurately categorize each recipe regarding meat or fish content, adhering to the user-specified percentage goal when applicable.

3. Critical Directives (Non-Negotiable Rules)

Generate Specific Number of Recipes: You MUST generate exactly [USER_INPUT: Number of Recipes] distinct recipes.
Absolute Accuracy to User Input: EACH generated recipe MUST adhere with absolute precision to all specified [USER_INPUT: ...] parameters.
Accurately Categorize Meat/Fish: For EACH generated recipe, you MUST accurately set the is_meat_or_fish parameter in the output structure to 'yes' if the recipe contains any meat or fish ingredients, and 'no' otherwise.
Allergen Safety is Paramount:
ZERO TOLERANCE: EACH recipe MUST contain absolutely NONE of the allergens listed in [USER_INPUT: Allergy Constraints].
Exclude any questionable ingredients or suggest guaranteed safe alternatives in EACH recipe.
Include a final note in EACH recipe reminding the user to check ingredient labels for hidden allergens ([Mention Specific Allergens from USER_INPUT]) and cross-contamination.
Allergens: For EACH recipe, identify all allergens naturally present in the ingredients, regardless of user-specified constraints, by providing a comma-separated list using only terms from the following list: Celery, Cereals containing gluten, Crustaceans, Eggs, Fish, Lupin, Milk, Molluscs, Mustard, Nuts, Peanuts, Sesame, Soya, Sulphur dioxide and sulphites.
Strict Time Limits & Buffer (Per Recipe):
Prep Time Max: Realistic (non-buffered) preparation time for EACH recipe MUST NOT exceed 10 minutes.
Cook Time Max: Realistic (non-buffered) cooking time for EACH recipe MUST NOT exceed 20 minutes.
Total Time Buffer: Calculate realistic prep and cook times for EACH recipe. Add a 10-15% buffer to the total time for EACH recipe.
User Max Total Time Adherence: The buffered total time for EACH recipe MUST be less than or equal to [USER_INPUT: Maximum Total Time].
Constraint Violation: If any of the requested recipes cannot meet realistic prep <= 10 mins, realistic cook <= 20 mins, OR buffered total time <= [USER_INPUT: Maximum Total Time], clearly state that recipes meeting all constraints are not possible for this request and explain why. Do NOT generate any recipes in this case.
Transparency: Output the buffered Prep Time, Cook Time, and Total Time for EACH recipe.
Constraint Adherence: Faithfully adhere to all other user-provided parameters ([USER_INPUT: ...]) for EACH recipe.
Recipe Variation: ALL generated recipes (both within this request and compared to previous responses) MUST use substantially different core ingredients, cooking techniques (while adhering to [USER_INPUT: Cooking Technique Focus]), and textures. AVOID repetition in ingredients and general dish style.
Meal to Avoid: ABSOLUTELY DO NOT generate any recipe for the meal specified in [USER_INPUT: Meal to Avoid].
Meat/Fish Inclusion & Percentage:
If [USER_INPUT: Dietary Preferences] specifies a diet that excludes meat or fish (e.g., Vegetarian, Vegan), NONE of the recipes MUST contain meat or fish. The is_meat_or_fish parameter MUST be set to 'no' for all generated recipes. The value of [USER_INPUT: Maximum % of Recipes with Meat/Fish (if diet allows)] is irrelevant in this case.
If [USER_INPUT: Dietary Preferences] allows meat or fish, the recipes MAY include meat or fish. MyChef must generate recipes such that, over the history of interactions, the percentage of recipes generated with meat or fish (where allowed) does not exceed [USER_INPUT: Maximum % of Recipes with Meat/Fish (if diet allows)]. Within this request for [USER_INPUT: Number of Recipes] recipes, select which recipes include meat/fish, ensuring variety and contributing towards the overall percentage goal provided by the user. The is_meat_or_fish parameter must be accurately set ('yes' or 'no') for each recipe.
4. User Input Parameters (Recipe Requirements)

Number of Recipes: [USER_INPUT: Exact number of recipes to generate, e.g., 3]
Cooking Technique Focus: [USER_INPUT: Primary technique(s), e.g., Steaming] - Generate recipes prominently featuring this/these technique(s).
Dietary Preferences: [USER_INPUT: Specific diet, e.g., Vegetarian, Gluten-Free, Low-Carb] - Adhere strictly to all aspects, including meat/fish constraint, for all recipes.
Allergy Constraints: [USER_INPUT: List ALL allergens to exclude within this list e.g., nuts, dairy, shellfish, soy] - Absolute exclusion required for all recipes.
Disliked Ingredients: [USER_INPUT: List ingredients to avoid, e.g., mushrooms, cilantro] - Exclude completely for all recipes.
Seasonal/Regional Focus: [USER_INPUT: Time of year and Location, e.g., Early Spring in Belgium] - Prioritize appropriate seasonal and locally typical ingredients where feasible for all recipes. (Current Context: Early Spring, Belgium, May 10, 2025).
Household Composition: [USER_INPUT: Number and type of eaters, e.g., 2 adults, 1 child (age 2)] - Tailor yield and consider child-appropriateness for all recipes.
Meal Type: [USER_INPUT: e.g., Dinner, Lunch, Breakfast] - Generate this type of meal for all recipes.
Maximum Total Time: [USER_INPUT: User's absolute maximum time in minutes, e.g., 30 min] - The buffered total time for EACH recipe must respect this limit.
Budget Consideration: [USER_INPUT: e.g., Low, Medium, High] - Guide ingredient choices accordingly for all recipes.
Suitability/Effort Level: [USER_INPUT: e.g., Quick weekday meal, Weekend project, Suitable for frequent weekly prep] - Influence recipe complexity (must align with strict time limits) for all recipes.
Meal to Avoid: [USER_INPUT: Meal type or specific dish to avoid, e.g., Pasta, Curry] - Absolutely exclude for all recipes.
Maximum % of Recipes with Meat/Fish (if diet allows): [USER_INPUT: A number from 0 to 100. Only relevant if Dietary Preferences allows meat/fish. e.g., 60]
5. Recipe Generation Process (Internal MyChef Logic)

Validate time constraints first: For each of the [USER_INPUT: Number of Recipes] recipes, check if realistic prep <= 10 mins and realistic cook <= 20 mins. If this check fails for any potential recipe, terminate and inform the user.
Prioritize Constraints: For each recipe, address Allergens ([USER_INPUT: Allergy Constraints]), Disliked Ingredients ([USER_INPUT: Disliked Ingredients]), and Meat/Fish ([USER_INPUT: Dietary Preferences]) first. Select ingredients accordingly.
Determine Meat/Fish Inclusion: Based on [USER_INPUT: Dietary Preferences] and [USER_INPUT: Maximum % of Recipes with Meat/Fish (if diet allows)], decide for each of the [USER_INPUT: Number of Recipes] recipes whether it will include meat/fish, ensuring variety among the set and contributing to the overall percentage goal.
Select Ingredients: For each recipe, choose ingredients fitting [USER_INPUT: Dietary Preferences], [USER_INPUT: Seasonal/Regional Focus], and [USER_INPUT: Budget Consideration]. Ensure variety from all previously generated recipes and other recipes in this set.
Integrate Technique: Build each recipe around [USER_INPUT: Cooking Technique Focus].
Develop Recipes: Create [USER_INPUT: Number of Recipes] clear, achievable recipes for [USER_INPUT: Household Composition] and [USER_INPUT: Suitability/Effort Level], ensuring substantial variety among them.
Calculate Buffered Time: For each recipe, add buffer to realistic total time. Check if buffered total time <= [USER_INPUT: Maximum Total Time]. If this check fails for any recipe, terminate and inform the user.
Adapt for Household: For each recipe, adjust yield and add Kid-Friendly Adaptation tip if relevant for [USER_INPUT: Household Composition].
Set Meat/Fish Flag: For each completed recipe concept, accurately determine if it contains meat or fish and note the is_meat_or_fish value ('yes' or 'no').
Format Output: Generate the response following the external OpenAPI schema, including all [USER_INPUT: Number of Recipes] recipes and their corresponding is_meat_or_fish flags.
6. Output Formatting (Referencing OpenAPI Schema)
The output structure for multiple recipes, including fields for Recipe Title, MyChef's Note, Yield, Prep time, Cook time, Total time, Ingredients list, Equipment list, Instructions, MyChef's Tips & Variations (including Kid-Friendly, Serving Suggestion, Variations, and Allergen Safety Note), Allergens, and the is_meat_or_fish parameter for EACH generated recipe, is defined by the external OpenAPI documentation. Generate the response precisely following that defined structure, containing exactly [USER_INPUT: Number of Recipes] distinct recipe objects, with the is_meat_or_fish flag accurately set for each.

7. MyChef Maintenance
Maintain the MyChef persona consistently. Acknowledge and be ready to adapt to modified parameters in future requests (number of recipes, diet, time, technique, season, location, meat/fish percentage, etc.). Ensure substantial variation from previous responses and adhere to the user-specified meat/fish inclusion percentage goal over time, accurately categorizing each recipe using the is_meat_or_fish flag."""



################################ GEMINI AI API ################################

def gemini_ai_api(input, temp):
    client = genai.Client(
        api_key=st.secrets["gemini_api_key"],
    )

    model = "gemini-3.8-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=input), # Query to generate meals based on user preferences
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=(temp+1)/10,
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_LOW_AND_ABOVE",  # Block most
            ),
        ],
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.OBJECT,
            required = ["recipes"],
            properties = {
                "recipes": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.OBJECT,
                        required = ["Recipe Title", "MyChef Note", "Yield", "Prep time", "Cook time", "Total time", "Ingredients List", "Equipment", "Instructions", "MyChef Tips", "Allergen Safety Note", "Is Meat Or Fish", "Allergens"],
                        properties = {
                            "Recipe Title": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "MyChef Note": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Yield": genai.types.Schema(
                                type = genai.types.Type.ARRAY,
                                items = genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                            ),
                            "Prep time": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Cook time": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Total time": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Ingredients List": genai.types.Schema(
                                type = genai.types.Type.ARRAY,
                                items = genai.types.Schema(
                                    type = genai.types.Type.OBJECT,
                                    required = ["Quantity", "Unit", "Ingredient Name"],
                                    properties = {
                                        "Quantity": genai.types.Schema(
                                            type = genai.types.Type.INTEGER,
                                        ),
                                        "Unit": genai.types.Schema(
                                            type = genai.types.Type.STRING,
                                        ),
                                        "Ingredient Name": genai.types.Schema(
                                            type = genai.types.Type.STRING,
                                        ),
                                    },
                                ),
                            ),
                            "Equipment": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Instructions": genai.types.Schema(
                                type = genai.types.Type.ARRAY,
                                items = genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                            ),
                            "MyChef Tips": genai.types.Schema(
                                type = genai.types.Type.ARRAY,
                                items = genai.types.Schema(
                                    type = genai.types.Type.OBJECT,
                                    required = ["Kid-Friendly Adaptation", "Serving Suggestion", "Variations"],
                                    properties = {
                                        "Kid-Friendly Adaptation": genai.types.Schema(
                                            type = genai.types.Type.STRING,
                                        ),
                                        "Serving Suggestion": genai.types.Schema(
                                            type = genai.types.Type.STRING,
                                        ),
                                        "Variations": genai.types.Schema(
                                            type = genai.types.Type.STRING,
                                        ),
                                    },
                                ),
                            ),
                            "Allergen Safety Note": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "Is Meat Or Fish": genai.types.Schema(
                                type = genai.types.Type.BOOLEAN,
                            ),
                            "Allergens": genai.types.Schema(
                                type = genai.types.Type.ARRAY,
                                items = genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                            ),
                        },
                    ),
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(text=prompt_instructions), # Returns the prompting file
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    return response.text

