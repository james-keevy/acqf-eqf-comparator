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
import time

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

        # --- Parse NQF PDF ---
        def parse_nqf_pdf_format(uploaded_file, label="primary"):
            if not uploaded_file:
                return {}, None

            try:
                # Wrap the uploaded file in a BytesIO buffer
                pdf_buffer = BytesIO(uploaded_file.read())

                # ✅ Try opening PDF
                text = ""
                with fitz.open(stream=pdf_buffer, filetype="pdf") as doc:
                    for page in doc:
                        text += page.get_text()

                # ✅ Extract structured descriptors
                structured = extract_descriptors_from_pdf_text_grouped(text)

                # ✅ Save to temp CSV
                temp_dir = tempfile.gettempdir()
                output_csv_path = Path(temp_dir) / f"{label.lower()}_levels.csv"

                rows = []
                for level, domains in structured.items():
                    for domain, descriptor in domains.items():
                        rows.append({
                            "Level": level,
                            "Domain": domain,
                            "Descriptor": descriptor
                        })

                pd.DataFrame(rows).to_csv(output_csv_path, index=False, encoding="utf-8-sig")

                return structured, str(output_csv_path)

            except Exception as e:
                st.error(f"❌ Failed to parse PDF: {e}")
                return {}, None

            structured = extract_descriptors_from_pdf_text_grouped(text)

            temp_dir = tempfile.gettempdir()
            output_csv_path = Path(temp_dir) / f"{label.lower()}_levels.csv"

            rows = []
            for level, domains in structured.items():
                for domain, descriptor in domains.items():
                    rows.append({"Level": level, "Domain": domain, "Descriptor": descriptor})

            pd.DataFrame(rows).to_csv(output_csv_path, index=False, encoding="utf-8-sig")
            return structured, str(output_csv_path)

        # --- Process Primary File ---
                
        Primary_levels = {}

        if Primary_file:
            try:
                file_ext = Primary_file.name.split(".")[-1].lower()

                if file_ext == "csv":
                    df_primary = pd.read_csv(Primary_file, encoding="utf-8-sig", on_bad_lines="skip")
                    if all(col in df_primary.columns for col in ['Level', 'Domain', 'Descriptor']):
                        grouped = df_primary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                        for (level, domain), descriptor in grouped.items():
                            Primary_levels.setdefault(level, {})[domain] = descriptor
                    else:
                        st.warning("⚠️ Primary CSV is missing required columns: Level, Domain, Descriptor.")

                elif file_ext == "pdf":
                    st.subheader("📄 Parsing NQF-style Level Descriptors from PDF")
                    Primary_levels_dict, csv_path = parse_nqf_pdf_format(Primary_file, label="primary")

                    if Primary_levels_dict:
                        success_placeholder = st.empty()
                        success_placeholder.success(f"✅ Parsed {len(Primary_levels_dict)} levels from PDF.")
                        time.sleep(3)
                        success_placeholder.empty()

                        st.write(Primary_levels_dict)

                        df_primary = pd.read_csv(csv_path)
                        st.session_state.df_primary_loaded = True
                        Primary_levels = Primary_levels_dict
                    else:
                        st.warning("⚠️ No structured descriptors could be extracted from the PDF.")

                else:
                    st.error(f"❌ Unsupported file format: `{file_ext.upper()}`. Please upload a CSV or PDF file.")

            except Exception as e:
                st.error(f"❌ Error processing Primary artefact: {e}")

        # Move PDF renders to CSV if need be

        Primary_levels_dict, csv_path = parse_nqf_pdf_format(Primary_file, label="primary")

        if structured_data:
            success_placeholder = st.empty()
            success_placeholder.success("✅ Parsed data from PDF.")
            time.sleep(3)
            success_placeholder.empty()

        # if Primary_levels_dict and csv_path:
        # # st.success(f"✅ Parsed {len(Primary_levels_dict)} levels from PDF.")
        #     success_placeholder = st.empty()
        #     success_placeholder.success(f"✅ Parsed data from PDF.")
        # # Wait for 3 seconds
        # time.sleep(3)

        # Clear the success message
        # success_placeholder.empty()

        # ✅ Load into DataFrame like a normal CSV
        df_primary = pd.read_csv(csv_path)
        st.session_state.df_primary_loaded = True  # optional flag
       
        # ..............................end primary

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
                    file_ext = Secondary_file.name.split(".")[-1].lower()

                    if file_ext == "csv":
                        df_secondary = pd.read_csv(Secondary_file, encoding="utf-8-sig", on_bad_lines="skip")
                        if all(col in df_secondary.columns for col in ['Level', 'Domain', 'Descriptor']):
                            grouped = df_secondary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                            for (level, domain), descriptor in grouped.items():
                                Secondary_levels.setdefault(level, {})[domain] = descriptor
                        else:
                            st.warning("⚠️ Secondary CSV is missing required columns: Level, Domain, Descriptor.")

                    elif file_ext == "pdf":
                        st.subheader("📄 Parsing NQF-style Level Descriptors from PDF")
                        structured_data, csv_path = parse_nqf_pdf_format(Secondary_file)

                        if structured_data:
                            st.success(f"✅ Parsed {len(structured_data)} levels from PDF.")
                            st.write(structured_data)
                            df_secondary = pd.read_csv(csv_path)
                        else:
                            st.warning("⚠️ No structured descriptors could be extracted from the PDF.")

                    else:
                        st.error(f"❌ Unsupported file format: `{file_ext.upper()}`. Please upload a CSV or PDF file.")

                except Exception as e:
                    st.error(f"❌ Error processing Secondary artefact: {e}")

        # Move PDF renders to CSV if need be

            elif file_ext == "pdf":
                st.subheader("📄 Parsing data from PDF")

        Secondary_levels_dict, csv_path = parse_nqf_pdf_format(Secondary_file)

        if Secondary_levels_dict and csv_path:
            # st.success(f"✅ Parsed {len(Secondary_levels_dict)} levels from PDF.")
            success_placeholder = st.empty()
            success_placeholder.success(f"✅ Parsed data from PDF.")
            # Wait for 3 seconds
            time.sleep(3)

            # Clear the success message
            success_placeholder.empty()

            # ✅ Load into DataFrame like a normal CSV
            df_secondary = pd.read_csv(csv_path)
            st.session_state.df_secondary_loaded = True  # optional flag
               
        # ..............................end secondary 
        
        # Match threshold slider
        high_match_threshold = st.slider("Set threshold for High Match (%)", min_value=50, max_value=100, value=80)

        # Session state for results
        if "results" not in st.session_state:
            st.session_state.results = []

        # If all inputs are available
        if api_key and Primary_file and Secondary_file:
            client = OpenAI(api_key=api_key)
                              
            # Build Primary: Level → {Domain: Descriptor} ---
            Primary_levels = {}
            if 'df_primary' in locals() and isinstance(df_primary, pd.DataFrame):
                if all(col in df_primary.columns for col in ['Level', 'Domain', 'Descriptor']):
                    grouped = df_primary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                    for (level, domain), descriptor in grouped.items():
                        Primary_levels.setdefault(level, {})[domain] = descriptor
                else:
                    st.warning("⚠️ Primary CSV must include 'Level', 'Domain', and 'Descriptor' columns.")

            # --- Build Secondary: Level → {Domain: Descriptor} ---
            Secondary_levels = {}
            if 'df_secondary' in locals() and isinstance(df_secondary, pd.DataFrame):
                if all(col in df_secondary.columns for col in ['Level', 'Domain', 'Descriptor']):
                    grouped = df_secondary.groupby(['Level', 'Domain'])['Descriptor'].apply(lambda x: "\n".join(x.dropna()))
                    for (level, domain), descriptor in grouped.items():
                        Secondary_levels.setdefault(level, {})[domain] = descriptor
                else:
                    st.warning("⚠️ Secondary data must include 'Level', 'Domain', and 'Descriptor' columns.")

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

Add a visual depiction with one row of 10 circles sized double the height of the text. Fill the circles in red to match the score out of 100 proportionally, starting from the left. Keep the other circles unfilled.

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
