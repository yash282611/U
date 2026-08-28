import os, asyncio, random, logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROUP_LINK = os.environ.get("GROUP_LINK", "https://t.me/your_group_link")

if not all([API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY]):
    logging.error("❌ ज़रूरी क्रेडेंशियल्स मौजूद नहीं हैं!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_INSTRUCTION = f"आप Telegram ग्रुप/DM में असली इंसान की तरह बात कर रहे हैं। Hinglish में छोटे जवाब दें। जब कोई ग्रुप के बारे में पूछे तभी लिंक दें: {GROUP_LINK}"
model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
chat_sessions = {}
app = Client("group_human_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@app.on_message((filters.group | filters.private) & ~filters.me & ~filters.bot & filters.text)
async def auto_reply(client: Client, message: Message):
    chat_id = message.chat.id
    sender_name = message.from_user.first_name if message.from_user else "दोस्त"
    incoming_text = message.text
    if not incoming_text: return
    try:
        await client.read_chat_history(chat_id)
        await asyncio.sleep(random.uniform(1.2, 2.5))
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        if chat_id not in chat_sessions: chat_sessions[chat_id] = model.start_chat(history=[])
        response = await asyncio.to_thread(chat_sessions[chat_id].send_message, f"[{sender_name}]: {incoming_text}")
        reply_text = response.text.strip() if response and response.text else "हाँ भाई, बताओ!"
        await asyncio.sleep(min(max(len(reply_text) * 0.03, 1.2), 3.5))
        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    app.run()
