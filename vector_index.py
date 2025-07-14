import faiss
import numpy as np
from embeddings import generate_embedding
from mongo_store import get_all_embeddings
import logging

logging.basicConfig(level=logging.INFO)

class VectorIndex:
    def __init__(self, dim=384):  # MiniLM-L6-v2 has 384 dims
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.id_to_message = {}

    def build_index(self):
        logging.info("[VectorIndex] Building FAISS index...")
        self.index.reset()
        self.id_to_message.clear()
        embeddings = get_all_embeddings()
        vectors = []
        valid_indices = []
        for i, item in enumerate(embeddings):
            emb = np.array(item['embedding'], dtype='float32')
            if emb.shape[0] != self.dim:
                logging.warning(f"[VectorIndex] Skipping embedding with wrong dimension: {emb.shape[0]} (expected {self.dim}) for message: {item.get('message', '')[:50]}")
                continue
            vectors.append(emb)
            self.id_to_message[len(vectors)-1] = item['message']
        if vectors:
            self.index.add(np.array(vectors))
            logging.info(f"[VectorIndex] Added {len(vectors)} vectors to FAISS index.")
        else:
            logging.warning("[VectorIndex] No valid vectors to add to index!")

    def search(self, query, top_k=3):
        logging.info(f"[VectorIndex] Searching for: {query}")
        query_vec = np.array(generate_embedding(query)).reshape(1, -1).astype('float32')
        distances, indices = self.index.search(query_vec, top_k)
        return [(self.id_to_message[i], distances[0][j]) for j, i in enumerate(indices[0])]
