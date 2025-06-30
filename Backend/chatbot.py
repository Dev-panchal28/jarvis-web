# === File: chatbot.py (PostgreSQL Only + .env) ===

from groq import Groq
from flask import session
from dotenv import dotenv_values
import datetime
import os
import psycopg2

# === Load Environment Variables from .env ===
env = dotenv_values(".env")

Assistantname = env.get("Assistantname", "Jarvis")
GroqAPIKey = env.get("GroqAPIKey")

PG_DB = env.get("PG_DB")
PG_USER = env.get("PG_USER")
PG_PASS = env.get("PG_PASS")
PG_HOST = env.get("PG_HOST")
PG_PORT = env.get("PG_PORT", "5432")

# === Initialize Groq Client ===
client = Groq(api_key=GroqAPIKey)

# === PostgreSQL Connection ===
def get_pg_conn():
    return psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        host=PG_HOST,
        port=PG_PORT
    )

# === System Prompt Generator ===
def build_system_prompt():
    user = session.get("username", "User")
    return f"""Hello, I am {user}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

# === Real-time Info String ===
def RealtimeInformation():
    now = datetime.datetime.now()
    return (
        f"Please use this real-time information if needed,\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
        f"Time: {now.strftime('%H')} hours :"
        f"{now.strftime('%M')} minutes :"
        f"{now.strftime('%S')} seconds.\n"
    )

# === Cleanup Response ===
def AnswerModifier(Answer):
    return '\n'.join([line for line in Answer.split('\n') if line.strip()])

# === Main Chat Interface ===
def Chat(query):
    try:
        username = session.get("username")
        context = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "system", "content": RealtimeInformation()},
            {"role": "user", "content": query}
        ]

        # === Get AI Response ===
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=context,
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stream=False
        )

        answer = completion.choices[0].message.content.replace("</s>", "")
        answer = AnswerModifier(answer)

        # ✅ Do not store chat here anymore (already done in app.py)
        return answer

    except Exception as e:
        print(f"[Chatbot Error] {e}")
        return "❌ Sorry, something went wrong while processing your request."
