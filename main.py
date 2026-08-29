import time
import random
import logging
import json
import urllib.request
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Pure Gemini AI Response Generator (Direct REST API)
def get_ai_response(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool Indian friend chatting on Telegram. Reply in 100% natural, casual Hinglish (Hindi words in English script).

Rules:
1. Understand chat short-forms & slang:
   - "kkrh" / "kya kr rha h" -> "kuch nahi bhai, bas phone chala raha hu. tu bata?"
   - "kidar h" -> "ghar pe hi hu bhai, tu bata kya scene?"
   - "kaisa h" -> "ekdum badhiya bhai, tu suna kaisa hai?"
   - "hi" / "yoo" / "oye" -> "haan bhai bol kya haal chaal?"
2. Reply in 1 short, dynamic line like a real person.
3. NEVER repeat the same canned answer. Always reply according to the message.
4. If asked for link/group, share: {GROUP_LINK}

User ({sender_name}) says: "{user_text}"
Your short Hinglish reply:"""

    # Active fast models on your account
    active_models = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash"
    ]

    for model_name in active_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 70
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                reply = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if reply:
                    return reply
        except Exception as e:
            logging.error(f"Error on {model_name}: {e}")
            continue

    return ""

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me & ~filters.bot)
def handle_messages(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message [{sender}]: {user_text}")

    try:
        # Seen & Typing Simulation
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 1.8))

        # Fetch Real AI Answer
        reply_text = get_ai_response(user_text, sender)

        if reply_text:
            message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"Message Handler Error: {e}")

if __name__ == "__main__":
    logging.info("🚀 AI Bot is LIVE & Listening...")
    app.run()
