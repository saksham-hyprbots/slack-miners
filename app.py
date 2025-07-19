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
    st.subheader("🔍 Search Decision Logs")
    search_query = st.text_input("Search for messages in decision logs:", placeholder="Enter keywords or phrases...")
    
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
            st.markdown("---")
            
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
                
                st.markdown(f"**User:** {user}  ")
                st.markdown(f"**Time:** {datetime.datetime.fromtimestamp(msg_time).strftime('%Y-%m-%d %H:%M:%S')}  ")
                st.markdown(f"**Original Message:** {row['message']}")
                st.markdown(f"**Summary of Follow-ups:** {summary}")
                st.markdown("---")
        else:
            st.info("No relevant decision log entries found for your search. Try different keywords.")
    else:
        # Show all decision logs when no search is performed
        st.subheader("📋 All Decision Logs")

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
            st.markdown(f"**User:** {log['user']}  ")
            st.markdown(f"**Time:** {log['timestamp']}  ")
            st.markdown(f"**Original Message:** {log['original']}")
            st.markdown(f"**Summary of Follow-ups:** {log['summary']}")
            st.markdown("---")

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
    matched_values = set([choices[i] for i, score, _ in matches if score > 60])
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
    user_filter = st.text_input("Fuzzy search user (initials, partial, etc.)")
    msg_filter = st.text_input("Fuzzy search message text")
    if user_filter:
        filtered_df = fuzzy_filter(filtered_df, 'user', user_filter)
    if msg_filter:
        filtered_df = fuzzy_filter(filtered_df, 'message', msg_filter)
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
    # --- Customizable columns ---
    if 'display_cols' not in st.session_state:
        st.session_state['display_cols'] = all_cols.copy()
    st.sidebar.markdown('### Dashboard Columns')
    selected_cols = st.sidebar.multiselect(
        'Choose columns to display:', all_cols, default=st.session_state['display_cols']
    )
    if st.sidebar.button('Save column preset'):
        st.session_state['display_cols'] = selected_cols
        st.sidebar.success('Column preset saved!')
    if not selected_cols:
        selected_cols = all_cols
    # --- Filter presets ---
    if 'filter_presets' not in st.session_state:
        st.session_state['filter_presets'] = {}
    preset_name = st.sidebar.text_input('Save current filters as preset (name):')
    if st.sidebar.button('Save filter preset') and preset_name:
        st.session_state['filter_presets'][preset_name] = {
            'user_filter': user_filter,
            'msg_filter': msg_filter,
            'columns': selected_cols
        }
        st.sidebar.success(f'Preset "{preset_name}" saved!')
    if st.sidebar.button('Load filter preset') and st.session_state['filter_presets']:
        preset_to_load = st.sidebar.selectbox('Choose preset to load:', list(st.session_state['filter_presets'].keys()))
        preset = st.session_state['filter_presets'][preset_to_load]
        user_filter = preset['user_filter']
        msg_filter = preset['msg_filter']
        selected_cols = preset['columns']
        st.rerun()
    display_cols = selected_cols
    if show_summary:
        st.markdown("### 🧮 Summary")
        for l in ["task", "bug", "blocker"]:
            count = filtered_df[filtered_df['label'] == l].shape[0]
            st.markdown(f"- **{l.capitalize()}s**: {count}")
    gb = GridOptionsBuilder.from_dataframe(filtered_df[display_cols])
    gb.configure_pagination()
    gb.configure_default_column(editable=True, groupable=True)
    gb.configure_selection('multiple', use_checkbox=True)
    # Render Slack Link column as HTML
    grid_response = AgGrid(filtered_df[display_cols], gridOptions=gb.build(), enable_enterprise_modules=False, return_mode='AS_INPUT', allow_unsafe_jscode=True, height=400, fit_columns_on_grid_load=True, reload_data=True, custom_css={".ag-cell": {"overflow": "visible"}}, enable_html=True)
    selected_rows = grid_response.get('selected_rows')
    if selected_rows is None:
        selected_rows = []
    selected_msgs = [
        row['message'] if isinstance(row, dict) and 'message' in row else str(row)
        for row in selected_rows
    ]
    # Multi-delete feature with confirmation
    if selected_rows is not None and len(selected_rows) > 0:
        st.warning(f"You have selected {len(selected_rows)} messages for deletion.")
        confirm = st.checkbox("I confirm I want to delete the selected messages.", key="confirm_delete_selected")
        if confirm:
            if st.button("Delete Selected Messages"):
                for row in selected_rows:
                    if isinstance(row, dict) and 'message' in row:
                        delete_message(message=row['message'])
                st.success(f"Deleted {len(selected_rows)} messages.")
                st.rerun()
    if st.button('Summarize Selected Messages'):
        summary = summarize_selected_messages(selected_msgs)
        st.markdown('#### Summary:')
        st.write(summary)
    if st.button('Extract Action Items from Selected Messages'):
        actions = extract_action_items(selected_msgs)
        st.markdown('#### Action Items:')
        st.write(actions)
    # Remove feedback loop: allow user to correct label
    # (Deleted code for label correction and feedback UI)

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