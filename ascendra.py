import streamlit as st
import csv
import pandas as pd
from collections import defaultdict
from openai import OpenAI
from datetime import datetime
import re
from fpdf import FPDF
import textwrap
import streamlit_authenticator as stauth

st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")

# To create a login screen for your public app (simulating private access)

# Hashed password generated earlier
hashed_passwords = ['$2b$12$2Myv8E.J5lIbWN5aThrBDOeGthVRDw4e7j38g.fDTOmiy.VvKRCZa']  

# ✅ New structure for credentials
credentials = {
    "usernames": {
        "ascendra": {
            "name": "Ascendra User",
            "password": hashed_passwords[0],
        }
    }
}

# ✅ New Authenticate() signature
authenticator = stauth.Authenticate(
    credentials,
    "ascendra_cookie",  # cookie_name
    "abcdef",           # key
    cookie_expiry_days=1
)

# 🔐 Show login widget
login_result = authenticator.login(form_name='Login', location='main')

if login_result is not None:
    name, auth_status, username = login_result
    if auth_status:
        authenticator.logout('Logout', location='sidebar')
        st.success(f"Welcome {name}")

        # --- Streamlit UI ---
        st.image("ascendra_v5.png", width=300)
        st.title("Comparing learning outcomes")
        st.caption("Ascendra v1.1 is limited to CSV files")
        st.caption("Ascendra provides AI-assisted comparisons of learning outcomes within different artefacts (e.g. qualifications, curricula, microcredentials, job descriptions and many others), but results should be interpreted as advisory, not definitive. The model relies on language patterns and may not capture nuanced policy or contextual differences across frameworks. It is not a substitute for expert judgement, formal benchmarking, or regulatory endorsement. Users should validate results through human review and consult official frameworks for authoritative decisions.")

        st.caption("Click 'Compare Levels' to generate an AI-based similarity score. The threshold below helps categorize the result.")

        # Input: OpenAI API key
        api_key = st.secrets["OPENAI_API_KEY"]

        # File upload widgets
        Primary_file = st.file_uploader("Upload a primary artefact in CSV format", type="csv")
        Secondary_file = st.file_uploader("Upload a secondary artefact in CSV format", type="csv")

        # Match threshold slider
        high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

        # Session state for results
        if "results" not in st.session_state:
            st.session_state.results = []

        # If all inputs are available
        if api_key and Primary_file and Secondary_file:
            client = OpenAI(api_key=api_key)

            # Load Primary levels
            Primary_levels = defaultdict(list)
            Primary_reader = csv.DictReader(Primary_file.read().decode("utf-8").splitlines())
            Primary_reader.fieldnames = [h.strip().lstrip('﻿') for h in Primary_reader.fieldnames]
            for row in Primary_reader:
                if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                    Primary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

            # Load Secondary levels
            Secondary_levels = defaultdict(list)
            Secondary_reader = csv.DictReader(Secondary_file.read().decode("utf-8").splitlines())
            Secondary_reader.fieldnames = [h.strip().lstrip('﻿') for h in Secondary_reader.fieldnames]
            for row in Secondary_reader:
                if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                    Secondary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

            # Level selection dropdowns
            selected_Primary_level = st.selectbox("Select Primary Level", sorted(Primary_levels.keys()))
            selected_Secondary_level = st.selectbox("Select Secondary Level", sorted(Secondary_levels.keys()))

            # Compare levels
            if st.button("Compare Levels"):
                Primary_text = "".join(Primary_levels[selected_Primary_level])
                Secondary_text = "".join(Secondary_levels[selected_Secondary_level])

                prompt = f"""

Compare the following qualification level descriptors and assess their equivalence.

Primary Level {selected_Primary_level}:
{Primary_text}

Secondary Level {selected_Secondary_level}:
{Secondary_text}

Compare the descriptors. Are these levels equivalent? Highlight similarities and differences. 
Suggest the most appropriate Secondary level match and provide a similarity score out of 100.
"""

                with st.spinner("Asking GPT-4o..."):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "system",
                                    "content": """You are an expert in qualifications frameworks and international education systems. You understand learning outcomes and domain-based comparisons..."""
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )

                        result_text = response.choices[0].message.content

                        if st.button("🔄 New Query"):
                            st.session_state.results = []
                            st.rerun()

                        if result_text:
                            match = re.search(r"similarity score[^\d]*(\d{1,3})", result_text, re.IGNORECASE)
                            ai_score = int(match.group(1)) if match else None

                            st.subheader(f"Comparison Result: Primary Level {selected_Primary_level} - Secondary Level {selected_Secondary_level}")

                            if ai_score is not None and 0 <= ai_score <= 100:
                                st.write(f"**AI Similarity Score:** {ai_score}/100")
                                st.progress(ai_score / 100.0)

                                if ai_score >= high_match_threshold:
                                    st.success("High Match")
                                elif ai_score >= 50:
                                    st.warning("Moderate Match")
                                else:
                                    st.error("Low Match")
                            else:
                                st.error("⚠️ No valid similarity score found in the response.")

                            with st.expander("View compared descriptors"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Primary Level {selected_Primary_level}**")
                                    for item in Primary_levels[selected_Primary_level]:
                                        st.markdown(f"- {item}")
                                with col2:
                                    st.markdown(f"**Secondary Level {selected_Secondary_level}**")
                                    for item in Secondary_levels[selected_Secondary_level]:
                                        st.markdown(f"- {item}")

                            st.write(result_text)

                    except Exception as e:
                        st.error(f"❌ API Error: {e}")

        # --- Pinned footer ---
        st.markdown("""
        <style>
        footer { visibility: hidden; }
        footer:after {
            content: 'Powered by Ascendra | Built with Streamlit & OpenAI • Version 1.0 – April 2025';
            visibility: visible;
            display: block;
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: #f0f2f6;
            color: #6c757d;
            text-align: center;
            padding: 0.5rem;
            font-size: 0.8rem;
            font-family: 'sans-serif';
            z-index: 9999;
        }
        </style>
        """, unsafe_allow_html=True)

    elif auth_status is False:
        st.error("Incorrect username or password")
    elif auth_status is None:
        st.warning("Please enter your credentials")
else:
    st.error("Login form could not be rendered.")
