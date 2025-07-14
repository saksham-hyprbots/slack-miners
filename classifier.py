import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def classify_message(text):
    prompt = f"What type of work item is this message?\n\n{text}\n\nRespond with one word: task, bug, blocker, or other."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response['choices'][0]['message']['content'].strip().lower()
