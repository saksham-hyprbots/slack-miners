# slack-miners

**Unlock hidden insights from your Slack conversations using AI.**

*Slack Miners* is a powerful tool that extracts and analyzes messages from Slack channels to help you uncover key trends, priority tasks, blockers, bugs, and more — all in real time.

## **🔍 What is Slack Miners?**

Slack Miners is our world-class AI-powered tool that transforms your team’s Slack data into actionable insights. Whether it’s surfacing bugs, tracking blockers, or prioritizing tasks, Slack Miners helps you make sense of the chaos and stay on top of what matters.

Perfect for:

* Engineering teams tracking real-time issues
* Project managers identifying blockers
* Anyone tired of scrolling endlessly through Slack

## **⚙️ How to Run**

Follow these simple steps to get started:

1) Create a virtual environment python3 -m venv venv
2) then run source venv/bin/activate [To activate virtual environment]
3) pip3 install requirements.txt [In virtual env]
4) Then run streamlit run app.py.

## 🚀 Run with Docker

1. Build the Docker image:
   ```bash
   docker build -t slack-miners .
   ```
2. Run the app:
   ```bash
   docker run -p 8501:8501 --env-file a.env slack-miners
   ```

- The app will be available at http://localhost:8501
- Make sure your `a.env` file contains all required environment variables (API keys, MongoDB URI, etc.)

## **🧠 What’s Inside**

* 🧬 Real-time Slack message ingestion
* 📊 Web dashboard with smart classification (tasks, blockers, bugs)
* 🗂️ Filtering, summaries, and user-specific views
* 🤖 AI-based prioritization and trend detection

## **🛠️ Built With**

* Python
* Streamlit
* OpenAI / HuggingFace Embeddings
* MongoDB
* Slack APIs

## **💡 Ideas? Feedback? Contributions?**

This is just the beginning. Have cool ideas or want to collaborate? Open an issue or reach out — we’re building this for builders like you.
