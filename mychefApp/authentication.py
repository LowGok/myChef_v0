import streamlit as st
import bcrypt
from sqlalchemy.sql import text
import time
from db_fetch_functions import fetch_recipes_ingredients, fetch_user_recipes
from connection import init_connection
ss = st.session_state 

######################## USER DATA ########################

# Defining user class for session state variable
class User:
    def __init__(self, user_id, firstName, lastName, sex, birthdate, email, userName, lastMeal=None, hasPref=False):
        self.user_id = user_id
        self.firstName = firstName
        self.lastName = lastName
        self.sex = sex
        self.birthdate = birthdate
        self.email = email
        self.userName = userName
        self.lastMeal = lastMeal
        self.hasPref = hasPref

def fetch_user_info(email):
    """Fetch user information in the database to enrich 
    st.session_state.user_instance with the User class"""
    if email:
        fetching_query = ("""
            SELECT 
                user_id, 
                firstname, 
                lastname, 
                sex, 
                birthdate, 
                email, 
                username, 
                allergens, 
                diet, 
                dislikes, 
                lastmeal, 
                haspref, 
                cooking_technique, 
                cooking_efforts 
            FROM 
                users 
            WHERE 
                email = :email
        """)
        # Establishing connection with database
        conn = init_connection()
        try:
            user_db = conn.query(fetching_query, params={"email": email}, show_spinner=False, ttl=0)
            if not user_db.empty:
                st.session_state.user_instance = User(
                    user_id=user_db["user_id"].iloc[0],
                    firstName=user_db["firstname"].iloc[0], 
                    lastName=user_db['lastname'].iloc[0],
                    sex=user_db['sex'].iloc[0],
                    birthdate=user_db['birthdate'].iloc[0],
                    email=user_db['email'].iloc[0],
                    userName=user_db['username'].iloc[0],
                    lastMeal=user_db["lastmeal"].iloc[0],
                    hasPref=user_db['haspref'].iloc[0]
                )
                st.session_state.preferences = {
                    "technique" : user_db["cooking_technique"].iloc[0],
                    "diet" : user_db["diet"].iloc[0],
                    "allergy" : user_db["allergens"].iloc[0],
                    "dislikes" : user_db["dislikes"].iloc[0],
                    "efforts" : user_db["cooking_efforts"].iloc[0]
                }
                return True
            else:
                st.error("User not found in the database")
                return False
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return False
    else:
        st.error("Email not found. Contact us at admin@gkldevelopment.com")
        return False

######################## AUTHENTICATION & REGISTRATION ########################

# Authentication logic below - To be changed with SSO authentication

# Password hashing
def hash_password(password):
    """Hashing the password for db storage"""
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')

# Credential verification for user authentication
def credentials(email, password):
    """Verifying users credentials for authentication"""
    if not email or not password:
        return False
    if len(password.encode("utf-8")) > 72:
        return False
    verification_query = ("""
        SELECT password FROM users WHERE email = :email
    """)
    # Establishing connection with database
    conn = init_connection()
    try:
        user_pwd = conn.query(verification_query, params={"email": email}, ttl=5, show_spinner=False)
        # Check if the query is not empty
        if not user_pwd.empty: 
            return bcrypt.checkpw(password.encode("utf-8"), user_pwd["password"].iloc[0].encode("utf-8"))
        else:
            # Email or Username not found
            return False 
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()

# Registration protocol
def registration_protocol(email, password, firstname, lastname, sex, birthdate, username, hasmeal=False):
    """Registration protocol for user inscription in database"""
    if not email or not password:
        return False
    if len(password.encode("utf-8")) > 72:
        st.warning("Passwords must be at most 72 UTF-8 bytes. Choose a shorter password.")
        return False
    usr_variable_dict = {
        "email": email,
        "password": hash_password(password=password),
        "firstname": firstname,
        "lastname": lastname,
        "sex": sex,
        "birthdate": birthdate,
        "hasmeal": hasmeal,
        "username": username
    }
    registration_query = ("""
        INSERT INTO users(
        user_id,
        firstname,
        lastname,
        sex,
        birthdate,
        email,
        password,
        username,
        allergens,
        diet,
        dislikes,
        lastmeal,
        cooking_efforts,
        cooking_technique,
        haspref
        )
        VALUES (
        DEFAULT,
        :firstname,
        :lastname,
        :sex,
        :birthdate,
        :email,
        :password,
        :username,
        NULL,
        NULL,
        NULL,
        '1970-01-01',
        NULL,
        NULL,
        NULL
        )
    """)
    conn = init_connection()
    with conn.session as s:
        try:
            s.execute(text(registration_query), usr_variable_dict)
            s.commit()
        except Exception as e:
            st.error(f"Invalid credentials provided... Please try again or contact us. {e}")
            st.stop()
    return True

