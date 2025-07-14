import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.slack_knowledge
collection = db.embeddings

def store_embedding(message, embedding, label=None, user=None, ts=None):
    collection.insert_one({
        "message": message,
        "embedding": embedding,
        "label": label,
        "user": user,
        "timestamp": ts
    })

def get_all_embeddings():
    return list(collection.find({}, {"_id": 0, "message": 1, "embedding": 1, "label": 1, "user": 1, "timestamp": 1}))
