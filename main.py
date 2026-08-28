import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Gemini Auto-Detection
genai.configure(api_key=GEMINI_API_KEY)

active_model = None
try:
    available_models = [
        m.name for m in genai.list_models() 
        if 'generateContent' in m.supported_generation_methods
    ]
    logging.info(f"Available Gemini Models: {available_models}")
    
    # Select best working model
    for target in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]:
        matching = [m for m in available_models if target in m]
        if matching:
            active_model = genai.GenerativeModel(matching[0])
            logging.info(f"✅ Loaded Model: {matching[0]}")
            break
            
    if not active_model and available_models:
        active_model = genai.GenerativeModel(available_models[0])
except Exception as e:
    logging.error(f"Model initialization error: {e}")
    active_model = genai.GenerativeModel("gemini-1.5-flash")

def ask_ai(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a young Indian friend chatting casually on Telegram in Hinglish (Hindi written in English alphabet).

Rules:
1. Always reply in natural, everyday casual Hinglish.
2. Understand slang and short-forms (e.g., kkrh = kya kar raha hai, kaisa h = kaisa hai, oye, wrud, haan, hmm).
3. Keep it brief (1 to 2 lines max).
4. Never introduce yourself as an AI or bot. Speak like a real person.
5. If the user asks for group/channel/link, share: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as err:
        logging.error(f"Gemini API generation error: {err}")
    
    return ""

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def handle_incoming(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Naya Message [{sender}]: {user_text}")

        # Seen status & typing simulation
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.2, 2.0))

        # Generate dynamic reply
        ai_reply = await asyncio.to_thread(ask_ai, user_text, sender)

        if not ai_reply:
            # Fallback if API response is empty
            ai_reply = "Bolo bhai, sun raha hu."

        await message.reply_text(text=ai_reply, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ AI Replied to [{sender}]: {ai_reply}")

    except Exception as e:
        logging.error(f"Handler error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs cache sync ho raha hai...")
    try:
        async for _ in app.get_dialogs(limit=50):
            pass
    except Exception:
        pass
    logging.info("🚀 AI Human Bot is LIVE & Ready!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
