import csv
from collections import defaultdict
import openai

# ✅ Set your OpenAI API key
openai.api_key = "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"  # Replace this with your actual key

# ✅ Load ACQF levels
acqf_levels = defaultdict(list)

with open("acqf_levels.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    # Clean up header names (handle BOM issues)
    reader.fieldnames = [h.strip().lstrip('\ufeff') for h in reader.fieldnames]
    for row in reader:
        if not row or not row.get('Level') or not row.get('Domain') or not row.get('Descriptor'):
            continue
        level = row['Level'].strip()
        domain = row['Domain'].strip()
        descriptor = row['Descriptor'].strip()
        acqf_levels[level].append(f"{domain}: {descriptor}")

# ✅ Load EQF levels (already ACQF-style)
eqf_levels = defaultdict(list)

with open("eqf_levels_cleaned.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    reader.fieldnames = [h.strip().lstrip('\ufeff') for h in reader.fieldnames]
    for row in reader:
        if not row or not row.get('Level') or not row.get('Domain') or not row.get('Descriptor'):
            continue
        level = row['Level'].strip()
        domain = row['Domain'].strip()
        descriptor = row['Descriptor'].strip()
        eqf_levels[level].append(f"{domain}: {descriptor}")

# ✅ Compare each ACQF level to each EQF level
for acqf_level, acqf_descriptors in acqf_levels.items():
    acqf_text = "\n".join(acqf_descriptors)
    print(f"\n=== ACQF Level {acqf_level} ===")

    for eqf_level, eqf_descriptors in eqf_levels.items():
        eqf_text = "\n".join(eqf_descriptors)

        prompt = f"""
Compare the following qualification level descriptors and assess their equivalence.

ACQF Level {acqf_level}:
{acqf_text}

EQF Level {eqf_level}:
{eqf_text}

Are these levels equivalent? Highlight similarities and differences. Suggest the most appropriate EQF level match.
"""

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in qualifications frameworks and international education systems."},
                {"role": "user", "content": prompt}
            ]
        )

        print(f"\n--- Comparison with EQF Level {eqf_level} ---")
        print(response.choices[0].message['content'])
