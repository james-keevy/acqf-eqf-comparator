import streamlit as st
import csv
import pandas as pd
from collections import defaultdict
from openai import OpenAI
from datetime import datetime
import re
from fpdf import FPDF
import io

# --- Streamlit UI ---
st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")
st.image("ascendra_logo_dark4.png", width=300)
st.title("Learning Outcomes Levelling")
st.caption("smarter levelling with genAI – by Ascendra")

st.markdown("""
<style>
/* Reduce font size of uploaded file name below uploader */
div[data-testid="stFileUploader"] > label > div {
    font-size: 0.8rem !important;
    color: #444;
}
</style>
""", unsafe_allow_html=True)

# Input: OpenAI API key
api_key = st.secrets["OPENAI_API_KEY"]

# File upload widgets
primary_file = st.file_uploader("Upload a primary set of level descriptors in CSV format", type="csv")
secondary_file = st.file_uploader("Upload a secondary set of level descriptors in CSV format", type="csv")

# Match threshold slider
high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

# Session state for results
if "results" not in st.session_state:
    st.session_state.results = []

# If all inputs are available
if api_key and primary_file and secondary_file:
    client = OpenAI(api_key=api_key)

    # Load primary levels
    primary_levels = defaultdict(list)
    primary_reader = csv.DictReader(primary_file.read().decode("utf-8").splitlines())
    primary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in primary_reader.fieldnames]
    for row in primary_reader:
        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
            primary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

    # Load secondary levels
    secondary_levels = defaultdict(list)
    secondary_reader = csv.DictReader(secondary_file.read().decode("utf-8").splitlines())
    secondary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in secondary_reader.fieldnames]
    for row in secondary_reader:
        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
            secondary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

    # Level selection dropdowns
    selected_primary_level = st.selectbox("Select Primary Level", sorted(primary_levels.keys()))
    selected_secondary_level = st.selectbox("Select Secondary Level", sorted(secondary_levels.keys()))

    # Compare levels
    if st.button("Compare Levels"):
        primary_text = "\n".join(primary_levels[selected_primary_level])
        secondary_text = "\n".join(secondary_levels[selected_secondary_level])

        prompt = f"""
Compare the following qualification level descriptors and assess their equivalence.

primary Level {selected_primary_level}:
{primary_text}

secondary Level {selected_secondary_level}:
{secondary_text}

Compare the descriptors. Are these levels equivalent? Highlight similarities and differences. Suggest the most appropriate secondary level match and provide a similarity score out of 100.
"""

        with st.spinner("Asking GPT-4o..."):
            try:
                response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert in qualifications frameworks and international education systems. You understand learning outcomes and domain-based comparisons."},
                    {"role": "user", "content": prompt}
                    ]
                )
                result_text = response.choices[0].message.content
            
            except Exception as e:
                st.error(f"❌ API Error: {e}")

           # Show comparison results
            if result_text:
                match = re.search(r"similarity score[^\d]*(\d{1,3})", result_text, re.IGNORECASE)
                similarity_score = int(match.group(1)) if match else None

                st.subheader(f"Comparison Result: Primary Level {selected_primary_level} - Secondary Level {selected_secondary_level}")

                if similarity_score is not None and 0 <= similarity_score <= 100:
                    st.write(f"**Similarity Score:** {similarity_score}/100")
                    st.progress(similarity_score / 100.0)

                    if similarity_score >= high_match_threshold:
                        st.success("High Match")
                    elif similarity_score >= 50:
                        st.warning("Moderate Match")
                    else:
                        st.error("Low Match")

                with st.expander("View compared descriptors"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Primary Level {selected_primary_level}**")
                        for item in primary_levels[selected_primary_level]:
                            st.markdown(f"- {item}")
                    with col2:
                        st.markdown(f"**Secondary Level {selected_secondary_level}**")
                        for item in secondary_levels[selected_secondary_level]:
                            st.markdown(f"- {item}")

                st.write(result_text)

                # Save to results state
                st.session_state.results.append({
                    "Primary Level": selected_primary_level,
                    "Secondary Level": selected_secondary_level,
                    "Similarity Score": similarity_score if similarity_score else "N/A",
                    "Response": result_text,
                    "Timestamp": datetime.utcnow().isoformat()
                })

                similarity_score = None

# --- PDFExport ---

            class PDFWithFooter(FPDF):
                def footer(self):
                    self.set_y(-15)
                    self.set_font("DejaVu", "I", 8)
                    self.set_text_color(128)
                    self.cell(0, 10, "Powered by Ascendra | Version 1.0 - April 2025", 0, 0, "C")

            pdf = PDFWithFooter()
            pdf.add_page()

            # Register Unicode fonts
            pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
            pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)
            pdf.set_font("DejaVu", "", 12)

            # Header
            pdf.image("ascendra_logo_dark4.png", x=10, y=8, w=40)
            pdf.ln(25)
            pdf.cell(200, 10, txt="primary - secondary Comparison Report", ln=True, align='C')
            pdf.cell(200, 10, txt=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), ln=True, align='C')
            pdf.ln(10)

            # primary Level Info
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 10, txt=f"primary Level {selected_primary_level}", ln=True)
            pdf.set_font("DejaVu", "", 11)
            for item in primary_levels[selected_primary_level]:
                pdf.set_x(10)  # Reset X position to left margin
                pdf.multi_cell(0, 8, item)

            # secondary Level Info
            pdf.ln(5)
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 10, txt=f"secondary Level {selected_secondary_level}", ln=True)
            pdf.set_font("DejaVu", "", 11)
            for item in secondary_levels[selected_secondary_level]:
                pdf.set_x(10)  # Reset X position to left margin
                pdf.multi_cell(0, 8, item)

            # Similarity Score
            pdf.ln(5)
            if similarity_score:
                pdf.cell(0, 10, txt=f"Similarity Score: {similarity_score}/100", ln=True)

            # GPT Output
            pdf.ln(5)
            pdf.set_font("DejaVu", "B", 12)
            pdf.multi_cell(0, 10, "GPT Comparison Result:")
            pdf.set_font("DejaVu", "", 11)
            pdf.set_x(10)  # Reset X position to left margin
            pdf.multi_cell(190, 10, result_text)

            # Export PDF
            # Output PDF to BytesIO
            pdf_bytes = pdf.output(dest="S").encode("latin-1")  # Convert string to bytes
            pdf_buffer = io.BytesIO(pdf_bytes)

            st.download_button(
                label="📄 Download this Comparison as PDF",
                data=pdf_buffer,
                file_name=f"Ascendra_{selected_primary_level}_{selected_secondary_level}.pdf",
                mime="application/pdf"
)

# --- CSV Export ---
if st.session_state.get("results"):
    df = pd.DataFrame(st.session_state.results)
    st.download_button(
        label="📥 Download All Comparisons as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="primary_secondary_comparisons.csv",
        mime="text/csv"
    )
else:
    st.info("No results yet — run a comparison to enable downloading.")

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
