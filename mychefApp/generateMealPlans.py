import streamlit as st
import time, json
from recipeGenerator import gemini_ai_api
from imageGenerator import imageGenerator, uploadImageToCloud
from db_insert_functions import databaseRecipesStorage, databaseIngredientsStorage, databaseImageStorage
from authentication import fetch_user_info
from connection import configure_cloudinary
from google.genai.errors import APIError
from generationTrace import record_stage
from db_fetch_functions import fetch_user_recipes, fetch_recipes_ingredients

############################## GENERATE MEAL PLAN ##############################

"""This file goal is only to define a function that generate meals for the week"""

@st.dialog("Tell MyChef about your preferences")
def selectMealPref():
    st.info("Your diet, allergens and dislikes preferences will be taken into account during the meal generation.")
    
    # Implement meal days storage in db to render meal cards with correct meals
    days_options = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days = st.pills("Number of meals:", options=days_options, selection_mode='multi', key="days")

    # User to select total time for meal prep
    time_options = ['10 min', '20 min', '30 min', '40 min', '50 min', '1 hour']
    total_time = st.pills("How much time will you spend prepping and cooking each meal?",options=time_options, selection_mode='single', key="tot_time")

    # User to select household composition for meal planning yield
    count_options = [1, 2, 3, 4, 5]
    adults = st.pills("How many adults are you cooking for?", options=count_options, selection_mode='single', key="adults")
    childs = st.pills("How many childrens are you cooking for?", options=count_options, selection_mode='single', key="childs")

    # User to select budget for meals
    budget_options = ['Low', 'Medium', 'High']
    budget = st.pills("Budget for your meal:", options=budget_options, selection_mode='single', key="budget")

    # User to select MyChef creativity
    creativity = st.slider("Handle MyChef creativity:", 0, 10, 8)

    # Submitting preferences 
    if st.button("Generate Now!", use_container_width=True, type='primary'):
        st.session_state["mealPreferences"] = {
            "days": days,
            "total_time": total_time,
            "adults": adults,
            "childs": childs,
            "budget": budget,
            "creativity": creativity
            }
        st.rerun()

def generateImage(meal_id, ingredient_list, meal_title=None):
    """
    Orchestrates the entire process of image generation: generate, upload, store link.
    """
    configure_cloudinary()
    record_stage("image_requested", meal_id=int(meal_id))
    
    image_data = imageGenerator(meal=meal_title or "prepared meal", ingredient_list=ingredient_list)
    # Corrected check for image generation failure
    if image_data is False:
        st.warning("The meal image is unavailable. Your saved recipe will use a placeholder.")
        print("Workflow failed: Image generation failed.")
        return None
    record_stage("image_received", bytes=len(image_data))
    cloudinary_response = uploadImageToCloud(image_data)
    if cloudinary_response is None:
        print("Workflow failed: Cloudinary upload failed.")
        return None
    cloudinary_public_id = cloudinary_response.get("public_id")
    image_link = cloudinary_response.get("secure_url")
    if not image_link or not cloudinary_public_id:
        print("Workflow failed: Missing public ID or secure URL from Cloudinary.")
        return None
    record_stage("image_uploaded")
    db_record_id = databaseImageStorage(cloudinary_pub_id=cloudinary_public_id, image_url=image_link, meal_id=meal_id)
    if not db_record_id:
        print("Workflow failed: Storing in Neon DB failed.")
        return None
    record_stage("image_saved", meal_id=int(meal_id))
    return True
    
