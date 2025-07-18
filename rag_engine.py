import os
import logging
import re
from groq_helper import generate_text

logging.basicConfig(level=logging.INFO)

def generate_answer(query, retrieved_texts):
    context = "\n".join(retrieved_texts)
    logging.info(f"[RAG Engine] Generating answer for query: {query}")
    prompt = (
        f"Given the following Slack messages:\n{context}\n"
        f"Answer the following question concisely:\n{query}\n"
        "Respond ONLY with the answer after 'Answer:'.\nAnswer:"
    )
    content = generate_text(prompt)
    logging.info(f"[RAG Engine] Raw model response: {content}")

    # Extract everything after the last </think> tag
    if "</think>" in content:
        answer = content.split("</think>")[-1].strip()
    else:
        # Try to extract the last answer after 'Answer:'
        matches = re.findall(r"answer[:\s\*]*([\s\S]+)", content, re.IGNORECASE)
        if matches:
            answer = matches[-1].strip().split('\n')[0].strip()
        else:
            # fallback: take the last non-empty line
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            answer = lines[-1] if lines else ""
    logging.info(f"[RAG Engine] Final answer: {answer}")
    return answer