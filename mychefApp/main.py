import streamlit as st

# Set page config an SEO optimization
st.set_page_config(
    page_title="MyChef: Meal Planner", 
    page_icon="https://res.cloudinary.com/dmg7zxlwr/image/upload/w_1000,c_fill,ar_1:1,g_auto,r_max,bo_5px_solid_red,b_rgb:262c35/v1743927852/MyChef_C_icon_i7vknk.png",
    layout="centered",
    menu_items={
        "Get Help": 'https://github.com/GKL-Development/myChef_v0',
        "Report a bug": "mailto:admin@gkldevelopment.com",
        "About": "MyChef v0.1 \n\n https://github.com/GKL-Development/myChef_v0 \n\n Copyright 2025 GKL-Development. All rights reserved \n\n __________________________________"
    })

import time # For demonstration of re-run pause
from authentication import authenticate, register, logout

ss = st.session_state

# Logo image
st.logo("./img/logo/row_no_sentence.png", size = "large")

# Assign authentication and email session state to correct value for authentication
if "authenticated" not in ss:
    ss["authenticated"] = False
    ss["email"] = None

# Browser cookies are user-controlled and cannot establish an authenticated session.
# A new Streamlit session must verify credentials until server-validated tokens exist.

if ss["authenticated"]:
    if "user_instance" not in ss:
        ss["authenticated"] = False
        ss["email"] = None
        st.error("Database connection failed. Try login again or contact support at admin@gkldevelopment.com")
        st.rerun() # Rerun to show login form
    if st.sidebar.button("Be an early adopter!", use_container_width=True): # To be replaced by st.sidebar.link_button("Check our crowdfunding!", use_container_width=True, url=""): // and remove warning
        st.sidebar.warning("Not yet live. Come back in a couple of days!")
    if st.sidebar.button("Logout", use_container_width=True, type="primary", key="logout"):
        if logout():
            st.sidebar.success("You have been logged out.")
            time.sleep(1)
            st.rerun() 
        else:
            st.sidebar.error("Failed to log you out. Please try again.")
        # Rerun to show login form
    # st.sidebar.divider()
    # st.sidebar.markdown("<i>MyChef© by GKL Development</i>", unsafe_allow_html=True)
    # Defining navigation
    pages = {
        "MyChef":[
            st.Page(
                "dashboard.py",
                title='Meals',
                icon="🏠",
                default=True
            ),
            st.Page(
                "shoppingList.py",
                title='Shopping List',
                icon="🗒️"
            ),
            st.Page(
                "imageToRecipe.py",
                title='Image To Recipe',
                icon="📸"
            )
        ],
        "Ressources":[
            st.Page(
                "about.py", 
                title="About Us",
                icon='🌐'
                ),
            st.Page(
                "profile.py",
                title="Profile",
                icon="👤"
            ),
            st.Page(
                "testing.py",
                title="Testing",
                icon='🧪'
            )
        ]
    }
    pg=st.navigation(pages)
    pg.run()
else:
    l_, mid, r_ = st.columns([1,3,1], border=False, vertical_alignment="top")
    with mid:
        st.title("Welcome on MyChef")
        st.text("Your weekly meal planner to make cooking meals enjoyable!")
        signIn, signUp = st.tabs(["Sign-In :unlock:", "Sign-Up :receipt:"])
        with signIn:
            authenticate()
        with signUp:
            register()
    # st.link_button("Intagram", url="https://www.instagram.com/mychef.be/", type='tertiary', icon='🔗', use_container_width=False)
    # st.link_button("LinkedIn", url="https://www.linkedin.com/in/louis-gokelaere/", type='tertiary', icon='🪪', use_container_width=False)