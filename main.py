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

def generate_human_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a chill Indian guy chatting on Telegram. Reply like a real, cool human friend in everyday casual Hinglish (Hindi written in English alphabet).

Chat Rules:
1. Speak 100% natural conversational Hinglish (use casual words like bhai, arre, mast, badhiya, yaar, tu bata).
2. Understand chat slang & short forms (e.g. 'kkrh' = kya kar raha hai, 'wrud' = what are you doing, 'kaisa h' = kaisa hai, 'gn' = good night).
3. Keep replies very short and sweet (1 to 2 lines max).
4. NEVER say "I am an AI", "How can I assist you?", or speak like a robot/bot.
5. If the user asks for a group, channel, link, or where to join, share this: {GROUP_LINK}

User message from {sender_name}: "{user_text}"
Your natural reply:"""

    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
    
    for model_name in models_to_try:
        try:
            m = genai.GenerativeModel(model_name)
            res = m.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            logging.error(f"Error on model {model_name}: {e}")
            continue

    # Human-like dynamic fallbacks
    fallbacks = [
        "Kuch nahi bhai, bas phone chala raha tha. Tu bata kya scene?",
        "Badhiya bhai, tu suna kya chal raha hai?",
        "Haan bolo bhai, sab theek thaak?",
        "Bas aese hi baitha tha yaar, tu bata kaisa hai?"
    ]
    return random.choice(fallbacks)

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & filters.incoming & ~filters.me & ~filters.bot)
async def auto_reply(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Incoming Message [{sender}]: {user_text}")

        # Seen & Typing Simulation
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        # Natural typing delay
        await asyncio.sleep(random.uniform(1.2, 2.5))

        # AI Reply
        reply_text = await asyncio.to_thread(generate_human_reply, user_text, sender)

        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

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
    logging.info("🚀 AI Human Bot is LIVE and Ready!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
