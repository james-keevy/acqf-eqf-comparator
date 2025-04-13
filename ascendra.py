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
import fitz  # PyMuPDF
import io

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
        st.caption("Ascendra v1.2 is limited to CSV and PDF files")
        st.caption("Ascendra provides AI-assisted comparisons of learning outcomes within different artefacts (e.g. qualifications, curricula, microcredentials, job descriptions and many others), but results should be interpreted as advisory, not definitive. The model relies on language patterns and may not capture nuanced policy or contextual differences across frameworks. It is not a substitute for expert judgement, formal benchmarking, or regulatory endorsement. Users should validate results through human review and consult official frameworks for authoritative decisions.")

        st.caption("Click 'Compare Levels' to generate an AI-based similarity score. The threshold below helps categorize the result.")

        # Input: OpenAI API key
        api_key = st.secrets["OPENAI_API_KEY"]

        # File upload widgets
        # Primary_file = st.file_uploader("Upload a primary artefact in CSV format", type="csv")
        # Secondary_file = st.file_uploader("Upload a secondary artefact in CSV format", type="csv")

        # Helper function to extract text from PDF
        def extract_text_from_pdf(file):
            text = ""
            try:
                with fitz.open(stream=file.read(), filetype="pdf") as doc:
                    for page in doc:
                        text += page.get_text()
                return text
            except Exception as e:
                st.error(f"❌ Error reading PDF: {e}")
                return ""

        # File upload widgets
        Primary_file = st.file_uploader("📥 Upload a *Primary* artefact (CSV or PDF)", type=["csv", "pdf"])
        Secondary_file = st.file_uploader("📥 Upload a *Secondary* artefact (CSV or PDF)", type=["csv", "pdf"])

        # Initialize variables
        Primary_text = ""
        Secondary_text = ""

        # --- Process Primary File ---
        if Primary_file:
            try:
                extension = Primary_file.name.lower().split(".")[-1]
                if extension == "csv":
                    df_primary = pd.read_csv(Primary_file, encoding="utf-8-sig", on_bad_lines="skip")
                    Primary_text = "\n".join(df_primary.iloc[:, 0].dropna().astype(str).tolist())
                    # Load Primary levels
                    if 'df_primary' in locals() and isinstance(df_primary, pd.DataFrame):
                        if all(col in df_primary.columns for col in ['Level', 'Domain', 'Descriptor']):
                            # Group by Level and Domain
                            Primary_descriptors = (
                                df_primary.groupby(['Level', 'Domain'])['Descriptor']
                                .apply(lambda x: "\n".join(x.dropna()))
                                .to_dict()
                            )
                        else:
                            st.warning("⚠️ Primary CSV must have 'Level', 'Domain', and 'Descriptor' columns.")
                elif extension == "pdf":
                    Primary_text = extract_text_from_pdf(Primary_file)
                else:
                    st.warning("Unsupported file format for Primary artefact.")
            except Exception as e:
                st.error(f"❌ Could not process Primary file: {e}")

        # --- Process Secondary File ---
        Secondary_levels = {}

        def extract_descriptors_from_pdf_text_grouped(text):
            """
            Extracts descriptors from plain PDF text in the form:
            Level → { Domain → Descriptor }
            """
            pattern = r"(Level\s*\d+)[\s\n]+(Knowledge|Skills|Autonomy|Responsibility|Competence)[\s\n]+(.+?)(?=(?:Level\s*\d+)|\Z)"
            matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)

            structured = {}
            for level_raw, domain_raw, descriptor in matches:
                level = level_raw.strip().title()
                domain = domain_raw.strip().title()
                desc = descriptor.strip().replace('\n', ' ')
                structured.setdefault(level, {})[domain] = desc
            return structured

        if Secondary_file:
            try:
                file_ext = Secondary_file.name.lower().split(".")[-1]

                if file_ext == "csv":
                    df_secondary = pd.read_csv(Secondary_file, encoding="utf-8-sig", on_bad_lines="skip")
                    if all(col in df_secondary.columns for col in ['Level', 'Domain', 'Descriptor']):
                        grouped = df_secondary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                        for (level, domain), descriptor in grouped.items():
                            Secondary_levels.setdefault(level, {})[domain] = descriptor
                    else:
                        st.warning("⚠️ Secondary CSV missing required columns.")


