import streamlit as st
from db_insert_functions import pushPreferences, updateCredentials
from authentication import fetch_user_info
import time

ss = st.session_state
sep = ", "
@st.dialog("We'd love to learn more about you!")
def askUserPreferences():
    """"
    This function goal is to prompt new users with their cooking and eating preferences
    to shape generated recipes to their personal habits 
    """
    # Defining options for selectbox and other variables
    cooking_techniques = ("Frying Pan", 
                          "Roasting", 
                          "Baking", 
                          "Boiling", 
                          "Steaming", 
                          "Grilling", 
                          "Slow Cooking")
    diets = ("Vegetarian", 
             "Vegan", 
             "Gluten-Free", 
             "Keto", 
             "Mediterranean", 
             "Pescatarian", 
             "Dairy-Free")
    allergy = ("Cereals containing gluten",
               "Crustaceans", 
               "Eggs", 
               "Fish",
               "Peanuts",
               "Soybeans",
               "Milk",
               "Nuts",
               "Celery",
               "Mustard",
               "Sesame seeds",
               "Sulphites",
               "Lupin",
               "Molluscs")
    cooking_effort_levels = ("Minimal Effort",
                             "Quick & Easy (Weekday Dinner)",
                             "Moderate Effort (Weeknight/Weekend)",
                             "Time-Intensive Project (Weekend Project)")
    disliked_ingredients = ("Olives",
                            "Mushrooms",
                            "Cilantro",
                            "Onions (raw)",
                            "Bell Peppers",
                            "Eggplant",
                            "Tomatoes (raw)",
                            "Mayonnaise",
                            "Pickles",
                            "Spicy Peppers/Chili",
                            "Cabbage",
                            "Seafood (general)",
                            "Blue Cheese",
                            "Licorice",
                            "Liver")

    st.info("Please do not select any if not applicable")
    # Defining questions about preferences
    # st.text("What is your favorite cooking technique:")
    technique = st.multiselect(label="_What is your favorite cooking technique:_", placeholder="Select among this list or add it yourself...", accept_new_options=True, options=cooking_techniques, default=None, key="cookingTechnique")
    # st.html("<br>")
    # st.text("Are you on a diet?")
    diet = st.multiselect(label="_Are you on a diet?_", placeholder="Select among these diets or add your own...",accept_new_options=True, options=diets, default=None, key="diet")
    # st.html("<br>")
    # st.text("Do you have any allergies?")
    allergens = st.multiselect(label="_Do you have any allergies?_", placeholder="Select your allergy or let us know if we missed any...", accept_new_options=True, options=allergy, default=None, key="allergens")
    # st.html("<br>")
    # st.text("Do you have any ingredients dislikes?")
    dislikes = st.multiselect(label="_Do you have any ingredients dislikes?_", placeholder="Select the ingredients you want to absolutely avoid, add whatever you want...", accept_new_options=True, options=disliked_ingredients, default=None, key="dislikes")
    # st.html("<br>")
    # st.text("How much efforts do you want to put in your daily cooking?")
    efforts = st.selectbox(label="_How much efforts do you want to put in your daily cooking?_", placeholder="Select the efforts you want to put in cooking your meals...", options=cooking_effort_levels, index=1, key="cookingEfforts")
    st.html("<br>")
    if st.button("Submit My Preferences", use_container_width=True, type="primary"):
        
        with st.status("Updating your preferences", expanded=False) as status:
            st.info("We are updating your preferences. You can change it anytime, in your profile section")
            if pushPreferences(sep.join(technique), sep.join(diet), sep.join(allergens), sep.join(dislikes), efforts, int(ss.user_instance.user_id)):
                ss.preferences = {
                    "technique": sep.join(technique), "diet": sep.join(diet),
                    "allergy": sep.join(allergens), "dislikes": sep.join(dislikes),
                    "efforts": efforts,
                }
                time.sleep(2)
                status.update(label="Upload completed", state="complete", expanded=False)
                ss.userPref = True
                st.rerun()
            else:
                status.update(label="Failed to upload", state="error", expanded=False)
                st.stop()

@st.dialog("Please update your credentials information:")
def update_dialog(email=None):
    ss_user = st.session_state.user_instance
    if email is None:
        email = ss_user.email
    # Defining gender dictionnary for user informations
    gender_dict = {
        "Male": "M",
        "Female": "F",
        "Don't Specify": "/"
    }
    # Sarting dialog form
    st.write("Update your personal informations here below.")

    # Prompting user for information
    firstname = st.text_input("Update your firstname:", placeholder="Firstname", value=ss_user.firstName)
    lastname = st.text_input("Update your lastname:", placeholder="Lastname", value=ss_user.lastName)
    username = st.text_input("Update your username:", placeholder="Username", value=ss_user.userName)
    birthdate = st.date_input("Update your birthdate:", value=ss_user.birthdate, min_value="1900-01-01")
    gender_choice = st.radio("What gender are you?",["Male", "Female", "Don't Specify"])
    sex = gender_dict[gender_choice]
    if st.button("Update", use_container_width=True):
        if not firstname or not lastname or not birthdate or not sex:
            st.warning("One of the information has not been filled.")
        else:
            if updateCredentials(firstname=firstname, lastname=lastname, age=birthdate, username=username):
                # Useless design for database communication waiting time
                progress_text = "Updating your credentials..."
                my_bar = st.progress(0, text=progress_text)
                for percent_complete in range(0,100):
                    my_bar.progress(percent_complete+1, text=progress_text)
                    time.sleep(0.02)
                time.sleep(1)
                my_bar.empty
                st.success("Updated successfully!")
                # Fetching user info on db
                if fetch_user_info(email=email):
                    st.session_state["authenticated"] = True
                    st.session_state["email"] = email
                    st.rerun()
                else:
                    st.error("Failed to fetch user information after registration. Please try logging in manually.")
            else:
                st.error("Update failed. Please try again or contact support.")
