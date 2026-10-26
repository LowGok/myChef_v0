import streamlit as st
from datetime import date
from db_fetch_functions import fetch_user_recipes, fetch_recipes_ingredients
import math

################################## Variable, classes and functions ########################################

ss = st.session_state

def instructions(col):
    today = date.today()
    weeklyPlan, _ = fetch_user_recipes(ss.user_instance.user_id, today)
    mealPlan = weeklyPlan[int(col)]
    instructions = list(mealPlan['instructions'].strip('{}""').split('","'))
    equipments = mealPlan['equipment']
    ingredients = fetch_recipes_ingredients(ss.user_instance.user_id, ss.recipesId)
    recipe_ingredients = ingredients[ingredients['recipe_id'] == int(mealPlan['meal_id'])]
    if st.button("‹ Back To Meal Cards", type="tertiary"):
        ss.selected_meal = None
        st.rerun()
    st.subheader(mealPlan['recipetitle'])
    if mealPlan['recipeimg']:
        st.image(mealPlan['recipeimg'], caption=mealPlan['mychefnotes'], use_container_width=True, width=300)
    else:
        st.image('./img/weeklyMealImg/placeholder.jpg', caption=mealPlan['mychefnotes'], use_container_width=True, width=300)
    ##### Simplifying the markdown string due to error of unterminated f-string #####
    allergens_str = mealPlan.get('allergens', '').strip('{}"') 
    if not allergens_str or 'none' in allergens_str.lower():
        allergen_badge = ":green-badge[:material/check: Allergen Free]"
    else:
        first_allergen = allergens_str.split()[0].capitalize()
        allergen_badge = f":orange-badge[⚠️{first_allergen}]"
    time_str = mealPlan.get('totaltime', 'N/A').split(" (")[0]
    time_badge = f":blue-badge[🕒 Ready in {time_str}]"
    st.markdown(f"{allergen_badge} {time_badge}")
    ing, rec = st.tabs(["Ingredients", "Instructions"])
    with ing:
        st.html("<h2>Requirements & Ingredients:</h2>")
        st.write(f"For this recipe you will need a ***{equipments.lower()}***")
        st.write(recipe_ingredients.drop("recipe_id", axis=1))
        # for i in range(len(recipe_ingredients)):
        #     # Formatizing ingredients display in shopping list
        #     if recipe_ingredients['unit'].iloc[i] in ("tablespoon", "tablespoons", "teaspoon", "teaspoons", "cup", "cups"):
        #         ingredient = recipe_ingredients['ingredient_name'].iloc[i]#.split(", ")[0]
        #     elif recipe_ingredients['quantity'].iloc[i] != 0:
        #         ingredient = str(int(recipe_ingredients['quantity'].iloc[i])) + " " + recipe_ingredients['unit'].iloc[i] + " " + recipe_ingredients['ingredient_name'].iloc[i]#.split(", ")[0]
        #     else: 
        #         ingredient = recipe_ingredients['unit'].iloc[i] + " " + recipe_ingredients['ingredient_name'].iloc[i]#.split(", ")[0]
        #     # Returning ingredient
        #     st.write(f"- {str(ingredient).capitalize()}")
    with rec:
        st.html("<h2>Instructions:</h2>")
        for index, instruction in enumerate(instructions, 1):
            st.write(f"{index}. {instruction}")


# @st.cache_data(max_entries=200)
def mealCards():
    # Defining weekdays for column generation
    weekDays = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }
    today = date.today()           
    # Fetching meal plan recipes
    weeklyPlan, recipesId = fetch_user_recipes(ss.user_instance.user_id, today)
    ss["recipesId"] = recipesId 
    # Starting columns generation
    numberOfRecipes = len(weeklyPlan) # Defines the number of recipes for the column generation
    max_columns = 2 # Defining the max recipes columns per row 
    num_of_row = math.ceil(numberOfRecipes / max_columns) # Calculating row needed
    current_col = 0 # Set the current col number for weeklyPlan dict parsing
    # Defining page header
    st.subheader('Your Weekly Meals!')
    st.text(f'Never miss a meal with our highly personnalized planner and enjoy cooking seasonal ingredients with your own style!')
    st.html("<br>")
    for row in range(num_of_row):
        # Calculates the number of columns needed to fill the current row // It will take max_columns if there are more than 3 to be processed
        column_in_row = min(max_columns, numberOfRecipes - current_col)
        if column_in_row > 0: # Creates a new row only if they are still columns to be processed
            cols = st.columns(column_in_row, vertical_alignment='top')
            for i in range(column_in_row):
                with cols[i]:
                    row = current_col
                    st.subheader(weekDays.get(current_col, f"Meal {current_col + 1}"))
                    if weeklyPlan[current_col]["recipeimg"]:
                        st.image(image=weeklyPlan[current_col]["recipeimg"], caption=weeklyPlan[current_col]['recipetitle'].ljust(65-len(weeklyPlan[current_col]['recipetitle'])), use_container_width=True, width=300)
                    else:
                        st.image('./img/weeklyMealImg/placeholder.jpg', caption=weeklyPlan[current_col]['recipetitle'].ljust(65-len(weeklyPlan[current_col]['recipetitle'])), use_container_width=True, width=300)
                                        
                    ##### Simplifying the markdown string due to error of unterminated f-string #####
                    allergens_str = weeklyPlan[current_col].get('allergens', '').strip('{}"') 
                    if not allergens_str or 'none' in allergens_str.lower():
                        allergen_badge = ":green-badge[:material/check: Allergen Free]"
                    else:
                        first_allergen = allergens_str.split()[0].capitalize()
                        allergen_badge = f":orange-badge[⚠️{first_allergen}]"
                    time_str = weeklyPlan[current_col].get('totaltime', 'N/A').split(" (")[0]
                    time_badge = f":blue-badge[🕒 Ready in {time_str}]"
                    st.markdown(f"{allergen_badge} {time_badge}")

                    recipe_details = st.button("Cook Now!", key=weeklyPlan[current_col]['meal_id'], use_container_width=True, type="primary")
                    if recipe_details:
                        ss.selected_meal = str(row)
                        st.rerun()
                        # st.warning("Not functional yet. Try again later.")
                    feedback = st.feedback(options="thumbs", key=f"{weeklyPlan[current_col]['meal_id']}_feedback")
                current_col += 1
