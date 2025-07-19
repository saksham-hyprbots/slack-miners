import streamlit as st
import pandas as pd
from vector_index import VectorIndex
from slack_ingest import fetch_latest_messages
from rag_engine import generate_answer
from mongo_store import get_all_embeddings, store_embedding, update_label, delete_message
import datetime
import threading
import time
import logging
from dotenv import load_dotenv
from rapidfuzz import process, fuzz
from slack_sdk import WebClient
from st_aggrid import AgGrid, GridOptionsBuilder
import re
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import json
from streamlit_option_menu import option_menu

load_dotenv('a.env')

logging.basicConfig(level=logging.INFO)

# Remove authentication logic
# name, authentication_status, username = authenticate_user()
# st.write(name, authentication_status, username)

# st.title("Slack RAG Assistant (No Authentication)")
# st.write("Authentication has been removed. The app is now open to all users.")


# --- Custom CSS for better button design ---
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #5C5470;
        color: white;
        font-size: 18px;
        border-radius: 8px;
        padding: 0.5em 2em;
        margin-bottom: 1em;
        border: none;
        transition: background 0.2s;
    }
    .stButton>button:hover {
        background-color: #352F44;
        color: #fff;
    }
    
    /* Modern Search Bar Styling */
    .stTextInput > div > div > input {
        background-color: #2A2438;
        color: #fff;
        border: 2px solid #5C5470;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #DBD8E3;
        box-shadow: 0 0 0 2px rgba(219, 216, 227, 0.2);
        outline: none;
    }
    .stTextInput > div > div > input::placeholder {
        color: #9CA3AF;
    }
    
    /* Modern Card Styling for Decision Logs */
    .decision-log-card {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%);
        border: 1px solid #5C5470;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .decision-log-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* Modern Section Headers */
    .modern-header {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%);
        color: #fff;
        padding: 16px 24px;
        border-radius: 10px;
        margin: 20px 0;
        font-weight: 600;
        font-size: 1.2rem;
        border-left: 4px solid #DBD8E3;
    }
    
    /* Modern Success/Info Messages */
    .stSuccess {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #fff;
        border-radius: 10px;
        padding: 12px 16px;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .stInfo {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: #fff;
        border-radius: 10px;
        padding: 12px 16px;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Modern Warning Messages */
    .stWarning {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: #fff;
        border-radius: 10px;
        padding: 12px 16px;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Modern Divider */
    .modern-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #5C5470 50%, transparent 100%);
        margin: 20px 0;
        border-radius: 1px;
    }
    
    /* Modern Text Styling */
    .modern-text {
        color: #DBD8E3;
        line-height: 1.6;
    }
    
    .modern-label {
        color: #5C5470;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .modern-value {
        color: #DBD8E3;
        font-weight: 500;
        margin-bottom: 8px;
    }
    
    /* AgGrid Modern Dark Theme - Matching Sidebar */
    .ag-theme-alpine {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
        border: 2px solid #5C5470 !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        overflow: hidden !important;
    }
    
    /* Force all AgGrid elements to use our theme */
    div[class*="ag-theme-alpine"],
    .ag-theme-alpine,
    .ag-theme-alpine * {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
        color: #DBD8E3 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    .ag-theme-alpine .ag-header {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%) !important;
        border-bottom: 2px solid #DBD8E3 !important;
        color: #fff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        min-height: 60px !important;
    }
    
    .ag-theme-alpine .ag-header-cell {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%) !important;
        color: #fff !important;
        border-right: 1px solid rgba(219, 216, 227, 0.2) !important;
        padding: 16px 20px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    .ag-theme-alpine .ag-header-cell:hover {
        background: linear-gradient(135deg, #352F44 0%, #2A2438 100%) !important;
        transform: translateY(-1px) !important;
        transition: all 0.2s ease !important;
    }
    
    .ag-theme-alpine .ag-row {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
        border-bottom: 1px solid rgba(92, 84, 112, 0.3) !important;
        transition: all 0.2s ease !important;
        min-height: 50px !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    
    .ag-theme-alpine .ag-row:hover {
        background: linear-gradient(135deg, #352F44 0%, #2A2438 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    
    .ag-theme-alpine .ag-row.ag-row-selected {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%) !important;
        border-left: 4px solid #DBD8E3 !important;
        box-shadow: 0 4px 16px rgba(92, 84, 112, 0.4) !important;
    }
    
    .ag-theme-alpine .ag-cell {
        padding: 16px 20px !important;
        color: #DBD8E3 !important;
        border-right: 1px solid rgba(92, 84, 112, 0.3) !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        vertical-align: middle !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    .ag-theme-alpine .ag-cell:focus {
        outline: none !important;
        background: rgba(219, 216, 227, 0.1) !important;
        border-radius: 4px !important;
    }
    
    .ag-theme-alpine .ag-paging-panel {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
        border-top: 2px solid #5C5470 !important;
        color: #DBD8E3 !important;
        padding: 16px 20px !important;
        font-weight: 500 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    .ag-theme-alpine .ag-paging-button {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        margin: 0 6px !important;
        transition: all 0.2s ease !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    .ag-theme-alpine .ag-paging-button:hover {
        background: linear-gradient(135deg, #352F44 0%, #2A2438 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .ag-theme-alpine .ag-checkbox-input-wrapper {
        background: #2A2438 !important;
        border: 2px solid #5C5470 !important;
        border-radius: 6px !important;
        width: 18px !important;
        height: 18px !important;
        cursor: pointer !important;
        position: relative !important;
        z-index: 10 !important;
    }
    
    .ag-theme-alpine .ag-checkbox-input-wrapper.ag-checked {
        background: linear-gradient(135deg, #5C5470 0%, #352F44 100%) !important;
        border-color: #DBD8E3 !important;
    }
    
    .ag-theme-alpine .ag-checkbox-input-wrapper.ag-checked::after {
        content: '✓' !important;
        color: #DBD8E3 !important;
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        font-size: 12px !important;
        font-weight: bold !important;
    }
    
    /* Make sure the selection column is visible */
    .ag-theme-alpine .ag-cell[col-id="0"] {
        min-width: 50px !important;
        width: 50px !important;
    }
    
    /* Force override for any conflicting styles */
    div[class*="ag-theme-alpine"] {
        --ag-background-color: #2A2438 !important;
        --ag-foreground-color: #DBD8E3 !important;
        --ag-header-background-color: #5C5470 !important;
        --ag-header-foreground-color: #fff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    /* Additional force overrides */
    .ag-theme-alpine .ag-root-wrapper {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
    }
    
    .ag-theme-alpine .ag-root {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
    }
    
    .ag-theme-alpine .ag-body-viewport {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
    }
    
    .ag-theme-alpine .ag-body-viewport-wrapper {
        background: linear-gradient(135deg, #2A2438 0%, #352F44 100%) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# --- End Custom CSS ---

st.set_page_config(page_title="Slack RAG Assistant", layout="wide", initial_sidebar_state="auto")

st.markdown(
    """
    <style>
        [data-testid="stSidebarCollapseButton"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        position: absolute !important;
        z-index: -1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 300px;
        width: 300px;
        background-color: #2A2438;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .iconify {
        color: #fff !important;
    }
    .nav-link[aria-current="page"] .iconify {
        color: #2A2438 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #5C5470;
        color: #fff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Modern Sidebar Navigation ---
with st.sidebar:
    col1, col2 = st.columns([1, 3])  # Adjust the ratio as needed
    with col1:
        st.image("logo.png", width=48)
    with col2:
        st.markdown(
            """
                <div style='font-size:2rem; font-weight:700; letter-spacing:1px; margin-bottom:2rem;'>HyperSlack</div>
            """,
            unsafe_allow_html=True
        )
    selected_tab = option_menu(
        menu_title=None,
        options=[
            "Prioritized Tasks",
            "Bugs",
            "Blockers",
            "Important",
            "All",
            "AI Chat",
            "Expert Directory",
            "Decision Logs"
        ],
        icons=[
            "star-fill",  # Prioritized Tasks
            "bug-fill",   # Bugs
            "exclamation-triangle-fill",  # Blockers
            "bookmark-fill",  # Important
            "list-task",  # All
            "chat-dots-fill",  # AI Chat
            "person-lines-fill"  # Expert Directory
        ],
        menu_icon="cast",
        default_index=0,
        orientation="vertical",
        styles={
            "container": {"padding": "0!important", "background-color": "#2A2438"},
            "iconify": {"color": "#fff", "font-size": "1.2rem"},
            "nav-link": {"font-size": "1.1rem", "text-align": "left", "margin":"0.2rem 0", "padding": "0.7rem 1rem"},
            "nav-link-selected": {"background-color": "#DBD8E3", "color": "#2A2438", "font-weight": "bold"},
        }
    )

def summarize_selected_messages(selected_msgs):
    if not selected_msgs:
        return "No messages selected."
    prompt = "Summarize the following Slack messages in a concise way:\n" + "\n".join(selected_msgs)
    return generate_answer(prompt, selected_msgs)

def extract_action_items(selected_msgs):
    if not selected_msgs:
        return "No messages selected."
    prompt = "Extract all action items from the following Slack messages. Respond with a bullet list of action items only.\n" + "\n".join(selected_msgs)
    return generate_answer(prompt, selected_msgs)

# --- Expert Directory Data Store with Persistence ---
def load_experts():
    try:
        with open("experts.json", "r") as f:
            st.session_state['experts'] = json.load(f)
    except FileNotFoundError:
        st.session_state['experts'] = []

def save_experts():
    with open("experts.json", "w") as f:
        json.dump(st.session_state['experts'], f)

if 'experts' not in st.session_state:
    load_experts()

# Update add_expert to save after adding
def add_expert(name, expertise, slack_id):
    st.session_state['experts'].append({
        "name": name,
        "expertise": [tag.strip() for tag in expertise.split(",")],
        "slack_id": slack_id
    })
    save_experts()

# --- Expert Directory Page ---
if selected_tab == "Expert Directory":
    st.title("Expert Directory")
    with st.form("add_expert_form"):
        name = st.text_input("Expert Name")
        expertise = st.text_input("Expertise (comma-separated tags)")
        slack_id = st.text_input("Slack ID (e.g., U12345678)")
        submitted = st.form_submit_button("Add Expert")
        if submitted and name and expertise and slack_id:
            add_expert(name, expertise, slack_id)
            st.success(f"Added expert: {name}")

    st.subheader("Current Experts")
    for expert in st.session_state['experts']:
        st.markdown(
            f"**{expert['name']}** (Slack: `{expert['slack_id']}`)  \n"
            f"Expertise: {', '.join([f'`{tag}`' for tag in expert['expertise']])}"
        )

    # --- Expert Search Feature ---
    st.subheader("Find Experts for Multiple Tags")
    search_tags = st.text_input("Enter tags/topics (comma-separated, e.g., 'login, oauth, bug')", key="expert_search_multi")
    if search_tags:
        tag_list = [tag.strip().lower() for tag in search_tags.split(",") if tag.strip()]
        matches = []
        for expert in st.session_state['experts']:
            match_count = 0
            match_scores = []
            for search_tag in tag_list:
                for expert_tag in expert['expertise']:
                    score = fuzz.partial_ratio(expert_tag.lower(), search_tag)
                    if score > 60:
                        match_count += 1
                        match_scores.append(score)
                        break  # Only count each search tag once per expert
            if match_count > 0:
                avg_score = sum(match_scores) / len(match_scores) if match_scores else 0
                matches.append((match_count, avg_score, expert))
        if matches:
            # Sort by number of matches, then by average score
            matches.sort(reverse=True, key=lambda x: (x[0], x[1]))
            st.success("Matching experts:")
            for match_count, avg_score, expert in matches:
                st.markdown(
                    f"**{expert['name']}** (Slack: `{expert['slack_id']}`)  \n"
                    f"Expertise: {', '.join([f'`{tag}`' for tag in expert['expertise']])}  \n"
                    f"Matched tags: {match_count}  \n"
                    f"Average match score: {avg_score:.1f}"
                )
        else:
            st.info("No matching expert found. Try adding more experts or tags.")

# --- AI Chat Integration: Suggest Expert for Bug ---
def find_expert_for_bug(bug_description):
    best_score = 0
    best_expert = None
    for expert in st.session_state['experts']:
        for tag in expert['expertise']:
            score = fuzz.partial_ratio(tag.lower(), bug_description.lower())
            if score > best_score:
                best_score = score
                best_expert = expert
    if best_score > 60:
        return best_expert
    return None

if selected_tab == "AI Chat":
    st.title("AI Chat with Slack Knowledge")
    if st.button("🔄 Load Messages from Slack"):
        fetch_latest_messages()
        st.success("Messages indexed from Slack!")
    # Multi-turn chat: maintain chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    user_input = st.text_input("🔍 Ask a question from team history:")
    if st.button("Send") and user_input:
        st.session_state['chat_history'].append({"role": "user", "content": user_input})
        # Build context from chat history
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state['chat_history']])
        index = VectorIndex()
        index.build_index()
        results = index.search(user_input, top_k=5)
        retrieved_texts = [msg for msg, _ in results]
        # Pass chat history and retrieved texts to the model
        prompt = f"Context from Slack:\n{chr(10).join(retrieved_texts)}\n\nChat history:\n{context}\n\nAnswer the last user question based on the above."
        with st.spinner("🧠 Generating answer..."):
            answer = generate_answer(prompt, retrieved_texts)
        st.session_state['chat_history'].append({"role": "assistant", "content": answer})
    # Display chat history
    for msg in st.session_state['chat_history']:
        if msg['role'] == 'user':
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**AI:** {msg['content']}")
    st.info("Use the button above to fetch Slack messages.")

# --- Decision Logs Page ---
if selected_tab == "Decision Logs":
    st.title("Decision Logs")
    data = get_all_embeddings()
    df = pd.DataFrame(data)
    if df.empty or 'label' not in df.columns:
        st.warning("No Slack messages found or data is not yet indexed. Please load messages from Slack.")
        st.stop()
    # Ensure timestamp is float for comparison
    df['timestamp'] = df['timestamp'].astype(float)
    # Only consider important messages
    important_df = df[df['label'].isin(['task', 'bug', 'blocker'])]

    # --- Search Feature for Decision Logs ---
    st.markdown('<div class="modern-header">🔍 Search Decision Logs</div>', unsafe_allow_html=True)
    search_query = st.text_input("Search for messages in decision logs:", placeholder="Enter keywords or phrases...", key="decision_logs_search")
    
    if search_query:
        # Use semantic search to find relevant messages
        index = VectorIndex()
        index.build_index()
        search_results = index.search(search_query, top_k=10)
        
        # Filter search results to only important messages
        search_messages = [msg for msg, _ in search_results]
        filtered_important_df = important_df[important_df['message'].isin(search_messages)]
        
        if not filtered_important_df.empty:
            st.success(f"Found {len(filtered_important_df)} relevant decision log entries:")
            st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
            
            # Display search results
            for idx, row in filtered_important_df.iterrows():
                msg_time = float(row['timestamp'])
                user = row['user']
                thread_ts = row.get('thread_ts', None)
                # Find follow-ups: Prefer thread-based, else fallback to time/user-based
                if thread_ts and thread_ts in df['thread_ts'].values:
                    followups = df[(df['thread_ts'] == thread_ts) & (df['message'] != row['message'])]
                else:
                    followups = df[(df['user'] == user) & (df['timestamp'] > msg_time) & (df['timestamp'] <= msg_time + 86400) & (df['message'] != row['message'])]
                followup_msgs = followups['message'].tolist()
                # Show only stored summary if present
                summary = row.get('summary', None)
                if not summary:
                    summary = "No summary stored. Please generate summaries."
                
                st.markdown(f"""
                <div class="decision-log-card">
                    <div class="modern-label">User</div>
                    <div class="modern-value">{user}</div>
                    <div class="modern-label">Time</div>
                    <div class="modern-value">{datetime.datetime.fromtimestamp(msg_time).strftime('%Y-%m-%d %H:%M:%S')}</div>
                    <div class="modern-label">Original Message</div>
                    <div class="modern-value">{row['message']}</div>
                    <div class="modern-label">Summary of Follow-ups</div>
                    <div class="modern-value">{summary}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No relevant decision log entries found for your search. Try different keywords.")
    else:
        # Show all decision logs when no search is performed
        st.markdown('<div class="modern-header">📋 All Decision Logs</div>', unsafe_allow_html=True)

    # Button to generate and store summaries
    if st.button('Generate and Store Summaries for All Important Messages'):
        from mongo_store import update_summary
        import time
        for idx, row in important_df.iterrows():
            # Skip if summary already exists
            if row.get('summary', None):
                continue
            msg_time = float(row['timestamp'])
            user = row['user']
            thread_ts = row.get('thread_ts', None)
            # Find follow-ups: Prefer thread-based, else fallback to time/user-based
            if thread_ts and thread_ts in df['thread_ts'].values:
                followups = df[(df['thread_ts'] == thread_ts) & (df['message'] != row['message'])]
            else:
                followups = df[(df['user'] == user) & (df['timestamp'] > msg_time) & (df['timestamp'] <= msg_time + 86400) & (df['message'] != row['message'])]
            followup_msgs = followups['message'].tolist()
            if followup_msgs:
                summary = summarize_selected_messages(followup_msgs)
                update_summary(row['message'], summary)
                time.sleep(10)  # Add delay to avoid rate limits
        st.success('Summaries generated and stored for all important messages without a summary.')
        st.rerun()
    
    # Only show all logs if no search is being performed
    if not search_query:
        logs = []
        for idx, row in important_df.iterrows():
            msg_time = float(row['timestamp'])
            user = row['user']
            thread_ts = row.get('thread_ts', None)
            # Find follow-ups: Prefer thread-based, else fallback to time/user-based
            if thread_ts and thread_ts in df['thread_ts'].values:
                followups = df[(df['thread_ts'] == thread_ts) & (df['message'] != row['message'])]
            else:
                followups = df[(df['user'] == user) & (df['timestamp'] > msg_time) & (df['timestamp'] <= msg_time + 86400) & (df['message'] != row['message'])]
            followup_msgs = followups['message'].tolist()
            # Show only stored summary if present
            summary = row.get('summary', None)
            if not summary:
                summary = "No summary stored. Please generate summaries."
            logs.append({
                'original': row['message'],
                'followups': followup_msgs,
                'summary': summary,
                'user': user,
                'timestamp': datetime.datetime.fromtimestamp(msg_time).strftime('%Y-%m-%d %H:%M:%S')
            })
        # Display logs
        for log in logs:
            st.markdown(f"""
            <div class="decision-log-card">
                <div class="modern-label">User</div>
                <div class="modern-value">{log['user']}</div>
                <div class="modern-label">Time</div>
                <div class="modern-value">{log['timestamp']}</div>
                <div class="modern-label">Original Message</div>
                <div class="modern-value">{log['original']}</div>
                <div class="modern-label">Summary of Follow-ups</div>
                <div class="modern-value">{log['summary']}</div>
            </div>
            """, unsafe_allow_html=True)

# --- Theme toggle ---
# theme_choice = st.sidebar.selectbox('Theme', ['light', 'dark'], index=0)

# Helper to get Slack user and channel maps
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_TOKEN)

def get_user_map():
    try:
        users = slack_client.users_list()["members"]
        return {user["id"]: user.get("real_name", "Unknown") for user in users}
    except Exception:
        return {}

def get_channel_map():
    try:
        channels = slack_client.conversations_list(types="public_channel,private_channel", limit=1000)["channels"]
        return {ch["id"]: ch["name"] for ch in channels}
    except Exception:
        return {}

user_map = get_user_map()
channel_map = get_channel_map()

def extract_tagged_users(message):
    ids = re.findall(r"<@([A-Z0-9]+)>", message)
    return [user_map.get(uid, uid) for uid in ids]

def extract_channel_id(message):
    match = re.search(r"<#([A-Z0-9]+)\|?[^>]*>", message)
    if match:
        return channel_map.get(match.group(1), match.group(1))
    return None

def fuzzy_filter(df, col, query):
    if not query:
        return df
    choices = df[col].astype(str).tolist()
    matches = process.extract(query, choices, scorer=fuzz.partial_ratio, limit=len(choices))
    # Fix: process.extract returns (choice, score, index) tuples
    matched_values = set([choice for choice, score, index in matches if score > 60])
    return df[df[col].astype(str).isin(matched_values)]


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

def render_dashboard(filtered_df, show_summary=True):
    # Create a container for better organization
    with st.container():
        # Header section with better spacing
        st.markdown("---")
        
        # Search filters in a nice layout
        col1, col2 = st.columns(2)
        with col1:
            user_filter = st.text_input("🔍 Search by user", placeholder="Enter user name or initials...")
        with col2:
            msg_filter = st.text_input("🔍 Search by message", placeholder="Enter keywords...")
        
        # Apply filters
        if user_filter:
            filtered_df = fuzzy_filter(filtered_df, 'user', user_filter)
        if msg_filter:
            filtered_df = fuzzy_filter(filtered_df, 'message', msg_filter)
        
        # Process data
        filtered_df['timestamp'] = filtered_df['timestamp'].apply(
            lambda x: datetime.datetime.fromtimestamp(float(x)).strftime('%Y-%m-%d %H:%M:%S') if x else ''
        )
        filtered_df['tagged_users'] = filtered_df['message'].apply(extract_tagged_users)
        filtered_df['channel'] = filtered_df['message'].apply(extract_channel_id)

        # --- Add Slack Link column ---
        TEAM_ID = os.getenv('SLACK_TEAM_ID', 'T096DH6RKHN')  # Set your real team ID in .env
        def slack_link(row):
            channel_id = row.get('channel_id')
            ts = row.get('timestamp')
            if not channel_id or not ts:
                return ''
            # Convert formatted timestamp back to Slack ts format (remove non-digits)
            ts_raw = str(row['timestamp'])
            ts_slack = ts_raw.replace('.', '')
            url = f"https://app.slack.com/client/{TEAM_ID}/{channel_id}/thread/{channel_id}-{ts_slack}"
            return f'<a href="{url}" target="_blank">View in Slack</a>'
        filtered_df['Slack Link'] = filtered_df.apply(slack_link, axis=1)

        all_cols = ['message', 'label', 'user', 'timestamp', 'tagged_users', 'channel', 'Slack Link']
        
        # Sidebar controls in a better layout
        with st.sidebar:
            st.markdown("### 📊 Dashboard Controls")
            
            # Column selection
            st.markdown("**Choose columns to display:**")
            if 'display_cols' not in st.session_state:
                st.session_state['display_cols'] = all_cols.copy()
            selected_cols = st.multiselect(
                'Select columns:', all_cols, default=st.session_state['display_cols']
            )
            if st.button('💾 Save column preset', key='save_cols'):
                st.session_state['display_cols'] = selected_cols
                st.success('Column preset saved!')
            
            st.markdown("---")
            
            # Filter presets
            st.markdown("**Filter Presets:**")
            if 'filter_presets' not in st.session_state:
                st.session_state['filter_presets'] = {}
            
            preset_name = st.text_input('Save current filters as preset:', key='preset_name')
            col_save, col_load = st.columns(2)
            with col_save:
                if st.button('💾 Save preset') and preset_name:
                    st.session_state['filter_presets'][preset_name] = {
                        'user_filter': user_filter,
                        'msg_filter': msg_filter,
                        'columns': selected_cols
                    }
                    st.success(f'Preset "{preset_name}" saved!')
            
            with col_load:
                if st.button('📂 Load preset') and st.session_state['filter_presets']:
                    preset_to_load = st.selectbox('Choose preset:', list(st.session_state['filter_presets'].keys()))
                    preset = st.session_state['filter_presets'][preset_to_load]
                    user_filter = preset['user_filter']
                    msg_filter = preset['msg_filter']
                    selected_cols = preset['columns']
                    st.rerun()
        
        if not selected_cols:
            selected_cols = all_cols
        display_cols = selected_cols
        
        # Summary section with better styling
        if show_summary:
            st.markdown("### 📈 Summary Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                task_count = filtered_df[filtered_df['label'] == 'task'].shape[0]
                st.metric("Tasks", task_count)
            with col2:
                bug_count = filtered_df[filtered_df['label'] == 'bug'].shape[0]
                st.metric("Bugs", bug_count)
            with col3:
                blocker_count = filtered_df[filtered_df['label'] == 'blocker'].shape[0]
                st.metric("Blockers", blocker_count)
        
        # Configure grid options
        gb = GridOptionsBuilder.from_dataframe(filtered_df[display_cols])
        gb.configure_pagination()
        gb.configure_default_column(editable=True, sortable=True, resizable=True)
        gb.configure_selection('multiple', use_checkbox=True, pre_selected_rows=[])
        
        # Configure row selection with new API
        grid_options = gb.build()
        
        # Simplified grid options for better compatibility
        grid_options.update({
            'domLayout': 'normal',
            'rowHeight': 50,
            'headerHeight': 60,
            'theme': 'ag-theme-alpine',
            'rowSelection': 'multiple',
            'suppressRowClickSelection': False,
            'rowMultiSelectWithClick': True
        })
        
        # Convert object columns to strings to avoid serialization issues
        display_df = filtered_df[display_cols].copy()
        for col in display_cols:
            if col in ['tagged_users', 'channel']:
                display_df[col] = display_df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
        
        # Format column headers to be more readable and standard
        column_headers = {
            'message': 'Message',
            'label': 'Label',
            'user': 'User',
            'timestamp': 'Timestamp',
            'tagged_users': 'Tagged Users',
            'channel': 'Channel',
            'Slack Link': 'Slack Link'
        }
        
        # Rename columns for better display
        display_df = display_df.rename(columns=column_headers)
        
        # Update grid options to match renamed columns
        if 'columnDefs' in grid_options:
            for col_def in grid_options['columnDefs']:
                old_field = col_def.get('field', '')
                if old_field in column_headers:
                    new_field = column_headers[old_field]
                    col_def['field'] = new_field
                    col_def['headerName'] = new_field
        
        # Table section with better spacing
        st.markdown("### 📋 Slack Messages")
        st.markdown("*Use the controls in the sidebar to customize your view*")
        
        # Render Slack Link column as HTML
        grid_response = AgGrid(
            display_df, 
            gridOptions=grid_options, 
            enable_enterprise_modules=False, 
            return_mode='AS_INPUT', 
            allow_unsafe_jscode=True, 
            height=500, 
            fit_columns_on_grid_load=True, 
            reload_data=True, 
            enable_html=True,
            custom_css={
                ".ag-theme-alpine": {
                    "background": "linear-gradient(135deg, #2A2438 0%, #352F44 100%)",
                    "border": "2px solid #5C5470",
                    "border-radius": "12px",
                    "box-shadow": "0 8px 32px rgba(0, 0, 0, 0.3)",
                    "font-family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                },
                ".ag-theme-alpine .ag-header": {
                    "background": "linear-gradient(135deg, #5C5470 0%, #352F44 100%)",
                    "color": "#fff",
                    "font-weight": "600",
                    "text-transform": "uppercase"
                },
                ".ag-theme-alpine .ag-row": {
                    "background": "linear-gradient(135deg, #2A2438 0%, #352F44 100%)",
                    "color": "#DBD8E3"
                },
                ".ag-theme-alpine .ag-cell": {
                    "color": "#DBD8E3",
                    "font-family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                }
            }
        )
        
        selected_rows = grid_response.get('selected_rows')
        if selected_rows is None:
            selected_rows = []
        
        # Convert DataFrame to list of dictionaries if needed
        if hasattr(selected_rows, 'to_dict'):
            selected_rows = selected_rows.to_dict('records')
        elif not isinstance(selected_rows, list):
            selected_rows = []
        
        # Debug information
        st.write(f"Debug: Selected rows count: {len(selected_rows)}")
        if len(selected_rows) > 0:
            st.write(f"Debug: First selected row keys: {list(selected_rows[0].keys()) if selected_rows else 'None'}")
        
        selected_msgs = [
            row['Message'] if isinstance(row, dict) and 'Message' in row else str(row)
            for row in selected_rows
        ]
        
        # Action buttons in a better layout
        if selected_rows is not None and len(selected_rows) > 0:
            st.markdown("### ⚡ Actions for Selected Messages")
            st.warning(f"You have selected {len(selected_rows)} messages.")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                confirm = st.checkbox("I confirm I want to delete the selected messages.", key="confirm_delete_selected")
            with col2:
                if confirm and st.button("🗑️ Delete Selected Messages"):
                    for row in selected_rows:
                        if isinstance(row, dict) and 'Message' in row:
                            delete_message(message=row['Message'])
                    st.success(f"Deleted {len(selected_rows)} messages.")
                    st.rerun()
            with col3:
                if st.button('📊 Summarize Selected Messages'):
                    summary = summarize_selected_messages(selected_msgs)
                    st.markdown('#### Summary:')
                    st.write(summary)
            
            if st.button('📝 Extract Action Items from Selected Messages'):
                actions = extract_action_items(selected_msgs)
                st.markdown('#### Action Items:')
                st.write(actions)
        else:
            st.info("💡 Select messages from the table above to perform actions.")

# Semantic search bar and results
if selected_tab not in ["AI Chat", "Expert Directory", "Decision Logs"]:
    st.title(f"📋 {selected_tab}")
    data = get_all_embeddings()
    df = pd.DataFrame(data)
    if df.empty or 'label' not in df.columns:
        st.warning("No Slack messages found or data is not yet indexed. Please load messages from Slack.")
        st.stop()
    semantic_query = st.text_input("Semantic search (AI-powered, finds similar messages by meaning)")
    semantic_results = None
    if semantic_query:
        index = VectorIndex()
        index.build_index()
        results = index.search(semantic_query, top_k=10)
        semantic_results = pd.DataFrame([
            {"message": msg, "score": score} for msg, score in results
        ])
        st.markdown("#### Top 10 Semantic Matches:")
        st.dataframe(semantic_results)
    if selected_tab == "Prioritized Tasks":
        filtered_df = df[df['label'] == 'task']
        render_dashboard(filtered_df, show_summary=False)
    elif selected_tab == "Bugs":
        filtered_df = df[df['label'] == 'bug']
        render_dashboard(filtered_df, show_summary=False)
    elif selected_tab == "Blockers":
        filtered_df = df[df['label'] == 'blocker']
        render_dashboard(filtered_df, show_summary=False)
    elif selected_tab == "Important":
        filtered_df = df[df['label'].isin(['task', 'bug', 'blocker'])]
        render_dashboard(filtered_df, show_summary=False)
    else:  # All
        filtered_df = df
        render_dashboard(filtered_df, show_summary=True)