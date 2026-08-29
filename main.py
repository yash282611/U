import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_KEY = str(GEMINI_API_KEY).strip()
MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]

# Pure REST API Call (Zero SDK/Auth Crashes)
def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, friendly Indian chatting casually on Telegram with a friend.\n"
        f"Guidelines:\n"
        f"1. Reply strictly in natural, casual everyday Hinglish (Hindi written in English alphabet).\n"
        f"2. Understand chat slang & short words (e.g. 'gf h teri', 'kidar gya', 'kkrh', 'kaisa h', 'hi', 'oye', 'thik').\n"
        f"3. Keep it strictly 1-2 short sentences like a real mobile user typing.\n"
        f"4. Never say you are an AI or bot.\n"
        f"5. Only share this link if user asks for group/channel/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) sent: \"{user_text}\"\n"
        f"Your natural Hinglish reply:"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 80}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except urllib.error.HTTPError as e:
            logging.warning(f"Model {model} HTTP {e.code}")
            continue
        except Exception as e:
            logging.warning(f"Model {model} error: {e}")
            continue

    return "Haan bhai, bol sun raha hu!"

# Telegram Client Setup
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

CHAT_FILTER = (filters.private | filters.group) & filters.incoming & ~filters.me & ~filters.bot

# Text Messages Handler
@app.on_message(filters.text & CHAT_FILTER)
async def text_handler(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Text [{sender}]: {user_text}")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.8))
        reply = await asyncio.to_thread(fetch_gemini_reply, user_text, sender)

        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Replied to [{sender}]: {reply}")
    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Messages Handler
@app.on_message(filters.sticker & CHAT_FILTER)
async def sticker_handler(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.5))
        if message.sticker and message.sticker.file_id:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
    except Exception as e:
        logging.error(f"Sticker error: {e}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE, REST API Connected & Ready 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
