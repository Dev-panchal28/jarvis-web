# === Imports ===
import os
import re
import webbrowser
from flask import session
from datetime import datetime
from dotenv import dotenv_values
from groq import Groq

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jarvis_db import get_user_by_name, save_user_file



# === Load environment variables ===
env = dotenv_values(".env")

GroqAPIKey = env.get("GroqAPIKey")


# === PostgreSQL-backed AI Content Writer ===
def WriteContent(prompt):
    try:
        if not GroqAPIKey:
            return "❌ Groq API Key not found."

        # Load current username from session
        Username = session.get("username", "User")

        # Construct message context
        messages = [
            {
                "role": "system",
                "content": f"Hello, I am {Username}. You're a content writer. You have to write content like letters, codes, applications, essays, notes, songs, poems etc."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Generate content using Groq
        client = Groq(api_key=GroqAPIKey)
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=False
        )

        # Extract answer
        choice = completion.choices[0]
        message = getattr(choice, "message", None)
        answer = message.content if message else str(choice)
        answer = answer.replace("</s>", "")

        # Safe filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', prompt.lower())
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_name}_{timestamp}.txt"

        # Save to DB
        user = get_user_by_name(Username)
        if not user:
            return "❌ Error: User not found in database."

        user_id = user["id"]
        save_user_file(user_id, filename, answer)

        return f"✅ Content generated! <a href='/download/{filename}' target='_blank'>Download here</a>"

    except Exception as e:
        return f"❌ Error using Groq API: {e}"


# === Open Website Helper ===
def OpenSite(app):
    if not app.startswith("http"):
        app = f"https://www.{app.lower().replace(' ', '')}.com"
    webbrowser.open(app)
    return f"🌐 Opening {app} in browser"


# === Web Search Utilities ===
def GoogleSearch(topic):
    webbrowser.open(f"https://www.google.com/search?q={topic}")
    return f"🔍 Google search started for '{topic}'"

def YouTubeSearch(topic):
    webbrowser.open(f"https://www.youtube.com/results?search_query={topic}")
    return f"🎮 YouTube search started for '{topic}'"


# === Command Handler for Web Interface ===
def run_automation(command: str):
    command = command.lower().strip()

    if command.startswith("open "):
        app = command.replace("open ", "")
        return f"Opening <a href='https://{app.lower()}.com' target='_blank'>{app}</a> in your browser."

    elif command.startswith("play "):
        query = command.replace("play ", "")
        return f"Playing <a href='https://www.youtube.com/results?search_query={query}' target='_blank'>{query}</a> on YouTube."

    elif command.startswith("google search "):
        topic = command.replace("google search ", "")
        return f"Searching Google for <a href='https://www.google.com/search?q={topic}' target='_blank'>{topic}</a>."

    elif command.startswith("write ") or command.startswith("generate "):
        return WriteContent(command)

    return "❌ This command cannot be run in web version."
