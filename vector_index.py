import faiss
import numpy as np
from embeddings import generate_embedding
from mongo_store import get_all_embeddings

class VectorIndex:
    def __init__(self, dim=1536):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.id_to_message = {}

    def build_index(self):
        self.index.reset()
        self.id_to_message.clear()
        embeddings = get_all_embeddings()
        vectors = []
        for i, item in enumerate(embeddings):
            vectors.append(np.array(item['embedding'], dtype='float32'))
            self.id_to_message[i] = item['message']
        self.index.add(np.array(vectors))

    def search(self, query, top_k=3):
        query_vec = np.array(generate_embedding(query)).reshape(1, -1).astype('float32')
        distances, indices = self.index.search(query_vec, top_k)
        return [(self.id_to_message[i], distances[0][j]) for j, i in enumerate(indices[0])]
