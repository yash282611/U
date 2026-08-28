import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    f"Aap Telegram par ek real human ki tarah baat kar rahe hain. "
    f"Hinglish me friendly aur short jawab dein (1-2 lines). "
    f"Jab koi group/link maange tabhi yeh dein: {GROUP_LINK}"
)

# Robust Multi-Model Finder
def get_working_model():
    model_candidates = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
    try:
        available = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for candidate in model_candidates:
            if candidate in available:
                logging.info(f"✅ Gemini Model Selected: {candidate}")
                return genai.GenerativeModel(candidate, system_instruction=SYSTEM_PROMPT)
    except Exception as e:
        logging.warning(f"Model listing failed: {e}")
    return genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

model = get_working_model()

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me)
async def auto_reply(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

    try:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        prompt = f"User ({sender}) says: {user_text}\nReply:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        reply_text = response.text.strip() if (response and response.text) else "Haan bhai, bolo!"

        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Reply bheja: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error in reply: {e}")
        try:
            await message.reply_text("Haan bhai, bolo kya haal chaal?", quote=True)
        except Exception:
            pass

async def main():
    await app.start()
    logging.info("⏳ Dialogs cache load ho raha hai...")
    try:
        async for _ in app.get_dialogs(limit=50):
            pass
    except Exception:
        pass
    logging.info("🚀 AI Bot puri tarah ready hai aur live listen kar raha hai!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
