import time
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Active Gemini Model Setup
genai.configure(api_key=GEMINI_API_KEY)

active_model = None
MODELS_TO_CHECK = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-1.5-flash"
]

for m_name in MODELS_TO_CHECK:
    try:
        test_m = genai.GenerativeModel(m_name)
        # Test connection
        test_m.generate_content("hi")
        active_model = test_m
        logging.info(f"⚡ AI Connected to Model: {m_name}")
        break
    except Exception as e:
        logging.warning(f"Model {m_name} check failed: {e}")
        continue

if not active_model:
    active_model = genai.GenerativeModel("gemini-2.5-flash")

# 2. Pure Human-like Dynamic AI Generator
def generate_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, young Indian friend chatting on Telegram. Reply like an authentic real human in natural casual Hinglish (Hindi written in English alphabets).

Strict Guidelines:
1. Always reply in everyday conversational Hinglish (like talking to a close friend).
2. Understand chat short-forms and slangs (e.g. 'kkrh' = kya kar rahe ho, 'kidar h' = kahan ho, 'kaisa h' = kaisa hai, 'wrud', 'oye', 'yoo', 'hmm').
3. Keep it crisp and short (1-2 sentences maximum, never give essays).
4. NEVER say you are an AI, bot, or virtual assistant.
5. If the user explicitly asks for a group, channel or join link, share: {GROUP_LINK}

Friend ({sender_name}): "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"❌ AI Generation Error: {e}")
        # Retry with latest fallback model if current fails
        try:
            m_fallback = genai.GenerativeModel("gemini-flash-latest")
            res = m_fallback.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception as err2:
            logging.error(f"Fallback generation error: {err2}")
    
    return ""

# Popular Sticker Pack File IDs for instant sticker responses
COOL_STICKERS = [
    "CAACAgIAAxkBAAEK1eBlvK9-h3V1Lh6DkgABw1b4a3kAAj0AA8G2wQgYjGfXW3wFHgQ",  # Thumbs up / Cool
    "CAACAgIAAxkBAAEK1eJlvK-KzP6b2hM4g9_ySgABG3kAAl0AA8G2wQjK_HwXlB0BHgQ",  # Laugh
    "CAACAgIAAxkBAAEK1eRlvK-W6Z4zQ4YxKjZtL-UAAkcAA8G2wQirF03mGgW5HgQ",      # Wink / Hi
    "CAACAgIAAxkBAAEK1eZlvK-f7uO0n8cQ5f7L3OQAAiEAA8G2wQjX_d8uT4QHHgQ"       # Respect / Namaste
]

# 3. Telegram Client
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Text Message Handler (100% Dynamic AI)
@app.on_message(filters.text & ~filters.me & ~filters.bot)
def handle_incoming_text(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message [{sender}]: {user_text}")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.2, 2.0))

        # 100% AI generated reply
        reply_text = generate_ai_reply(user_text, sender)

        if reply_text:
            message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

    except Exception as err:
        logging.error(f"Text handling error: {err}")

# Sticker Message Handler (Replies with Sticker)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
def handle_incoming_sticker(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 1.8))
        message.reply_sticker(sticker=random.choice(COOL_STICKERS), quote=True)
        logging.info(f"✅ Replied Sticker to [{sender}]")

    except Exception as err:
        logging.error(f"Sticker handling error: {err}")

if __name__ == "__main__":
    logging.info("🚀 AI Bot is LIVE & Listening...")
    app.run()
