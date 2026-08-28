import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if not all([API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY]):
    logging.error("❌ क्रेडेंशियल्स मौजूद नहीं हैं! Railway Variables चेक करें।")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_INSTRUCTION = f"आप Telegram ग्रुप/DM में असली इंसान की तरह बात कर रहे हैं। Hinglish में छोटे जवाब दें। जब कोई ग्रुप के बारे में पूछे तभी लिंक दें: {GROUP_LINK}"
model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

chat_sessions = {}
app = Client("group_human_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@app.on_message((filters.group | filters.private) & ~filters.me & ~filters.bot & filters.text)
async def auto_reply(client: Client, message: Message):
    try:
        chat_id = message.chat.id
        sender_name = message.from_user.first_name if message.from_user else "दोस्त"
        incoming_text = message.text

        if not incoming_text:
            return

        await client.read_chat_history(chat_id)
        await asyncio.sleep(random.uniform(1.2, 2.5))
        await client.send_chat_action(chat_id, ChatAction.TYPING)

        if chat_id not in chat_sessions:
            chat_sessions[chat_id] = model.start_chat(history=[])

        session = chat_sessions[chat_id]
        prompt = f"[{sender_name}]: {incoming_text}"
        response = await asyncio.to_thread(session.send_message, prompt)

        reply_text = response.text.strip() if response and response.text else "हाँ भाई, बताओ!"
        typing_delay = min(max(len(reply_text) * 0.03, 1.2), 3.5)
        await asyncio.sleep(typing_delay)

        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"Replied in chat {chat_id} to {sender_name}")

    except Exception as e:
        logging.error(f"Message error ignored: {e}")

async def main():
    async with app:
        logging.info("⏳ ग्रुप्स और चैट्स लोड हो रहे हैं...")
        try:
            async for _ in app.get_dialogs(limit=100):
                pass
        except Exception as e:
            logging.warning(f"Dialog cache warning: {e}")
        logging.info("🚀 AI बॉट सफलतापूर्वक लाइव हो चुका है!")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
