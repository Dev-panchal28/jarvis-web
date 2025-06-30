# === Backend/speak.py (complete version) ===
import asyncio
import edge_tts

async def generate_tts(text, filename="Data/speech.mp3", voice="en-CA-LiamNeural", rate="+10%"):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(filename)

# ✅ This is the callable from Flask
def speak_text(text, filename="Data/speech.mp3"):
    asyncio.run(generate_tts(text, filename))
