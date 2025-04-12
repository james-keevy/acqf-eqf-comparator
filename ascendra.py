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
login_result = authenticator.login('Login', location='main')

if login_result is not None:
    name, auth_status, username = login_result
    if auth_status:
            name, auth_status, username = login_result

            if auth_status:
                authenticator.logout('Logout', location='sidebar')
                st.success(f"Welcome {name} 👋")
                # 👉 Your app goes here

                # --- Streamlit UI ---
                # st.set_page_config(page_title="Learning Outcomes Levelling", layout="centered")
                st.image("ascendra_logo_dark4.png", width=300)
                st.title("Learning Outcomes Levelling")
                st.caption("Smarter Learning Outcomes Levelling with Generative AI | by Ascendra")

                # Input: OpenAI API key
                api_key = st.secrets["OPENAI_API_KEY"]

                # File upload widgets
                Primary_file = st.file_uploader("Upload a primary set of level descriptors in CSV format", type="csv")
                Secondary_file = st.file_uploader("Upload a secondary set of level descriptors in CSV format", type="csv")

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
                    Primary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in Primary_reader.fieldnames]
                    for row in Primary_reader:
                        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                            Primary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

                    # Load Secondary levels
                    Secondary_levels = defaultdict(list)
                    Secondary_reader = csv.DictReader(Secondary_file.read().decode("utf-8").splitlines())
                    Secondary_reader.fieldnames = [h.strip().lstrip('\ufeff') for h in Secondary_reader.fieldnames]
                    for row in Secondary_reader:
                        if row.get("Level") and row.get("Domain") and row.get("Descriptor"):
                            Secondary_levels[row["Level"].strip()].append(f"{row['Domain'].strip()}: {row['Descriptor'].strip()}")

                    # Level selection dropdowns
                    selected_Primary_level = st.selectbox("Select Primary Level", sorted(Primary_levels.keys()))
                    selected_Secondary_level = st.selectbox("Select Secondary Level", sorted(Secondary_levels.keys()))

                    # Compare levels
                    if st.button("Compare Levels"):
                        Primary_text = "\n".join(Primary_levels[selected_Primary_level])
                        Secondary_text = "\n".join(Secondary_levels[selected_Secondary_level])

                        prompt = f"""
                Compare the following qualification level descriptors and assess their equivalence.

                Primary Level {selected_Primary_level}:
                {Primary_text}

                Secondary Level {selected_Secondary_level}:
                {Secondary_text}

                Compare the descriptors. Are these levels equivalent? Highlight similarities and differences. Suggest the most appropriate Secondary level match and provide a similarity score out of 100.
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

                                if result_text:
                                    match = re.search(r"similarity score[^\d]*(\d{1,3})", result_text, re.IGNORECASE)
                                    similarity_score = int(match.group(1)) if match else None

                                    st.subheader(f"Comparison Result: Primary Level {selected_Primary_level} - Secondary Level {selected_Secondary_level}")

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
                                            st.markdown(f"**Primary Level {selected_Primary_level}**")
                                            for item in Primary_levels[selected_Primary_level]:
                                                st.markdown(f"- {item}")
                                        with col2:
                                            st.markdown(f"**Secondary Level {selected_Secondary_level}**")
                                            for item in Secondary_levels[selected_Secondary_level]:
                                                st.markdown(f"- {item}")

                                    st.write(result_text)

                                    # Save to results state
                                    st.session_state.results.append({
                                        "Primary Level": selected_Primary_level,
                                        "Secondary Level": selected_Secondary_level,
                                        "Similarity Score": similarity_score if similarity_score else "N/A",
                                        "Response": result_text,
                                        "Timestamp": datetime.utcnow().isoformat()
                                    })
                                    
                                    from fpdf import FPDF
                                    import io
                                    import re
                                    from datetime import datetime
                                    import streamlit as st
                                    from fpdf.enums import XPos, YPos

                                    # --- Safe multi-cell rendering ---
                                    def safe_multicell(pdf_obj, width, height, text):
                                        """
                                        A failsafe wrapper around multi_cell that prevents horizontal space errors
                                        by measuring string widths and forcing line breaks if needed.
                                        """
                                        if not text:
                                            return

                                        try:
                                            words = re.split(r'(\s+)', str(text))  # Split and preserve spaces
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
                                        except Exception as e:
                                            pdf_obj.multi_cell(width, height, f"[Render error: {e}]", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                                    # --- Footer class ---
                                    class PDFWithFooter(FPDF):
                                        def footer(self):
                                            self.set_y(-15)
                                            self.set_font("DejaVu", "I", 8)
                                            self.set_text_color(128)
                                            self.cell(0, 10, "Powered by Ascendra | Version 1.0 – April 2025", 0, 0, "C")

                                    # --- Create PDF ---
                                    pdf = PDFWithFooter()
                                    pdf.add_page()

                                    # Load fonts
                                    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
                                    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
                                    pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
                                    pdf.set_font("DejaVu", size=12)

                                    # --- Header ---
                                    pdf.image("ascendra_logo_dark4.png", x=10, y=8, w=40)
                                    pdf.ln(25)
                                    safe_multicell(pdf, 0, 10, "Primary - Secondary Comparison Report")
                                    safe_multicell(pdf, 0, 10, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
                                    pdf.ln(10)

                                    # --- Primary Level Info ---
                                    pdf.set_font("DejaVu", "B", 12)
                                    safe_multicell(pdf, 0, 10, f"Primary Level {selected_Primary_level}")
                                    pdf.set_font("DejaVu", size=11)
                                    for item in Primary_levels[selected_Primary_level]:
                                        safe_multicell(pdf, 0, 8, item)

                                    # --- Secondary Level Info ---
                                    pdf.ln(5)
                                    pdf.set_font("DejaVu", "B", 12)
                                    safe_multicell(pdf, 0, 10, f"Secondary Level {selected_Secondary_level}")
                                    pdf.set_font("DejaVu", size=11)
                                    for item in Secondary_levels[selected_Secondary_level]:
                                        safe_multicell(pdf, 0, 8, item)

                                    # --- Similarity Score ---
                                    pdf.ln(5)
                                    if similarity_score is not None:
                                        safe_multicell(pdf, 0, 10, f"Similarity Score: {similarity_score}/100")

                                    # --- GPT Comparison Result ---
                                    pdf.ln(5)
                                    pdf.set_font("DejaVu", "B", 12)
                                    safe_multicell(pdf, 0, 10, "GPT Comparison Result:")
                                    pdf.set_font("DejaVu", size=11)
                                    safe_multicell(pdf, 0, 10, result_text)

                                    # --- Convert to BytesIO for Streamlit ---
                                    pdf_bytes = io.BytesIO(pdf.output(dest='S'))

                                    # --- Streamlit PDF Download Button ---
                                    st.download_button(
                                        label="📄 Download This Comparison as PDF",
                                        data=pdf_bytes,
                                        file_name=f"Primary_Secondary_comparison_{selected_Primary_level}_{selected_Secondary_level}.pdf",
                                        mime="application/pdf"
                                    )
                                
                            except Exception as e:
                                st.error(f"❌ API Error: {e}")

                # --- CSV Export ---
                if st.session_state.get("results"):
                    df = pd.DataFrame(st.session_state.results)
                    st.download_button(
                        label="📥 Download All Comparisons as CSV",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name="Primary_Secondary_comparisons.csv",
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

    elif auth_status is False:
        st.error("Incorrect username or password")
    elif auth_status is None:
        st.warning("Please enter your credentials")
else:
    st.error("Login form could not be rendered.")