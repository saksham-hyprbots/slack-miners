import os
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('a.env')

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.slack_knowledge
collection = db.embeddings

def store_embedding(message, embedding, label=None, user=None, ts=None, thread_ts=None, channel_id=None):
    doc = {
        "message": message,
        "embedding": embedding,
        "label": label,
        "user": user,
        "timestamp": ts
    }
    if thread_ts is not None:
        doc["thread_ts"] = thread_ts
    if channel_id is not None:
        doc["channel_id"] = channel_id
    collection.insert_one(doc)

def get_all_embeddings():
    return list(collection.find({}, {"_id": 0, "message": 1, "embedding": 1, "label": 1, "user": 1, "timestamp": 1, "summary": 1, "thread_ts": 1, "channel_id": 1}))

def message_exists(ts):
    return collection.count_documents({"timestamp": ts}) > 0

def update_label(message, new_label):
    collection.update_one({"message": message}, {"$set": {"label": new_label}})

def update_summary(message, summary):
    collection.update_one({"message": message}, {"$set": {"summary": summary}})

def delete_message(message=None, ts=None):
    if message is not None:
        collection.delete_one({"message": message})
    elif ts is not None:
        collection.delete_one({"timestamp": ts})
