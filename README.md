# ACQF-EQF Comparator

**Smarter Learning Outcomes Levelling with Generative AI – by Ascendra**

This Streamlit app compares learning outcome descriptors from two qualification frameworks and generates a similarity score using GPT-4o.

## Features

- Upload two CSV files: one for your **Primary Framework**, one for the **Secondary Framework**
- Select levels from each
- View detailed descriptor comparisons and similarity score
- Export results to PDF or CSV

## Deployment

To deploy locally:

```bash
git clone https://github.com/james-keevy/acqf-eqf-comparator.git
cd acqf-eqf-comparator
pip install -r requirements.txt
streamlit ascendra.py
