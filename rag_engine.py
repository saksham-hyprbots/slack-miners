import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_answer(query, retrieved_messages):
    context = "\n".join(retrieved_messages)
    prompt = f"""You are a helpful team assistant. Based on the following Slack history, answer the question:

Slack Messages:
{context}

Question:
{query}

Answer:"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()