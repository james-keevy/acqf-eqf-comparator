import csv
from collections import defaultdict

# Load and group descriptors by level
acqf_levels = defaultdict(list)

with open('acqf_levels.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if not row or not row['Level'] or not row['Domain'] or not row['Descriptor']:
            continue  # Skip empty or malformed rows

        level = row['Level'].strip()
        domain = row['Domain'].strip()
        descriptor = row['Descriptor'].strip()
        acqf_levels[level].append(f"{domain}: {descriptor}")

# Example: print ACQF Level 1 descriptors
for level, descriptors in acqf_levels.items():
    print(f"\nACQF Level {level}")
    print("\n".join(descriptors))
