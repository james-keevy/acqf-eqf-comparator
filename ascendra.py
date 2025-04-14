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
from io import BytesIO
import tempfile

# Initialize variables
Primary_text = ""
Secondary_text = ""
Secondary_file = st.file_uploader("Upload secondary artefact (CSV or PDF formats)", type=["csv", "pdf"])

# Create a login screen for your public app (simulating private access)
st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")

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

        # File upload
        st.markdown(
            """
            <style>
            /* 🎯 Target file uploader container */
            div[data-testid="stFileUploader"] > div {
                background-color: #f5faff !important;
                border: 2px solid #2c6ebb !important;
                border-radius: 10px;
                padding: 10px;
                transition: all 0.3s ease;
            }

            div[data-testid="stFileUploader"] > div:hover {
                background-color: #e6f0ff !important;
                border-color: #1a5fb4 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        Primary_file = st.file_uploader("Upload primary artefact (CSV format)", type=["csv"])

        if Primary_file is not None:
            try:
                # Read the file once
                bytes_data = Primary_file.getvalue()
                content = bytes_data.decode("utf-8-sig", errors="ignore")

                if not content.strip():
                    st.error("❌ Uploaded Primary file is empty.")
                else:
                    file_buffer = io.StringIO(content)
                    df_primary = pd.read_csv(file_buffer, on_bad_lines="skip")

                    required_cols = {"Level", "Domain", "Descriptor"}
                    if required_cols.issubset(df_primary.columns):
                        st.success("✅ Primary file loaded successfully.")

                        # ✅ Preview toggle
                        if st.checkbox("🔍 Show Primary file preview", value=False):
                            st.dataframe(df_primary.head())
                            
                    else:
                        st.warning(f"⚠️ Missing required columns: {required_cols - set(df_primary.columns)}")

            except Exception as e:
                st.error(f"❌ Could not process Primary file: {e}")
        else:
            st.info("📥 Please upload a primary file to continue.")
      
        st.file_uploader("Upload secondary artefact (CSV or PDF formats)", type=["csv", "pdf"])

        if Secondary_file is not None:
            
            # DEBUG
            st.write("🔍 Type of Secondary_file before parsing:", type(Secondary_file))
            structured_data, csv_path = parse_nqf_pdf_format(Secondary_file)

            def parse_nqf_pdf_format(file):
                try:
                    Secondary_file.seek(0)  # 🔄 Reset pointer to beginning
                    pdf_bytes = file.read()

                    # 🔍 Confirm the type is bytes, or raise clear error
                    if isinstance(pdf_bytes, str):
                        raise TypeError("❌ pars_pdf_format expected bytes, but got string.")

                    # ✅ Open PDF from byte stream
                    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                        text = "".join([page.get_text() for page in doc])

                except Exception as e:
                    raise RuntimeError(f"Error while opening PDF: {e}")

                # === Your existing parsing logic ===
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                lines = [line for line in lines if not re.match(r'^\d+$', line.strip())]  # remove standalone page numbers
                
                level_pattern = re.compile(r'(?:^|\s)Level (One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)', re.IGNORECASE)
                domain_pattern = re.compile(r'^([a-j])\.\s+(.*?)(?=, in respect of)', re.IGNORECASE)

                current_level = None
                current_domain = None
                descriptor_accumulator = ""
                data = []

                for line in lines:
                    level_match = level_pattern.search(line)
                    domain_match = domain_pattern.match(line)

                    if level_match:
                        if current_level and current_domain and descriptor_accumulator:
                            data.append((current_level, current_domain, descriptor_accumulator.strip()))
                            descriptor_accumulator = ""
                        current_level = f"Level {level_match.group(1).capitalize()}"
                        current_domain = None

                    elif domain_match:
                        if current_level and current_domain and descriptor_accumulator:
                            data.append((current_level, current_domain, descriptor_accumulator.strip()))
                            descriptor_accumulator = ""
                        current_domain = domain_match.group(2).strip()

                    elif current_level and current_domain:
                        descriptor_accumulator += " " + line

                if current_level and current_domain and descriptor_accumulator:
                    data.append((current_level, current_domain, descriptor_accumulator.strip()))

                if not data:
                    raise RuntimeError("⚠️ No structured descriptors could be extracted from the PDF.")

                # ✅ Save to CSV
                temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w', newline='', suffix='.csv')
                writer = csv.writer(temp_csv)
                writer.writerow(["Level", "Domain", "Descriptor"])
                writer.writerows(data)
                temp_csv.close()

                return data, temp_csv.name

            try:
                file_ext = Secondary_file.name.split(".")[-1].lower()

                if file_ext == "csv":
                    bytes_data = Secondary_file.getvalue()
                    content = bytes_data.decode("utf-8-sig", errors="ignore")

                    if not content.strip():
                        st.error("❌ Uploaded Secondary CSV file is empty.")
                    else:
                        df_secondary = pd.read_csv(io.StringIO(content), on_bad_lines="skip")
                        required_cols = {"Level", "Domain", "Descriptor"}
                        if required_cols.issubset(df_secondary.columns):
                            st.success("✅ Secondary file loaded successfully.")
                            if st.checkbox("🔍 Show Secondary file preview", value=False):
                                st.dataframe(df_secondary.head())
                        else:
                            st.warning(f"⚠️ Missing required columns: {required_cols - set(df_secondary.columns)}")

                elif file_ext == "pdf":
                    st.subheader("📄 Parsing PDF descriptors...")

                    try:
                        structured_data, csv_io = parse_nqf_pdf_format(Secondary_file)

                        if structured_data and csv_io:
                            csv_io.seek(0)
                            csv_text = csv_io.read().decode("utf-8-sig")
                            df_secondary = pd.read_csv(io.StringIO(csv_text))

                            st.success(f"✅ Secondary file loaded successfully from PDF ({len(structured_data)} records).")

                            if st.checkbox("🔍 Show Secondary file preview", value=False):
                                st.dataframe(df_secondary.head())
                        else:
                            st.warning("⚠️ No valid descriptors found in PDF.")

                    except Exception as e:
                        st.error(f"❌ Could not process Secondary file: {e}")
            
            except Exception as e:
                st.error(f"❌ Unexpected error while loading Secondary file: {e}")
        
        else:
            st.info("📥 Please upload a secondary file to continue.")
        if Primary_file and Secondary_file:
            try:
                # Compare byte content directly
                if Primary_file.getvalue() == Secondary_file.getvalue():
                    st.error("⚠️ You’ve uploaded the same file for both Primary and Secondary. Please upload two different files.")
                    st.stop()  # 🚫 Prevents further execution
            except Exception as e:
                st.warning(f"⚠️ Could not compare files: {e}")

        # Process Primary File
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

            # ✅ Reusable function: Extract structured data and write to CSV
            def parse_nqf_pdf_format(uploaded_file):
                try:
                    uploaded_file.seek(0)
                    pdf_bytes = uploaded_file.read()

                    # ✅ Add this diagnostic
                    if isinstance(pdf_bytes, str):
                        raise TypeError("❌ File was read as a string — expected bytes.")
                    
                    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                        text = "".join([page.get_text() for page in doc])

                except Exception as e:
                    raise RuntimeError(f"Error while opening PDF: {e}")

                # Continue with the parsing logic...
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                level_pattern = re.compile(r'^Level (One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)', re.IGNORECASE)
                domain_pattern = re.compile(r'^([a-j])\.\s+(.*?)(?=, in respect of)', re.IGNORECASE)

                current_level = None
                current_domain = None
                descriptor_accumulator = ""
                data = []

                for line in lines:
                    level_match = level_pattern.match(line)
                    domain_match = domain_pattern.match(line)

                    if level_match:
                        if current_level and current_domain and descriptor_accumulator:
                            data.append((current_level, current_domain, descriptor_accumulator.strip()))
                            descriptor_accumulator = ""
                        current_level = f"Level {level_match.group(1).capitalize()}"
                        current_domain = None

                    elif domain_match:
                        if current_level and current_domain and descriptor_accumulator:
                            data.append((current_level, current_domain, descriptor_accumulator.strip()))
                            descriptor_accumulator = ""
                        current_domain = domain_match.group(2).strip()

                    elif current_level and current_domain:
                        descriptor_accumulator += " " + line

                if current_level and current_domain and descriptor_accumulator:
                    data.append((current_level, current_domain, descriptor_accumulator.strip()))

                if not data:
                    raise RuntimeError("⚠️ No structured descriptors could be extracted from the PDF.")

                temp_csv = tempfile.NamedTemporaryFile(delete=False, mode='w', newline='', suffix='.csv')
                writer = csv.writer(temp_csv)
                writer.writerow(["Level", "Domain", "Descriptor"])
                writer.writerows(data)
                temp_csv.close()

                return data, temp_csv.name

        # Process Secondary File 
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

                elif file_ext == "pdf":
                    st.subheader("📄 Parsing Level Descriptors from PDF")

                    # ✅ Always reset file pointer before reading
                    Secondary_file.seek(0)

                    # ✅ Correct parser name
                    structured_data, csv_path = parse_nqf_pdf_format(Secondary_file)

                    if structured_data:
                        st.success(f"✅ Parsed {len(structured_data)} levels from PDF.")
                        st.write(structured_data)

                        if csv_path:
                            with open(csv_path, "rb") as f:
                                st.download_button("⬇️ Download Extracted CSV", f, file_name="secondary_descriptors.csv")
                    else:
                        st.warning("⚠️ PDF parsing returned no valid structured descriptors.")

                else:
                    st.warning("⚠️ Unsupported file format for Secondary artefact.")

            except Exception as e:
                st.error(f"❌ Could not process Secondary file: {e}")

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

                Compare the following level descriptors and assess their equivalence.

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




            

