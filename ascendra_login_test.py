import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="Ascendra Login Test", layout="centered")
st.cache_data.clear()

# Pre-hashed password for 'beta'
hashed_passwords = ['$2b$12$8MxaagkOaB343exRdh.uBu9k7uQW/kVSKJqJ/mvcrwZpKVa.bXOAi']

credentials = {
    "usernames": {
        "ascendra": {
            "name": "Ascendra User",
            "password": hashed_passwords[0],
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "cookie_name",
    "some_signature_key",
    cookie_expiry_days=1
)

# ✅ FIX: Provide form_name as the first argument
login_result = authenticator.login('Login', location='main')

if login_result is not None:
    name, auth_status, username = login_result

    if auth_status:
        authenticator.logout("Logout", location="sidebar")
        st.success(f"Welcome {name} 👋")
        st.write("✅ You are logged in!")
    elif auth_status is False:
        st.error("Incorrect username or password")
    elif auth_status is None:
        st.warning("Please enter your credentials")
else:
    st.error("Login form could not be rendered.")
