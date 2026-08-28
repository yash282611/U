import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if not all([API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY]):
    logging.error("❌ Railway Variables missing hain!")
    exit(1)

# Gemini AI Setup
genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = (
    f"Aap Telegram par ek real human ki tarah baat kar rahe hain. "
    f"Hinglish me chote, casual aur natural reply dein. "
    f"Jab koi group ya channel ke baare me puche tabhi yeh link dein: {GROUP_LINK}"
)
model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & filters.incoming)
async def auto_reply(client: Client, message: Message):
    sender_name = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text

    # Log incoming message
    logging.info(f"📩 Naya message aaya from [{sender_name}]: {user_text}")

    try:
        # Human-like typing delay
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Generate AI Reply
        prompt = f"User ({sender_name}) says: {user_text}\nReply:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        reply_text = response.text.strip() if response and response.text else "Haan bhai, bolo!"

        # Send Reply
        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Reply bhej diya: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error aaya message reply me: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs cache load ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=50):
            pass
    except Exception:
        pass
    logging.info("🚀 AI Bot puri tarah active hai aur message sun raha hai!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
