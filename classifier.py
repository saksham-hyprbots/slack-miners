import os
from dotenv import load_dotenv
load_dotenv('a.env')
import ollama
import logging
import re

logging.basicConfig(level=logging.INFO)

def classify_message(text):
    logging.info(f"[Classifier] Classifying message: {text}")
    prompt = (
        "Classify the following message as one of: task, bug, blocker, or other.\n"
        f"Message: {text}\n"
        "Respond ONLY with the label word (task, bug, blocker, or other) and nothing else. Label:"
    )
    response = ollama.chat(model='deepseek-r1', messages=[{'role': 'user', 'content': prompt}])
    content = response['message']['content']
    logging.info(f"[Classifier] Raw model response: {content}")

    # Try to extract the last label from the response
    matches = re.findall(r"label[:\\s\\*]*([a-zA-Z]+)", content, re.IGNORECASE)
    if matches:
        label = matches[-1].strip().lower()
    else:
        # fallback: just take the last word
        label = content.strip().split()[-1].lower()
    if label not in ["task", "bug", "blocker", "other"]:
        label = "other"
    logging.info(f"[Classifier] Final label: {label}")
    return label
