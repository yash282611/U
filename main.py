import time
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Setup (Ultra Fast Flash Model)
genai.configure(api_key=GEMINI_API_KEY)

# Select fastest flash model from your account
FLASH_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash",
    "models/gemini-2.5-flash",
    "models/gemini-flash-latest"
]

ai_model = None
for m_name in FLASH_MODELS:
    try:
        ai_model = genai.GenerativeModel(m_name)
        logging.info(f"⚡ Active High-Speed Model: {m_name}")
        break
    except Exception:
        continue

if not ai_model:
    ai_model = genai.GenerativeModel("gemini-1.5-flash")

def get_real_human_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool Indian friend chatting on Telegram. Reply like a real human in natural casual Hinglish (Hindi words in English script).

Rules:
1. Speak 100% everyday casual Hinglish (use words like: haan, arre, mast, badhiya, bhai, yaar, tu bata, kuch nahi).
2. Understand slang and short words (kkrh = kya kar raha hai, kidar h = kahan hai, kaisa h = kaisa hai, yoo, oye, kya huau = kya hua).
3. Directly answer the question in 1 short line like a real person typing on phone.
4. DO NOT repeat fixed sentences.
5. NEVER mention you are an AI or bot.
6. Only share this link if someone asks for a group or link: {GROUP_LINK}

Friend ({sender_name}): "{user_text}"
Your fast Hinglish reply:"""

    try:
        response = ai_model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI generation failed: {e}")
    
    return "Haan bol bhai, sun raha hu!"

# 2. Telegram Pyrogram Client
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me & ~filters.bot)
def on_user_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message [{sender}]: {user_text}")

    try:
        # Mark as read & Typing status
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        # Realistic short delay
        time.sleep(random.uniform(1.0, 1.8))

        # Dynamic AI reply
        reply_text = get_real_human_reply(user_text, sender)

        # Send Reply
        message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

    except Exception as err:
        logging.error(f"Message send error: {err}")

if __name__ == "__main__":
    logging.info("🚀 AI Userbot is Starting...")
    app.run()
