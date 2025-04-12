import streamlit_authenticator as stauth

passwords = ['beta']
hashed_passwords = stauth.Hasher(passwords).generate()
print(hashed_passwords)