############# PDF SECONDARY INPUT 
                elif file_ext == "pdf":
                    Secondary_text = extract_text_from_pdf(Secondary_file)
                    Secondary_levels = extract_descriptors_from_pdf_text_grouped(Secondary_text)

                    if 'Secondary_text' in locals():
                        st.subheader("📄 Raw Secondary PDF Text")
                        st.text_area("Raw Text", Secondary_text[:3000], height=300)

                    if Secondary_levels:
                        st.success(f"✅ Found descriptors for {len(Secondary_levels)} levels.")
                        st.write(Secondary_levels)
                    else:
                        st.warning("⚠️ Secondary PDF parsing returned an empty dictionary.")

                    def extract_structured_from_pdf_to_csv(pdf_file, output_csv="extracted_descriptors.csv"):
                        import fitz  # PyMuPDF

                    # Step 1: Extract full text from PDF
                    try:
                        with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
                            text = ""
                            for page in doc:
                                text += page.get_text()
                    except Exception as e:
                        st.error(f"❌ Failed to read PDF: {e}")

                    # Step 2: Use regex to extract Level → Domain → Descriptor triples
                    pattern = r"""
                    (?:Level[:\s-]*\s*(\d+))                               # Match Level number (e.g. Level 4, Level: 4)
                    [\s\n\r]+                                              # Allow whitespace/newlines
                    (?:Domain[:\s-]*)?                                     # Optional 'Domain:' label
                    (Knowledge|Skills|Autonomy|Responsibility|Competence) # Explicit domain match
                    [\s\n\r]+
                    (.+?)                                                  # Descriptor (non-greedy)
                    (?=\n?(?:Level[:\s-]*\s*\d+|$))                        # Lookahead for next Level or EOF
                    """
                    matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE | re.VERBOSE)

                    if not matches:
                        st.warning("⚠️ No valid level-domain-descriptor groups found in the PDF.")

                    # Step 3: Clean and save to CSV
                    rows = []
                    for level, domain, descriptor in matches:
                        level = f"Level {level.strip()}"
                        domain = domain.strip().title()

                        # ✅ Move cleaning inside the loop
                        cleaned_lines = [
                            re.sub(r"\s+", " ", line).strip()
                            for line in descriptor.strip().splitlines()
                            if line.strip() and not re.fullmatch(r"\s*", line)
                        ]
                        cleaned_descriptor = " ".join(cleaned_lines)

                        if level and domain and cleaned_descriptor:
                            rows.append([level, domain, cleaned_descriptor])

                    if not rows:
                        st.warning("⚠️ All extracted entries were incomplete and skipped.")

                    # Step 4: Write to CSV
                    output_path = f"/tmp/{output_csv}"
                    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(["Level", "Domain", "Descriptor"])
                        writer.writerows(rows)

                    # --- Build Secondary: Level → {Domain: Descriptor} ---
                    Secondary_levels = {}
                    if 'df_secondary' in locals() and isinstance(df_secondary, pd.DataFrame):
                        if all(col in df_secondary.columns for col in ['Level', 'Domain', 'Descriptor']):
                            grouped = df_secondary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                            for (level, domain), descriptor in grouped.items():
                                Secondary_levels.setdefault(level, {})[domain] = descriptor
                        else:
                            st.warning("⚠️ Secondary CSV must include 'Level', 'Domain', and 'Descriptor' columns.")

