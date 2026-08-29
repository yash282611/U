import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import pyrogram.client
import pyrogram.utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. PERMANENT ENGINE FIX: 64-bit Telegram IDs & Update Crash Bypass
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MAX_CHAT_ID = -1
pyrogram.utils.MIN_USER_ID = 0
pyrogram.utils.MAX_USER_ID = 99999999999999

orig_handle_updates = pyrogram.client.Client.handle_updates

async def safe_handle_updates(self, updates):
    try:
        await orig_handle_updates(self, updates)
    except Exception:
        # Invalid background channel updates ko drop karke DMs ko 100% free rakhega
        pass

pyrogram.client.Client.handle_updates = safe_handle_updates

# 2. Main Bot Setup
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

API_KEY = str(GEMINI_API_KEY).strip()
ACTIVE_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash"
]

def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, cool Indian friend chatting casually on Telegram.\n"
        f"Guidelines:\n"
        f"1. Reply strictly in natural, casual everyday Hinglish (Hindi written in English alphabets).\n"
        f"2. Understand slang and chat short-words (e.g. 'gf h teri', 'kidar hoo', 'kkrh', 'kaisa h', 'hi', 'heyy', 'yooo', 'nenjhhisbs', 'gi').\n"
        f"3. Keep replies very short (1 crisp sentence like a real mobile user typing).\n"
        f"4. Never say you are an AI, bot, or assistant.\n"
        f"5. If someone asks for a group or link, share: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) sent: \"{user_text}\"\n"
        f"Your quick Hinglish reply:"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 70}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in ACTIVE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            continue

    # Instant Fallback Response
    low = user_text.lower().strip()
    if any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
        return "Kuch nahi bhai, bas phone chala raha tha. Tu bata?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya plan hai?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi bindass hain!"
    elif any(k in low for k in ["hi", "hii", "hiii", "yoo", "heyy", "oye", "gi", "h"]):
        return "Haan bhai, bol kya haal chaal!"

    return "Haan bhai bol, sun raha hu!"

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKERS_MEMORY = []

# Text Messages Handler
@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def text_handler(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Naya Text [{sender}]: {user_text}")

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

# Sticker Messages Handler (Sticker par Sticker Reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def sticker_handler(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id

        if message.sticker and message.sticker.file_id:
            STICKERS_MEMORY.append(message.sticker.file_id)

        logging.info(f"🎨 Sticker received from [{sender}]")

        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.5))
        sticker_to_send = random.choice(STICKERS_MEMORY) if STICKERS_MEMORY else message.sticker.file_id
        await message.reply_sticker(sticker=sticker_to_send, quote=True)
        logging.info(f"✅ Replied Sticker to [{sender}]")

    except Exception as e:
        logging.error(f"Sticker error: {e}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE & 100% Ready 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
