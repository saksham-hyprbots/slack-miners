import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from classifier import classify_message
from mongo_store import store_embedding
from embeddings import generate_embedding

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

client = WebClient(token=SLACK_TOKEN)

def get_user_map():
    try:
        users = client.users_list()["members"]
        return {user["id"]: user.get("real_name", "Unknown") for user in users}
    except SlackApiError as e:
        print(f"Failed to fetch user map: {e.response['error']}")
        return {}

def fetch_latest_messages(limit=100):
    user_map = get_user_map()
    try:
        result = client.conversations_history(channel=CHANNEL_ID, limit=limit)
        for msg in result['messages']:
            if 'text' in msg:
                text = msg['text']
                user_id = msg.get('user', 'unknown')
                user_name = user_map.get(user_id, 'unknown')
                ts = msg.get('ts')
                label = classify_message(text)
                embedding = generate_embedding(text)
                store_embedding(text, embedding, label=label, user=user_name, ts=ts)
    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
