import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import pyrogram.client
import pyrogram.utils

# 1. CRITICAL PATCH: Prevent ChannelInvalid & PeerId Crashes
orig_handle_updates = pyrogram.client.Client.handle_updates

async def safe_handle_updates(self, updates):
    try:
        await orig_handle_updates(self, updates)
    except Exception as e:
        # Silently ignore bad channel difference errors
        logging.warning(f"Handled background update glitch: {e}")

pyrogram.client.Client.handle_updates = safe_handle_updates

# Patch for 64-bit Telegram IDs
def patched_get_peer_type(peer_id: int) -> str:
    if peer_id < 0:
        if str(peer_id).startswith("-100"):
            return "channel"
        return "chat"
    return "user"

def patched_get_channel_id(peer_id: int) -> int:
    s = str(peer_id)
    if s.startswith("-100"):
        return peer_id
    return int(f"-100{peer_id}")

pyrogram.utils.get_peer_type = patched_get_peer_type
pyrogram.utils.get_channel_id = patched_get_channel_id

# 2. Main Bot Setup
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_KEY = str(GEMINI_API_KEY).strip()
ACTIVE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, friendly Indian chatting casually on Telegram with a friend.\n"
        f"Guidelines:\n"
        f"1. Reply strictly in natural, casual everyday Hinglish (Hindi written in English alphabet).\n"
        f"2. Understand chat slang & short words (e.g. 'gf h teri', 'kidar hoo', 'kkrh', 'kaisa h', 'hi', 'heyy', 'yooo', 'oye').\n"
        f"3. Keep it strictly 1 short sentence like a real mobile user typing.\n"
        f"4. Never say you are an AI or bot.\n"
        f"5. Only share this link if user asks for group/channel/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) sent: \"{user_text}\"\n"
        f"Your natural Hinglish reply:"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 70}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in ACTIVE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            continue

    return "Haan bhai, bol kya haal chaal!"

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

# Sticker Messages Handler
@app.on_message(filters.sticker & CHAT_FILTER)
async def sticker_handler(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id

        logging.info(f"🎨 Sticker received from [{sender}]")

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
    logging.info("🚀 AI Userbot is LIVE & Crash-Proof 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
