import streamlit as st
import csv
from collections import defaultdict
import openai

# --- Streamlit UI ---
st.set_page_config(page_title="ACQF-EQF Level Comparator")
st.title("🔍 ACQF ↔ EQF Level Comparator")

# Input: OpenAI API key
api_key = st.text_input("Enter your OpenAI API key", type="password")

# File upload widgets
acqf_file = st.file_uploader("Upload ACQF levels CSV", type="csv")
eqf_file = st.file_uploader("Upload EQF levels CSV (ACQF format)", type="csv")

# Proceed if all inputs are available
if api_key and acqf_file and eqf_file:
    openai.api_key = api_key

    # Load ACQF levels
    acqf_levels = defaultdict(list)
    reader = csv.DictReader(acqf_file)
    reader.fieldnames = [h.strip().lstrip('\ufeff') for h in reader.fieldnames]
    for row in reader:
        if not row or not row.get('Level') or not row.get('Domain') or not row.get('Descriptor'):
            continue
        level = row['Level'].strip()
        domain = row['Domain'].strip()
        descriptor = row['Descriptor'].strip()
        acqf_levels[level].append(f"{domain}: {descriptor}")

    # Load EQF levels
    eqf_levels = defaultdict(list)
    reader = csv.DictReader(eqf_file)
    reader.fieldnames = [h.strip().lstrip('\ufeff') for h in reader.fieldnames]
    for row in reader:
        if not row or not row.get('Level') or not row.get('Domain') or not row.get('Descriptor'):
            continue
        level = row['Level'].strip()
        domain = row['Domain'].strip()
        descriptor = row['Descriptor'].strip()
        eqf_levels[level].append(f"{domain}: {descriptor}")

    # Dropdowns for selecting levels
    selected_acqf_level = st.selectbox("Select ACQF Level", sorted(acqf_levels.keys()))
    selected_eqf_level = st.selectbox("Select EQF Level", sorted(eqf_levels.keys()))

    if st.button("Compare Levels"):
        acqf_text = "\n".join(acqf_levels[selected_acqf_level])
        eqf_text = "\n".join(eqf_levels[selected_eqf_level])

        prompt = f"""
Compare the following qualification level descriptors and assess their equivalence.

ACQF Level {selected_acqf_level}:
{acqf_text}

EQF Level {selected_eqf_level}:
{eqf_text}

Are these levels equivalent? Highlight similarities and differences. Suggest the most appropriate EQF level match.
"""

        with st.spinner("Asking GPT-4o..."):
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert in qualifications frameworks and international education systems."},
                    {"role": "user", "content": prompt}
                ]
            )
            st.subheader(f"Comparison Result: ACQF {selected_acqf_level} ↔ EQF {selected_eqf_level}")
            st.write(response.choices[0].message['content'])
