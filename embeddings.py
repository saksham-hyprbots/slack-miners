import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_embedding(text, model="text-embedding-3-small"):
    response = openai.Embedding.create(input=[text], model=model)
    return response['data'][0]['embedding']