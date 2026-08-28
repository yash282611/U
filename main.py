import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = (
    f"Aap Telegram par ek real human ki tarah baat kar rahe hain. "
    f"Hinglish me friendly, casual aur short jawab dein (1-2 lines). "
    f"Jab koi group ya channel ka link maange tabhi yeh dein: {GROUP_LINK}"
)

# Multi-Model Fallback
MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro", "gemini-1.5-pro"]

def ask_gemini(user_text, sender_name):
    prompt = f"User ({sender_name}): {user_text}\nReply in Hinglish:"
    for model_name in MODELS_TO_TRY:
        try:
            m = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
            res = m.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            continue
    return "Haan bhai, bolo kya haal chaal?"

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me)
async def auto_reply(client: Client, message: Message):
    try:
        chat_id = message.chat.id
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text

        logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

        # 1. Seen / Read status
        await client.read_chat_history(chat_id)

        # 2. Human typing delay
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(1.2, 2.2))

        # 3. Get AI Response
        reply_text = await asyncio.to_thread(ask_gemini, user_text, sender)

        # 4. Send Reply
        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Sent Reply to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error in message handling: {e}")

if __name__ == "__main__":
    logging.info("🚀 AI Human Bot is Starting...")
    app.run()
