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
    f"Aap ek real human ki tarah baat kar rahe hain. "
    f"Hinglish me casual aur natural jawab dein. "
    f"Jab koi link ya group maange tabhi yeh dein: {GROUP_LINK}"
)
model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me)
def auto_reply(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "User"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

    try:
        # Typing status
        client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # Gemini AI generation
        prompt = f"User ({sender}): {user_text}\nReply:"
        response = model.generate_content(prompt)
        reply_text = response.text.strip() if response and response.text else "Haan bhai, bolo!"

        # Reply to user
        message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Sent Reply: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error in reply: {e}")

if __name__ == "__main__":
    logging.info("🚀 Bot start ho raha hai...")
    app.run()
