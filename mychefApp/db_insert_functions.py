import streamlit as st
from sqlalchemy.sql import text
import pandas as pd
from datetime import date
from connection import init_connection, with_db_retry

@with_db_retry(max_retries=3)
def databaseRecipesStorage(recipesData, userId=1):
    """The function takes recipesData already JSON parsed 
    and deconstructs it to store it in the database"""
    if userId and recipesData:
        # Insert SQL scripts
        insert_sql = """
        INSERT INTO meals (
            creator_id,
            meal_id,
            creationDate,
            recipeTitle,
            yield,
            prepTime,
            cookTime,
            myChefNotes,
            equipment,
            instructions,
            allergens,
            allergensSafetyNote,
            isMeatOrFish,
            totalTime
        ) VALUES (
            :creator_id,
            :meal_id,
            :creationDate,
            :recipeTitle,
            :yield,
            :prepTime,
            :cookTime,
            :myChefNotes,
            :equipment,
            :instructions,
            :allergens,
            :allergensSafetyNote,
            :isMeatOrFish,
            :totalTime
        );
        """
        
        recipes = recipesData.get('recipes', [])

        # Defining date in int for meal_id
        today = date.today()
        str_date = today.strftime("%Y%m%d")
        meal_id_dict = {}
        
        # Establishing connection with database
        conn = init_connection()
        with conn.session as s:
            for i, recipe in enumerate(recipes):
                meal_id = int(str_date + str(i) + str(userId))
                meal_data = {
                    "creator_id": userId,
                    "meal_id": meal_id,
                    "creationDate": today,
                    "recipeTitle": recipe.get("Recipe Title"),
                    "yield": recipe.get("Yield"), 
                    "prepTime": recipe.get("Prep time"),
                    "cookTime": recipe.get("Cook time"),
                    "myChefNotes": recipe.get("MyChef Note"),
                    "equipment": recipe.get("Equipment"),
                    "instructions": recipe.get("Instructions"),
                    "allergens": recipe.get("Allergens", []),
                    "allergensSafetyNote": recipe.get("Allergen Safety Note"),
                    "isMeatOrFish": recipe.get("Is Meat Or Fish"),
                    "totalTime": recipe.get("Total time")
                }
                meal_id_dict[recipe.get("Recipe Title")] = meal_id
                s.execute(text(insert_sql), meal_data)
                s.execute(text("UPDATE users SET lastmeal = :today WHERE user_id = :user_id"), {"user_id": userId, "today": today})
            s.commit()
        return meal_id_dict
    else:
        st.error("Database meal storage error. Contact admin@gkldevelopment.com or try again.")
        return None

@with_db_retry(max_retries=3)
def databaseIngredientsStorage(recipesData, meal_id_dict, userId=1):
    """The function takes recipesData already JSON parsed 
    and deconstructs it to store it in the database"""
    if userId and recipesData and meal_id_dict:
        insert_sql = """
        INSERT INTO ingredients (
            pk_ingredients,
            recipe_id,
            quantity,
            unit,
            ingredient_name,
            date            
        ) VALUES (
            DEFAULT,
            :recipe_id,
            :quantity,
            :unit,
            :ingredient_name,
            :date
        );
        """
        
        recipes = recipesData.get('recipes', [])
        today = date.today()
        
        conn = init_connection()
        with conn.session as s:
            ingredients_df = pd.json_normalize(
                recipes,
                record_path='Ingredients List',
                meta=['Recipe Title'],
                sep='.',
                errors='ignore'
            )
            ingredients_df = ingredients_df.rename(columns={
                'Quantity': 'quantity',
                'Unit': 'unit',
                'Ingredient Name': 'ingredient_name'
            })
            ingredients_df['date'] = today
            ingredients_df['recipe_id'] = ingredients_df['Recipe Title'].map(meal_id_dict)
            records_to_insert = ingredients_df[[
                'recipe_id',
                'quantity',
                'unit',
                'ingredient_name',
                'date'
            ]].to_dict(orient='records')
            s.execute(text(insert_sql), records_to_insert)
            s.commit()
            return True
    else:
        st.error("Database meal storage error. Contact admin@gkldevelopment.com or try again.")
        return False

@with_db_retry(max_retries=3)
def updateCredentials(firstname=None, lastname=None, age=None, username=None, userId=None):
    """
    Pushing preferences into user table with dynamic session_state fallback.
    """
    user = getattr(st.session_state, "user_instance", None)
    if userId is None and user:
        userId = getattr(user, "user_id", None)
    if firstname is None and user:
        firstname = getattr(user, "firstName", None)
    if lastname is None and user:
        lastname = getattr(user, "lastName", None)
    if age is None and user:
        age = getattr(user, "birthdate", None)
    if username is None and user:
        username = getattr(user, "userName", None)

    if firstname and lastname and age and userId:
        variables_dict = {
            "firstname": firstname,
            "lastname": lastname,
            "age": age,
            "username": username,
            "user_id": int(userId)
        }

        preferencesQuery = """
            UPDATE users
            SET
                firstname = :firstname,
                lastname = :lastname,
                birthdate = :age,
                username = :username
            WHERE 
                user_id = :user_id
        """
        conn = init_connection()
        with conn.session as s:
            s.execute(text(preferencesQuery), params=variables_dict)
            s.commit()
            return True
    else:
        st.error("Invalid UserId or credentials, please contact us: admin@gkldevelopment.com")
        return False

@with_db_retry(max_retries=3)
def pushPreferences(technique, diet, allergens, dislikes, efforts, userId):
    """
    Pushing preferences into user table.
    """
    if userId:
        variables_dict = {
            "allergens": allergens,
            "diet": diet,
            "dislikes": dislikes,
            "cooking_efforts": efforts,
            "cooking_technique": technique,
            "user_id": userId
        }

        preferencesQuery = """
            UPDATE users
            SET
                allergens = :allergens,
                diet = :diet,
                dislikes = :dislikes,
                cooking_efforts = :cooking_efforts,
                cooking_technique = :cooking_technique,
                haspref = 'True'
            WHERE 
                user_id = :user_id
        """
        conn = init_connection()
        with conn.session as s:
            s.execute(text(preferencesQuery), params=variables_dict)
            s.commit()
            return True
    else:
        st.error("Invalid UserId, please contact us: admin@gkldevelopment.com")
        return False

@with_db_retry(max_retries=3)
def databaseImageStorage(cloudinary_pub_id, image_url, meal_id, user_id=None):
    """
    Stores the image (public ID, and URL) in the Neon database with dynamic user_id fallback.
    """
    if user_id is None:
        user = getattr(st.session_state, "user_instance", None)
        user_id = getattr(user, "user_id", None) if user else None

    if cloudinary_pub_id and image_url and meal_id and user_id:
        variables_dict = {
            "recipeimg": image_url,
            "cloudinary_public_id": cloudinary_pub_id,
            "meal_id": meal_id,
            "user_id": int(user_id)
        }

        push_query = """
            UPDATE meals 
            SET
                recipeimg = :recipeimg,
                cloudinary_public_id = :cloudinary_public_id
            WHERE 1=1
                AND meal_id = :meal_id
                AND creator_id = :user_id;
        """
        conn = init_connection()
        with conn.session as s:
            s.execute(text(push_query), params=variables_dict)
            s.commit()
            return True
    else:
        st.error("Invalid UserId, please contact us: admin@gkldevelopment.com")
        return False
