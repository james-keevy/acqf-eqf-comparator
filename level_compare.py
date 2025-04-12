import openai

openai.api_key = "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"  # Your actual API key

response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are an expert in comparing international qualification frameworks."},
        {"role": "user", "content": """
Compare the following level descriptors from the European Qualifications Framework (EQF) and the Australian Qualifications Framework (AQF):

EQF Level 5:
Comprehensive, specialized, factual and theoretical knowledge within a field of work or study and an awareness of the boundaries of that knowledge.

AQF Level 5:
Graduates at this level will have technical and theoretical knowledge in a specific area or a broad field of work and learning.

Identify similarities, differences, and propose a likely equivalence.
"""}
    ]
)

print(response.choices[0].message['content'])
