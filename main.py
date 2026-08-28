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
    f"You are a friendly human chatting on Telegram in Hinglish. "
    f"Keep answers short, natural and casual (1-2 lines). "
    f"Only share this group link if someone asks for a group or link: {GROUP_LINK}"
)

model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Filters: Only text, incoming, not me, not bots
@app.on_message(filters.text & filters.incoming & ~filters.me & ~filters.bot)
async def auto_reply(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

        # 1. Seen / Typing simulation
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.2, 2.5))

        # 2. Gemini Response
        try:
            prompt = f"User ({sender}): {user_text}"
            res = await asyncio.to_thread(model.generate_content, prompt)
            reply_text = res.text.strip() if (res and res.text) else "Haan bhai, bolo!"
        except Exception as e:
            logging.warning(f"AI response fallback: {e}")
            reply_text = "Haan bhai, bolo kya haal chaal?"

        # 3. Send reply
        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Sent Reply to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"Message handling error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialog cache sync ho raha hai...")
    try:
        async for _ in app.get_dialogs(limit=100):
            pass
    except Exception:
        pass
    logging.info("🚀 AI Human Bot is LIVE and Ready!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
