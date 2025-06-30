# === Imports ===
import os
import cohere
from dotenv import dotenv_values

# === Load API Key from .env ===
env_vars = dotenv_values(".env")
CohereAPIKey = env_vars.get("CohereAPIKey")

# === Raise error if not set ===
if not CohereAPIKey:
    raise ValueError("❌ CohereAPIKey not found in .env file")

# === Initialize Cohere Client ===
co = cohere.Client(api_key=CohereAPIKey)

# === Defined Function Tags ===
funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "system", "content", "google search", "youtube search", "reminder"
]

# === Preamble for Decision-Making Context ===
preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
"""

# === Training Examples for Chat Context ===
ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi"},
    {"role": "User", "message": "remind me that i have dancing performance on 5th aug at 11pm"},
    {"role": "Chatbot", "message": "reminder 11:00pm 5th aug dancing performance"},
]

# === Decision-Making Function ===
def FirstLayerDMM(prompt: str):
    try:
        stream = co.chat_stream(
            model='command-r-plus',
            message=prompt,
            temperature=0.7,
            chat_history=ChatHistory,
            prompt_truncation='OFF',
            connectors=[],
            preamble=preamble
        )

        raw_response = ""
        for event in stream:
            if event.event_type == "text-generation":
                raw_response += event.text

        # Extract relevant function tags
        response = raw_response.replace("\n", "").split(",")
        response = [r.strip() for r in response if any(r.strip().startswith(f) for f in funcs)]

        # Retry if invalid structure
        if any("(query)" in r for r in response):
            return FirstLayerDMM(prompt)

        return response

    except Exception as e:
        return [f"❌ Error in DMM: {e}"]

# === CLI Test Mode ===
if __name__ == "__main__":
    while True:
        query = input(">>> ")
        print(FirstLayerDMM(query))
