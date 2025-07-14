# To use a free MongoDB Atlas cluster, set your .env or a.env like:
# MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
# Replace <username>, <password>, and cluster address with your Atlas details.

import streamlit as st
import pandas as pd
from vector_index import VectorIndex
from slack_ingest import fetch_latest_messages
from rag_engine import generate_answer
from mongo_store import get_all_embeddings
import datetime
import threading
import time
import logging
from dotenv import load_dotenv
load_dotenv('a.env')

logging.basicConfig(level=logging.INFO)

def background_fetcher():
    while True:
        new_count = fetch_latest_messages()
        if new_count == 0:
            logging.info("[Slack Fetcher] No new messages found.")
        else:
            logging.info(f"[Slack Fetcher] Fetched {new_count} new messages.")
        time.sleep(120)  # Fetch every 60 seconds

# Start background fetcher thread
fetcher_thread = threading.Thread(target=background_fetcher, daemon=True)
fetcher_thread.start()

# --- Custom CSS for better button design ---
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #4F8BF9;
        color: white;
        font-size: 18px;
        border-radius: 8px;
        padding: 0.5em 2em;
        margin-bottom: 1em;
        border: none;
        transition: background 0.2s;
    }
    .stButton>button:hover {
        background-color: #1746A2;
        color: #fff;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# --- End Custom CSS ---

st.set_page_config(page_title="Slack RAG Assistant", layout="wide")

# Sidebar navigation
st.sidebar.title("Navigation")
tab = st.sidebar.radio(
    "Go to",
    [
        "Prioritized Tasks",
        "Bugs",
        "Blockers",
        "Important",
        "All",
        "AI Chat"
    ]
)

def extract_tagged_users(message):
    import re
    return re.findall(r"<@([A-Z0-9]+)>", message)

def render_dashboard(filtered_df, show_summary=True):
    user_filter = st.text_input("Filter by user name (optional)")
    if user_filter:
        # Use regex/partial matching for user name (case-insensitive)
        filtered_df = filtered_df[filtered_df['user'].str.contains(user_filter, case=False, na=False, regex=True)]
    filtered_df['timestamp'] = filtered_df['timestamp'].apply(
        lambda x: datetime.datetime.fromtimestamp(float(x)).strftime('%Y-%m-%d %H:%M:%S') if x else ''
    )
    filtered_df['tagged_users'] = filtered_df['message'].apply(extract_tagged_users)
    if show_summary:
        st.markdown("### 🧮 Summary")
        for l in ["task", "bug", "blocker"]:
            count = filtered_df[filtered_df['label'] == l].shape[0]
            st.markdown(f"- **{l.capitalize()}s**: {count}")
    st.dataframe(filtered_df[['message', 'label', 'user', 'timestamp', 'tagged_users']])

if tab != "AI Chat":
    st.title(f"📋 {tab}")
    data = get_all_embeddings()
    df = pd.DataFrame(data)
    if df.empty or 'label' not in df.columns:
        st.warning("No Slack messages found or data is not yet indexed. Please load messages from Slack.")
        st.stop()
    if tab == "Prioritized Tasks":
        filtered_df = df[df['label'] == 'task']
        render_dashboard(filtered_df, show_summary=False)
    elif tab == "Bugs":
        filtered_df = df[df['label'] == 'bug']
        render_dashboard(filtered_df, show_summary=False)
    elif tab == "Blockers":
        filtered_df = df[df['label'] == 'blocker']
        render_dashboard(filtered_df, show_summary=False)
    elif tab == "Important":
        filtered_df = df[df['label'].isin(['task', 'bug', 'blocker'])]
        render_dashboard(filtered_df, show_summary=False)
    else:  # All
        filtered_df = df
        render_dashboard(filtered_df, show_summary=True)
else:
    st.title("💬 AI Chat with Slack Knowledge")
    if st.button("🔄 Load Messages from Slack"):
        fetch_latest_messages()
        st.success("Messages indexed from Slack!")
    query = st.text_input("🔍 Ask a question from team history:")
    if query:
        index = VectorIndex()
        index.build_index()
        results = index.search(query, top_k=5)
        st.subheader("📚 Retrieved Messages")
        for msg, score in results:
            st.markdown(f"- **{msg}** _(score: {score:.2f})_")
        with st.spinner("🧠 Generating answer..."):
            retrieved_texts = [msg for msg, _ in results]
            answer = generate_answer(query, retrieved_texts)
            st.subheader("💡 AI Answer")
            st.write(answer)
    else:
        st.info("Use the button above to fetch Slack messages.")