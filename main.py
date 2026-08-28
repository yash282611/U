import asyncio
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
    f"Hinglish me casual aur natural reply dein (1-2 sentences me). "
    f"Jab koi group/channel ke baare me puche tabhi yeh link dein: {GROUP_LINK}"
)

# Best available model finder
def get_best_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for name in models:
            if "flash" in name:
                logging.info(f"✅ Selected Gemini Model: {name}")
                return genai.GenerativeModel(name, system_instruction=SYSTEM_PROMPT)
        if models:
            logging.info(f"✅ Selected Gemini Model: {models[0]}")
            return genai.GenerativeModel(models[0], system_instruction=SYSTEM_PROMPT)
    except Exception as e:
        logging.warning(f"Model auto-detect error: {e}")
    return genai.GenerativeModel("gemini-1.5-flash-latest", system_instruction=SYSTEM_PROMPT)

model = get_best_model()

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me)
def auto_reply(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

    try:
        client.send_chat_action(chat_id, ChatAction.TYPING)

        prompt = f"User ({sender}): {user_text}\nReply:"
        response = model.generate_content(prompt)
        reply_text = response.text.strip() if (response and response.text) else "Haan bhai, bolo!"

        message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Sent Reply: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error in reply: {e}")

if __name__ == "__main__":
    logging.info("🚀 Bot start ho raha hai...")
    app.run()
