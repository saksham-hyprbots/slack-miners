import streamlit as st
import pandas as pd
from vector_index import VectorIndex
from slack_ingest import fetch_latest_messages
from rag_engine import generate_answer
from mongo_store import get_all_embeddings
import datetime

st.set_page_config(page_title="Slack RAG Assistant", layout="wide")
st.title("💬 Slack RAG Knowledge Assistant")

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

with st.expander("📋 Team Task Dashboard"):
    data = get_all_embeddings()
    df = pd.DataFrame(data)

    label_filter = st.selectbox("Filter by type", ["all", "task", "bug", "blocker"])
    user_filter = st.text_input("Filter by user name (optional)")

    filtered_df = df.copy()
    if label_filter != "all":
        filtered_df = filtered_df[filtered_df['label'] == label_filter]
    if user_filter:
        filtered_df = filtered_df[filtered_df['user'].str.lower() == user_filter.lower()]

    filtered_df['timestamp'] = filtered_df['timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(float(x)).strftime('%Y-%m-%d %H:%M:%S') if x else '')

    st.markdown("### 🧮 Summary")
    for l in ["task", "bug", "blocker"]:
        count = df[df['label'] == l].shape[0]
        st.markdown(f"- **{l.capitalize()}s**: {count}")

    st.dataframe(filtered_df[['message', 'label', 'user', 'timestamp']])