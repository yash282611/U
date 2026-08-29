import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import pyrogram.client
import pyrogram.utils
from pyrogram.raw.types import InputPeerEmpty

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. CRITICAL ENGINE PATCH: Safe Resolve Peer (Zero DM Freeze)
orig_resolve_peer = pyrogram.client.Client.resolve_peer

async def safe_resolve_peer(self, peer_id):
    try:
        return await orig_resolve_peer(self, peer_id)
    except Exception:
        # Invalid background channels will safely skip without blocking DMs
        return InputPeerEmpty()

pyrogram.client.Client.resolve_peer = safe_resolve_peer

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
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

API_KEY = str(GEMINI_API_KEY).strip()
ACTIVE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

# Fast Dynamic AI Generator
def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, friendly Indian friend chatting casually on Telegram in natural Hinglish.\n"
        f"Guidelines:\n"
        f"1. Reply in everyday casual Hinglish (Hindi written in English alphabet).\n"
        f"2. Understand chat slang & short words (e.g. 'gf h teri', 'kidar hoo', 'kkrh', 'kaisa h', 'hi', 'heyy', 'yooo', 'oye', 'gi').\n"
        f"3. Keep it to 1-2 short sentences like a real human typing.\n"
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

    # Instant Contextual Fallbacks
    low = user_text.lower().strip()
    if any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
        return "Kuch nahi bhai, bas phone chala raha hu. Tu bata?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya scene?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi bindass hain!"
    elif any(k in low for k in ["hi", "hii", "hiii", "yoo", "heyy", "oye", "gi"]):
        return "Haan bhai, bol kya haal chaal!"

    return "Haan bhai bol, sun raha hu!"

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

ACCOUNT_STICKERS = []

# Direct Clean Message Handlers
@app.on_message(~filters.me & ~filters.bot)
async def incoming_dispatcher(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id

        # 1. Agar STICKER aaya ho
        if message.sticker:
            if message.sticker.file_id:
                ACCOUNT_STICKERS.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}]")

            try:
                await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.6))

            if ACCOUNT_STICKERS:
                chosen = random.choice(ACCOUNT_STICKERS)
                await message.reply_sticker(sticker=chosen, quote=True)
            else:
                await message.reply_sticker(sticker=message.sticker.file_id, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
            return

        # 2. Agar TEXT message aaya ho
        if message.text:
            user_text = message.text
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
        logging.error(f"Handler error: {e}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE & 100% Active 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