def generateMealPlan(userId):
    """
    Pipeline for the full meal planning generation process. 
    Handles AI generation tasks, database insertions and session_state updating.
    """
    user = int(userId)
    ss = st.session_state
    # Consume one explicit request so reruns cannot silently regenerate paid output.
    ssp = ss.pop("mealPreferences")
    # Crafting prompt
    prompt_text = f"""
    Number of recipes: {7 if len(ssp["days"]) == 0 else len(ssp["days"])}
    Cooking technique focus: {ss.preferences['technique']}
    Dietary preferences: {ss.preferences['diet']}
    Allergy Constraints: {ss.preferences['allergy']}
    Disliked Ingredients: {ss.preferences['dislikes']}
    Seasonal/Regional Focus: Mid-autumn in Europe.
    Household Composition: {ssp["adults"]} adults, {ssp["childs"] if ssp["childs"] is not None else 0} child
    Meal Type: Dinner
    Maximum Total Time: {ssp["total_time"]}.
    Budget Consideration: {ssp["budget"]}.
    Suitability/Effort Level: {ss.preferences['efforts']}
    Meal to Avoid: None
    Maximum % of Recipes with Meat/Fish: 40"""

    try:
        # Generating meals from Gemini API 
        with st.status("MyChef is cooking!", expanded=False) as status:
            # Instanciating the prompting and meal generation process
            st.write("Providing informations to MyChef...")
            time.sleep(2)
            
            # Prompting MyChef
            st.write("Generating your meal plan...")
            structured_output = gemini_ai_api(prompt_text, ssp["creativity"])
            
            # Extracting the output as a Python dictionnary
            st.write("Saving your meals...")
            if structured_output:
                recipesData = json.loads(structured_output)
            else:
                st.error("Failed to generate meal plan. " \
                "An issue might be going on our side. " \
                "Please try again in a couple hours or contact us: admin@gkldevelopment.com.")
                status.update(label="Failed to generate meal plan. Please try again", state="error", expanded=False)
                st.stop()
            # Saving shopping list
            mealId = databaseRecipesStorage(recipesData=recipesData, userId=user)
            if mealId:
                record_stage("recipes_saved", count=len(mealId), meal_ids=list(mealId.values()))
                st.write("Crafting your shopping list...")
            else:
                status.update(label="Failed to save your meal plan. Please try again", state="error", expanded=False)
                st.stop()

            # Uploading Ingredients to DB
            ingredients_uploaded = databaseIngredientsStorage(recipesData=recipesData, meal_id_dict=mealId, userId=user)
            if ingredients_uploaded:    
                record_stage("ingredients_saved")
                fetch_user_recipes.clear()
                fetch_recipes_ingredients.clear()
                st.write("Generating meals images...")
            else:
                status.update(label="Failed to save your ingredients. Please try again", state="error", expanded=False)
                st.stop()
            # # Add these lines to debug
            # print("--- Debugging Data ---")
            # print("mealId Dictionary:", mealId)
            # print("recipesData List:", recipesData['recipes'][0]["Recipe Title"])
            # print("----------------------")
            # Generating Meals Images
            recipesList = recipesData['recipes']
            image_failures = 0
            for index in range(len(recipesList)):
                try:
                    recipeId = mealId[recipesList[index]["Recipe Title"]]
                    recipeIngredients = recipesList[index]["Ingredients List"]
                    # Check if the ingredients list is not empty
                    if not recipeIngredients:
                        print(f"Skipping image generation for meal ID: {recipeId} - No ingredients found.")
                        continue # Move to the next recipe
                    # Convert the list of ingredients to a string
                    ingredientsList = ", ".join(item["Ingredient Name"] for item in recipeIngredients if "Ingredient Name" in item)
                    # Ensure the list is not empty after filtering
                    if not ingredientsList:
                        print(f"Skipping image generation for meal ID: {recipeId} - No valid ingredient names found.")
                        continue
                    print(f"Generating image for meal ID: {recipeId} with ingredients: {ingredientsList}")
                    # Call the image generation function
                    image_generation_success = generateImage(meal_id=recipeId, ingredient_list=ingredientsList,
                                                            meal_title=recipesList[index]["Recipe Title"])
                    # Check if image generation failed
                    if not image_generation_success:
                        image_failures += 1
                        record_stage("image_unavailable", reason="save_or_upload_failed")
                except KeyError as e:
                    image_failures += 1
                    record_stage("image_unavailable", reason="invalid_recipe_data")
                except APIError as e:
                    image_failures += 1
                    record_stage("image_unavailable", status_code=e.code)
                except Exception as e:
                    image_failures += 1
                    record_stage("image_unavailable", error_type=type(e).__name__)
            if image_failures:
                ss["image_generation_notice"] = "Your meals and ingredients are saved. Images are unavailable; placeholders are shown."
            else:
                ss.pop("image_generation_notice", None)
            del ss.user_instance
            if fetch_user_info(email=ss["email"]):
                record_stage("menu_complete")
                status.update(label="Meal plan generated!", state="complete", expanded=False)
            else:
                status.update(label="Failed to generate and upload your images. Please try again", state="error", expanded=False)
                st.stop()
        st.success("Your weekly meal plan will be displayed shortly.")
        time.sleep(2)
        st.rerun()
    except APIError as e:
        if e.code == 429:
            st.error("Gemini's quota is exhausted. Wait for the quota to reset or configure a key with available quota.")
        else:
            st.error(f"Gemini could not generate the meal plan (HTTP {e.code}). Please try again later.")
        st.stop()
    except Exception as e:
        st.error("We couldn't generate your meal. Please try again or contact us: admin@gkldevelopment.com")
        # st.warning(f"Failed because of: {e}") | ONLY FOR DEBUG PURPOSES
        print(f"Meal generation failed: {type(e).__name__}")
        st.stop()