###############

            except Exception as e:
                st.error(f"❌ Could not process Secondary file: {e}")
            else:
                st.warning("Unsupported file format for Secondary artefact.")

        # Match threshold slider
        high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

        # Session state for results
        if "results" not in st.session_state:
            st.session_state.results = []

        # If all inputs are available
        if api_key and Primary_file and Secondary_file:
            client = OpenAI(api_key=api_key)
                              
            # Build a dictionary of levels to their descriptors
            Primary_levels = {}
            if 'df_primary' in locals() and isinstance(df_primary, pd.DataFrame):
                if all(col in df_primary.columns for col in ['Level', 'Domain', 'Descriptor']):
                    grouped = df_primary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                    for (level, domain), descriptor in grouped.items():
                        Primary_levels.setdefault(level, {})[domain] = descriptor
                else:
                    st.warning("⚠️ Primary CSV must include 'Level', 'Domain', and 'Descriptor' columns.")

            # --- Primary & Secondary UI ---
            if Primary_levels:
                selected_Primary_level = st.selectbox("Select Primary Level", sorted(Primary_levels.keys()))
            else:
                st.warning("⚠️ No valid Primary descriptors found.")
                
            if Secondary_levels:
                selected_Secondary_level = st.selectbox("Select Secondary Level", sorted(Secondary_levels.keys()))
            else:
                st.warning("⚠️ No valid Secondary descriptors found.")

            # Compare levels
            if st.button("Compare Levels"):
                Primary_text = "".join(Primary_levels[selected_Primary_level])
                Secondary_text = "".join(Secondary_levels[selected_Secondary_level])
            
            # PROMPT GPT >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

                prompt = f"""

Compare the following qualification level descriptors and assess their equivalence.

Primary Level {selected_Primary_level}:
{Primary_text}

Secondary Level {selected_Secondary_level}:
{Secondary_text}

Compare the descriptors. Are these levels equivalent? Highlight similarities and differences. 

Suggest the most appropriate Secondary level match.

Provide a similarity score out of 100. Write this as a separate score below your response. 

Add a visual depiction with one row of 10 circles sized double the hieght of the text. Fill the circles in red to match the score out of 100 proportionally, starting from the left. Keep the other circles unfilled.

Do not use a heading for the visual depiction. 

"""

                with st.spinner("Asking GPT-4o..."):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[

                            # PROMPT GPT >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

                                {
                                    "role": "system",
                                    "content": """You are an expert in qualifications frameworks and international education systems. You understand learning outcomes and domain-based comparisons. You are able to compare the learning outcomes in different artefacts (such as level descriptors, qualifications, curricula, and job descriptions). You are well versed in the application of taxonomies, such as the revised Bloom taxonomy for knowledge, the Structure of the Observed Learning Outcome (SOLO) taxonomy, and the the Dreyfus
model of skills acquisition."""
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )

                        result_text = response.choices[0].message.content

                        if result_text:
                            match = re.search(r"similarity score[^\d]*(\d{1,3})", result_text, re.IGNORECASE)
                            ai_score = int(match.group(1)) if match else None

                            st.subheader(f"Comparison Result: Primary Level {selected_Primary_level} - Secondary Level {selected_Secondary_level}")

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

                            from fpdf import FPDF
                            import io
                            from datetime import datetime
                            from fpdf.enums import XPos, YPos

                            class PDFWithFooter(FPDF):
                                def footer(self):
                                    self.set_y(-15)
                                    self.set_font("DejaVu", "I", 8)
                                    self.set_text_color(128)
                                    self.cell(0, 10, "Powered by Ascendra | Version 1.0 – April 2025 – Results should be interpreted as advisory", 0, 0, "C")

                            def safe_multicell(pdf_obj, width, height, text):
                                import re
                                if not text:
                                    return
                                words = re.split(r'(\s+)', str(text))
                                current_line = ''
                                for word in words:
                                    chunk = current_line + word
                                    if pdf_obj.get_string_width(chunk) > pdf_obj.w - 2 * pdf_obj.l_margin:
                                        pdf_obj.multi_cell(width, height, current_line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                                        current_line = word
                                    else:
                                        current_line += word
                                if current_line.strip():
                                    pdf_obj.multi_cell(width, height, current_line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                            # --- Create PDF ---
                            pdf = PDFWithFooter()
                            pdf.add_page()

                            # Fonts
                            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
                            pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
                            pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
                            pdf.set_font("DejaVu", size=8)

                            # Header
                            pdf.image("ascendra_v5.png", x=10, y=8, w=40)
                            pdf.ln(45)
                            pdf.set_font("DejaVu", "B", 14)
                            safe_multicell(pdf, 0, 8, "Primary - Secondary Comparison Report")
                            pdf.set_font("DejaVu", "", 8)
                            safe_multicell(pdf, 0, 8, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
                            pdf.ln(10)

                            # Primary Level
                            pdf.set_font("DejaVu", "B", 12)
                            safe_multicell(pdf, 0, 8, f"Primary Level {selected_Primary_level}")
                            pdf.set_font("DejaVu", "", 8)
                            for item in Primary_levels[selected_Primary_level]:
                                safe_multicell(pdf, 0, 8, f"• {item}")
                            pdf.ln(5)

                            # Secondary Level
                            pdf.set_font("DejaVu", "B", 12)
                            safe_multicell(pdf, 0, 8, f"Secondary Level {selected_Secondary_level}")
                            pdf.set_font("DejaVu", "", 8)
                            for item in Secondary_levels[selected_Secondary_level]:
                                safe_multicell(pdf, 0, 8, f"• {item}")
                            pdf.ln(5)

                            # # Similarity Score                                                  
                            # if ai_score is not None and 0 <= ai_score <= 100:
                            #     st.write(f"**AI Similarity Score:** {ai_score}/100")
                            #     st.progress(ai_score / 100.0)

                            #     if ai_score >= high_match_threshold:
                            #         st.success("High Match")
                            #     elif ai_score >= 50:
                            #         st.warning("Moderate Match")
                            #     else:
                            #         st.error("Low Match")
                            # else:
                            #     st.error("⚠️ No valid similarity score found in the response.")

                            # GPT Result
                            pdf.set_font("DejaVu", "B", 12)
                            safe_multicell(pdf, 0, 8, "GPT Comparison Result:")
                            pdf.set_font("DejaVu", "", 8)
                            safe_multicell(pdf, 0, 8, result_text)
                            pdf.ln(5)

                            # Convert to BytesIO
                            pdf_bytes = io.BytesIO(pdf.output(dest='S'))

                            st.session_state.results.append({
                                "Primary Level": selected_Primary_level,
                                "Secondary Level": selected_Secondary_level,
                                "Similarity Score": ai_score if ai_score else "N/A",
                                "Response": result_text,
                                "Timestamp": datetime.utcnow().isoformat()
                            })

                            # ✅ Show CSV export button right after results are stored
                            if st.session_state.results:
                                df = pd.DataFrame(st.session_state.results)
                                st.download_button(
                                    label="📥 Download comparison as CSV",
                                    data=df.to_csv(index=False).encode("utf-8"),
                                    file_name="Primary_Secondary_comparisons.csv",
                                    mime="text/csv"
                                )

                            # PDF Download Button
                            st.download_button(
                                label="📄 Download this comparison as PDF",
                                data=pdf_bytes,
                                file_name=f"Primary_Secondary_comparison_{selected_Primary_level}_{selected_Secondary_level}.pdf",
                                mime="application/pdf")
                            
                            # Reset Button
                            if st.button("🔄 Run new query"):
                                st.session_state.results = []
                                st.rerun()
                        else:
                            st.info("No results yet — run a comparison to enable downloading.")

                            if st.button("🔄 New Query"):
                                st.session_state.results = []
                                st.rerun()

                    except Exception as e:
                        st.error(f"❌ API Error: {e}")

        # ✅ These lines should align with the outermost block
        elif auth_status is False:
            st.error("Incorrect username or password")
        elif auth_status is None:
            st.warning("Please enter your credentials")
    else:
        st.error("Login form could not be rendered.")
