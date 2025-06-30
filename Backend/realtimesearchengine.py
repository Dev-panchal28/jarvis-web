# === Imports ===
from googlesearch import search
from groq import Groq
from flask import session
from dotenv import dotenv_values
import datetime
import psycopg2
import os

# === Load Environment Variables ===

GroqAPIKey = os.environ.get("GroqAPIKey")
Assistantname = os.environ.get("Assistantname", "Jarvis")
PG_USER = os.environ.get("PG_USER")
PG_PASS = os.environ.get("PG_PASS")
PG_HOST = os.environ.get("PG_HOST")
PG_DB = os.environ.get("PG_DB")

# === Initialize Groq Client ===
client = Groq(api_key=GroqAPIKey)

# === PostgreSQL Connection ===
def get_db():
    return psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        host=PG_HOST
    )

# === Google Search Helper ===
def GoogleSearch(query):
    try:
        results = list(search(query, advanced=True, num_results=5))
        answer = f"The search results for '{query}' are:\n[start]\n"
        for res in results:
            answer += f"Title: {res.title}\nDescription: {res.description}\n\n"
        answer += "[end]"
        return answer
    except Exception as e:
        return f"[start]\n⚠️ Failed to perform Google search: {e}\n[end]"

# === Answer Formatter ===
def AnswerModifier(Answer):
    return '\n'.join([line for line in Answer.split('\n') if line.strip()])

# === Real-time Info Helper ===
def Information():
    now = datetime.datetime.now()
    return (
        "Use this real-time information if needed:\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
        f"Time: {now.strftime('%H')} hours, {now.strftime('%M')} minutes, {now.strftime('%S')} seconds.\n"
    )

# === Main Function ===
def RealtimeSearchEngine(prompt):
    try:
        username = session.get("username", "User")

        system_prompt = (
            f"Hello, I am {username}, You are a very accurate and advanced AI chatbot named {Assistantname}, "
            f"which has real-time up-to-date information from the internet.\n"
            "*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar. ***\n"
            "*** Just answer the question from the provided data in a professional way. ***"
        )

        chat_context = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": GoogleSearch(prompt)},
            {"role": "system", "content": Information()},
            {"role": "user", "content": prompt},
        ]

        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=chat_context,
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=True
        )

        answer = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                answer += delta

        cleaned = AnswerModifier(answer)

        # ✅ No DB saving here anymore
        return cleaned

    except Exception as e:
        return f"❌ Error during real-time search: {e}"