@st.dialog("Please complete credentials information:")
def registration_dialog(email, password):
    # Defining gender dictionnary for user informations
    gender_dict = {
        "Male": "M",
        "Female": "F",
        "Don't Specify": "/"
    }
    # Sarting dialog form
    st.write("Thank you for signing up! " \
    "We want to get to know you a bit more before you can access the app.")

    # Prompting user for information
    firstname = st.text_input("What is your firstname?", placeholder="Firstname")
    lastname = st.text_input("What is your lastname?", placeholder="Lastname")
    username = st.text_input("Enter a username:", placeholder="Username")
    birthdate = st.date_input("When's your birthdate?", value=None, min_value="1900-01-01")
    gender_choice = st.radio("What gender are you?",["Male", "Female", "Don't Specify"])
    sex = gender_dict[gender_choice]
    if st.button("Submit", use_container_width=True):
        if not firstname or not lastname or not birthdate or not sex:
            st.warning("One of the information has not been filled.")
        else:
            if registration_protocol(email=email, password=password, firstname=firstname, lastname=lastname, birthdate=birthdate, sex=sex, username=username):
                # Useless design for database communication waiting time
                progress_text = "Registration in progress..."
                my_bar = st.progress(0, text=progress_text)
                for percent_complete in range(0,100):
                    my_bar.progress(percent_complete+1, text=progress_text)
                    time.sleep(0.02)
                time.sleep(1)
                my_bar.empty
                st.success("Registered successfully!")
                # Fetching user info on db
                if fetch_user_info(email=email):
                    st.session_state["authenticated"] = True
                    st.session_state["email"] = email
                    st.rerun()
                else:
                    st.error("Failed to fetch user information after registration. Please try logging in manually.")
            else:
                st.error("Registration failed. Please try again or contact support.")

# Registration function for visual form and onboarding
def register():
    """User are going to be onboarded through this function and the information are pushed to the database through registration protocol"""
    # with st.("Not registered yet? Create an account now!"):
    # st.subheader("Not registered yet? Create an account now!")
    with st.form("Register", enter_to_submit=True):
        email = st.text_input(label="Enter your email:", type="default", placeholder="Enter your email").lower()
        password = st.text_input(label="Enter your password:", type="password", placeholder="Enter your password")
        confirm_pwd = st.text_input(label="Confirm your password:", type="password", placeholder="Confirm your password")
        if st.form_submit_button("Register now!", use_container_width=True):    
            if len(password.encode("utf-8")) > 72:
                st.warning("Passwords must be at most 72 UTF-8 bytes. Choose a shorter password.")
            elif password == confirm_pwd:
                registration_dialog(email=email, password=password)
            else:
                st.warning("Passwords must match! Please check if there is no typos.")

# Authentication function for login
def authenticate():
    """User are being signed in after credential verification protocol with database user informations"""
    with st.form("Login", enter_to_submit=True):
        email = st.text_input(label="Enter your email:", type="default", placeholder="Enter your email").lower()
        password = st.text_input(label="Enter your password:", type="password", placeholder="Enter your password")
        if st.form_submit_button("Login", use_container_width=True):
            if credentials(email=email, password=password):
                # Useless design for database communication waiting time
                progress_text = "Registration in progress..."
                my_bar = st.progress(0, text=progress_text)
                my_bar.progress(0, text=progress_text)
                time.sleep(0.01)
                my_bar.progress(30, text=progress_text)
                time.sleep(0.01)
                my_bar.progress(70, text=progress_text)
                time.sleep(0.01)
                my_bar.progress(100, text=progress_text)
                time.sleep(1)
                my_bar.empty
                st.success("Logged in successfully!")
                # Fetching user info on db
                if fetch_user_info(email=email):
                    st.session_state["authenticated"] = True
                    st.session_state["email"] = email
                    st.rerun()
                else:
                    st.error("Failed to fetch user information after registration. Please try logging in manually.")
            else: 
                st.error("Invalid email or password...")

def logout():
    # Delete all the items in Session state
    for key in st.session_state.keys():
        del st.session_state[key]
    fetch_user_recipes.clear()
    fetch_recipes_ingredients.clear()
    return True
