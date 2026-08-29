import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import pyrogram.client
import pyrogram.utils
from pyrogram.errors import PeerIdInvalid, ChannelInvalid, ChannelPrivate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. CRITICAL ENGINE PATCH: Block Background Infinite Update Loop
orig_handle_updates = pyrogram.client.Client.handle_updates

async def bulletproof_handle_updates(self, updates):
    try:
        await orig_handle_updates(self, updates)
    except (PeerIdInvalid, ChannelInvalid, ChannelPrivate, ValueError, KeyError):
        # Corrupt channel updates ko drop karke event loop ko 100% free rakhega
        return
    except Exception:
        return

pyrogram.client.Client.handle_updates = bulletproof_handle_updates

# 64-bit Telegram IDs Patch
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
from pyrogram.raw.functions.messages import GetAllStickers
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

API_KEY = str(GEMINI_API_KEY).strip()
ACTIVE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

# Fast AI Generator
def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, cool Indian guy chatting casually on Telegram with a friend.\n"
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
            with urllib.request.urlopen(req, timeout=4) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            continue

    # Instant Fallback Response
    low = user_text.lower()
    if any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
        return "Kuch nahi bhai, bas baitha hu. Tu bata?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya scene?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi mast hain!"
    elif any(k in low for k in ["hi", "hii", "yoo", "heyy", "oye"]):
        return "Haan bhai, bol kya haal chaal?"

    return "Haan bhai bol, sun raha hu!"

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

ACCOUNT_STICKERS = []

async def sync_stickers():
    global ACCOUNT_STICKERS
    ACCOUNT_STICKERS.clear()
    try:
        res = await app.invoke(GetAllStickers(hash=0))
        if hasattr(res, "sets"):
            for s in res.sets:
                short_name = getattr(s.set, "short_name", None) if hasattr(s, "set") else getattr(s, "short_name", None)
                if short_name:
                    try:
                        st_set = await app.get_sticker_set(short_name)
                        for st in st_set.stickers:
                            ACCOUNT_STICKERS.append(st.file_id)
                    except Exception:
                        continue
    except Exception:
        pass

    if not ACCOUNT_STICKERS:
        for backup in ["AnimatedDog", "HotCherry", "Animals"]:
            try:
                st_set = await app.get_sticker_set(backup)
                for st in st_set.stickers:
                    ACCOUNT_STICKERS.append(st.file_id)
            except Exception:
                continue

    logging.info(f"🎨 Total {len(ACCOUNT_STICKERS)} Account Stickers Ready!")

CHAT_FILTER = (filters.private | filters.group) & filters.incoming & ~filters.me & ~filters.bot

# Text Message Handler
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

        await asyncio.sleep(random.uniform(1.0, 1.6))
        reply = await asyncio.to_thread(fetch_gemini_reply, user_text, sender)

        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Replied to [{sender}]: {reply}")
    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Message Handler (Account Stickers Reply)
@app.on_message(filters.sticker & CHAT_FILTER)
async def sticker_handler(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    if message.sticker and message.sticker.file_id:
        ACCOUNT_STICKERS.append(message.sticker.file_id)

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.5))

        if ACCOUNT_STICKERS:
            chosen = random.choice(ACCOUNT_STICKERS)
            await message.reply_sticker(sticker=chosen, quote=True)
            logging.info(f"✅ Sent Account Sticker to [{sender}]")
        else:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)
    except Exception as e:
        logging.error(f"Sticker error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs & Stickers Sync...")
    try:
        async for _ in app.get_dialogs(limit=30):
            pass
    except Exception:
        pass

    await sync_stickers()
    logging.info("🚀 AI Bot is LIVE, Lag-Free & Listening 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
