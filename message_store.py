messages = []

def add_message(msg):
    messages.append(msg)

def get_messages():
    return messages


def load_sample_messages():
    sample = [
        "We fixed the login bug by updating the OAuth token refresh logic.",
        "The payment service failed due to a timeout on the vendor API.",
        "Let's switch to PostgreSQL for better transaction support.",
        "How do I setup the dev environment for the new repo?",
        "Reminder: release v1.2 goes live on Friday.",
        "Use Docker to run the microservices locally.",
        "We deprecated the old auth system in favor of JWT.",
        "Production crashed due to a missing env variable.",
        "Make sure to update the README after changing the setup.",
        "Sprint planning moved to Wednesday this week."
    ]
    messages.extend(sample)