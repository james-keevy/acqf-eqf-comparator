import streamlit_authenticator as stauth

# Step 1: Generate the hashed password (do this only once)
hashed_passwords = stauth.Hasher(['yourpassword']).generate()
print(hashed_passwords)  # Copy this output
