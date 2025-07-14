from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)

model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text):
    logging.info(f"[Embeddings] Generating embedding for: {text}")
    embedding = model.encode([text])[0]
    logging.info(f"[Embeddings] Embedding shape: {embedding.shape}")
    return embedding.tolist()