
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
from io import BytesIO
import fitz  # PyMuPDF

st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")

# --- PDF Parsing Helper ---
def parse_nqf_pdf_format(file):
    def extract_text_from_pdf(file):
        text = ""
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        return text

    def parse_structured_descriptors(text):
        level_data = []
        matches = re.split(r"(Level\s+\d+)", text)
        for i in range(1, len(matches), 2):
            level = matches[i].strip()
            content = matches[i+1].strip()
            domains = re.split(r"(?=Knowledge|Skills|Responsibility|Autonomy)", content, flags=re.IGNORECASE)
            for domain_text in domains:
                domain_match = re.match(r"(Knowledge|Skills|Responsibility|Autonomy)", domain_text, re.IGNORECASE)
                if domain_match:
                    domain = domain_match.group(0).capitalize()
                    descriptor = domain_text[len(domain):].strip()
                    level_data.append({
                        "Level": level,
                        "Domain": domain,
                        "Descriptor": descriptor
                    })
        return level_data

    try:
        raw_text = extract_text_from_pdf(file)
        parsed_data = parse_structured_descriptors(raw_text)

        if not parsed_data:
            return None, None

        df = pd.DataFrame(parsed_data)
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return parsed_data, csv_buffer

    except Exception as e:
        st.error(f"❌ PDF parsing error: {e}")
        return None, None

# --- Auth Setup ---
hashed_passwords = ['$2b$12$2Myv8E.J5lIbWN5aThrBDOeGthVRDw4e7j38g.fDTOmiy.VvKRCZa']

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
    "ascendra_cookie",
    "abcdef",
    cookie_expiry_days=1
)

login_result = authenticator.login(form_name='Login', location='main')

if login_result is not None:
    name, auth_status, username = login_result
    if auth_status:
        authenticator.logout('Logout', location='sidebar')
        st.success(f"Welcome {name}")

        st.image("ascendra_v5.png", width=300)
        st.title("Comparing learning outcomes")
        st.caption("Ascendra v1.1 is limited to CSV and PDF files")
        st.caption("Ascendra provides AI-assisted comparisons of learning outcomes within different artefacts (e.g. qualifications, curricula, microcredentials, job descriptions and many others), but results should be interpreted as advisory, not definitive. The model relies on language patterns and may not capture nuanced policy or contextual differences across frameworks. It is not a substitute for expert judgement, formal benchmarking, or regulatory endorsement. Users should validate results through human review and consult official frameworks for authoritative decisions.")

        st.caption("Click 'Compare Levels' to generate an AI-based similarity score. The threshold below helps categorize the result.")

        api_key = st.secrets["OPENAI_API_KEY"]

        Primary_file = st.file_uploader("Upload a primary artefact (CSV or PDF)", type=["csv", "pdf"])
        Secondary_file = st.file_uploader("Upload a secondary artefact (CSV or PDF)", type=["csv", "pdf"])

        high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

        if "results" not in st.session_state:
            st.session_state.results = []

        Primary_levels = defaultdict(dict)
        Secondary_levels = defaultdict(dict)

        if Primary_file:
            ext = Primary_file.name.split(".")[-1].lower()
            if ext == "csv":
                df_primary = pd.read_csv(Primary_file)
            elif ext == "pdf":
                data, csv_bytes = parse_nqf_pdf_format(Primary_file)
                if data:
                    df_primary = pd.read_csv(csv_bytes)
                else:
                    df_primary = pd.DataFrame()
            else:
                df_primary = pd.DataFrame()

            if not df_primary.empty:
                grouped = df_primary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                for (level, domain), descriptor in grouped.items():
                    Primary_levels[level][domain] = descriptor

        if Secondary_file:
            ext = Secondary_file.name.split(".")[-1].lower()
            if ext == "csv":
                df_secondary = pd.read_csv(Secondary_file)
            elif ext == "pdf":
                data, csv_bytes = parse_nqf_pdf_format(Secondary_file)
                if data:
                    df_secondary = pd.read_csv(csv_bytes)
                else:
                    df_secondary = pd.DataFrame()
            else:
                df_secondary = pd.DataFrame()

            if not df_secondary.empty:
                grouped = df_secondary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                for (level, domain), descriptor in grouped.items():
                    Secondary_levels[level][domain] = descriptor

        if Primary_levels and Secondary_levels:
            selected_Primary_level = st.selectbox("Select Primary Level", sorted(Primary_levels.keys()))
            selected_Secondary_level = st.selectbox("Select Secondary Level", sorted(Secondary_levels.keys()))

            if st.button("Compare Levels"):
                Primary_text = "\n".join([f"{domain}: {desc}" for domain, desc in Primary_levels[selected_Primary_level].items()])
                Secondary_text = "\n".join([f"{domain}: {desc}" for domain, desc in Secondary_levels[selected_Secondary_level].items()])

                prompt = f"""Compare the following qualification level descriptors and assess their equivalence.

Primary Level {selected_Primary_level}:
{Primary_text}

Secondary Level {selected_Secondary_level}:
{Secondary_text}

Compare the descriptors. Are these levels equivalent? Highlight similarities and differences.

Suggest the most appropriate Secondary level match.

Provide a similarity score out of 100. Write this as a separate score below your response.

Add a visual depiction with one row of 10 circles sized double the height of the text. Fill the circles in red to match the score out of 100 proportionally, starting from the left. Keep the other circles unfilled.

Do not use a heading for the visual depiction.
"""
                st.session_state.comparison_prompt = prompt
                st.rerun()
else:
    st.error("Login form could not be rendered.")
