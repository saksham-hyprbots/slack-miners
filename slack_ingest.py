import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from classifier import classify_message
from mongo_store import store_embedding, message_exists
from embeddings import generate_embedding
from dotenv import load_dotenv
import time
import logging
load_dotenv('a.env')

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")

client = WebClient(token=SLACK_TOKEN)


def get_user_map():
    try:
        users = client.users_list()["members"]
        return {user["id"]: user.get("real_name", "Unknown") for user in users}
    except SlackApiError as e:
        print(f"Failed to fetch user map: {e.response['error']}")
        return {}


def get_all_channel_ids():
    channel_ids = []
    cursor = None
    while True:
        try:
            response = client.conversations_list(
                types="public_channel,private_channel",
                limit=1000,
                cursor=cursor
            )
            for channel in response["channels"]:
                channel_ids.append(channel["id"])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        except SlackApiError as e:
            print(f"Error fetching channels: {e.response['error']}")
            break
    return channel_ids


def fetch_latest_messages(limit=100):
    user_map = get_user_map()
    channel_ids = get_all_channel_ids()
    new_count = 0
    for channel_id in channel_ids:
        try:
            result = client.conversations_history(channel=channel_id, limit=limit)
            for msg in result['messages']:
                if 'text' in msg:
                    ts = msg.get('ts')
                    if message_exists(ts):
                        continue  # Skip already processed messages
                    text = msg['text']
                    user_id = msg.get('user', 'unknown')
                    user_name = user_map.get(user_id, 'unknown')
                    label = classify_message(text)
                    embedding = generate_embedding(text)
                    thread_ts = msg.get('thread_ts', ts)  # Use ts if thread_ts not present
                    store_embedding(text, embedding, label=label, user=user_name, ts=ts, thread_ts=thread_ts, channel_id=channel_id)
                    new_count += 1
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                logging.warning(f"Slack API rate limited on channel {channel_id}. Backing off for 20 minutes.")
                time.sleep(1200)  # Sleep for 10 minutes if rate limited
            else:
                print(f"Slack API Error in channel {channel_id}: {e.response['error']}" )
    return new_count
