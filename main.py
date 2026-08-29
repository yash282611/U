import time
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Setup (Google ki nayi API ke hisaab se fixed)
genai.configure(api_key=GEMINI_API_KEY)

def connect_best_model():
    # Ab hum wahi model use karenge jo Google ne log me manga hai (3.6-flash)
    priority_models = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest"
    ]
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        logging.info(f"Available Account Models: {all_models}")

        for target in priority_models:
            for full_name in all_models:
                if target in full_name:
                    try:
                        m = genai.GenerativeModel(full_name)
                        logging.info(f"🎯 Connected 100% to Active AI Model: {full_name}")
                        return m
                    except Exception as err:
                        logging.warning(f"Skipping {full_name}: {err}")
                        continue
    except Exception as e:
        logging.error(f"Error finding model: {e}")

    # Default fallback to 3.6-flash as requested by Google API
    return genai.GenerativeModel("models/gemini-3.6-flash")

active_ai = connect_best_model()

# 2. 100% Dynamic AI Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, casual Indian friend chatting on Telegram. Reply like an authentic real human in natural everyday Hinglish (Hindi words written in English alphabet).

Chat Guidelines:
1. Always understand chat short-forms & slang:
   - "kkrh" -> kya kar rahe ho
   - "kidar h" -> kahan ho
   - "kaisa h" -> kaisa hai
   - "yo" / "hi" / "oye" -> casual greeting
2. Reply strictly based on what the user said in 1 short line.
3. NEVER repeat fixed canned lines.
4. NEVER say you are an AI or bot.
5. If the user asks for a group, channel, or link, share: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI response generation error: {e}")
    return ""

# Popular Sticker Pack IDs
STICKERS = [
    "CAACAgIAAxkBAAEK1eBlvK9-h3V1Lh6DkgABw1b4a3kAAj0AA8G2wQgYjGfXW3wFHgQ",
    "CAACAgIAAxkBAAEK1eJlvK-KzP6b2hM4g9_ySgABG3kAAl0AA8G2wQjK_HwXlB0BHgQ",
    "CAACAgIAAxkBAAEK1eRlvK-W6Z4zQ4YxKjZtL-UAAkcAA8G2wQirF03mGgW5HgQ",
    "CAACAgIAAxkBAAEK1eZlvK-f7uO0n8cQ5f7L3OQAAiEAA8G2wQjX_d8uT4QHHgQ"
]

# 3. Pyrogram Client
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Text Handler
@app.on_message(filters.text & ~filters.me & ~filters.bot)
def on_text_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Text [{sender}]: {user_text}")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.2, 2.0))

        reply = get_ai_reply(user_text, sender)
        if reply:
            message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Handler
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
def on_sticker_message(client: Client, message: Message):
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
        message.reply_sticker(sticker=random.choice(STICKERS), quote=True)
        logging.info(f"✅ Replied Sticker to [{sender}]")

    except Exception as e:
        logging.error(f"Sticker error: {e}")

if __name__ == "__main__":
    logging.info("🚀 AI Human Bot is Starting with New Gemini API...")
    app.run()
