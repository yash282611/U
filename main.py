import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import pyrogram.client
import pyrogram.raw.functions.updates as raw_update_funcs
import pyrogram.raw.types.updates as raw_updates
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Background Channel Crash Suppressor (Only for background channels)
orig_invoke = pyrogram.client.Client.invoke

async def clean_invoke(self, query, *args, **kwargs):
    try:
        return await orig_invoke(self, query, *args, **kwargs)
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        if isinstance(query, raw_update_funcs.GetChannelDifference):
            return raw_updates.ChannelDifferenceEmpty(flags=0, final=True, pts=getattr(query, "pts", 0), timeout=0)
        raise

pyrogram.client.Client.invoke = clean_invoke

# 2. Gemini AI Fast REST Caller
API_KEY = str(GEMINI_API_KEY).strip()
CONFIRMED_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash"
]

def fetch_gemini_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are an authentic, cool Indian friend chatting casually on Telegram.\n"
        f"Guidelines:\n"
        f"1. Reply strictly in natural, casual everyday Hinglish (Hindi written in English alphabets).\n"
        f"2. Understand slang and chat short-forms (e.g. 'gf h teri', 'kidar hoo', 'kkrh', 'kaisa h', 'hi', 'heyy', 'yooo', 'nenjhhisbs').\n"
        f"3. Keep replies short (1 crisp sentence like a real mobile user typing).\n"
        f"4. Never say you are an AI, bot, or assistant.\n"
        f"5. If someone asks for a group or link, share: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) sent: \"{user_text}\"\n"
        f"Your quick Hinglish reply:"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 70}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in CONFIRMED_MODELS:
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
        return "Kuch nahi bhai, bas phone chala raha hu. Tu bata?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya plan?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi mast hain!"
    elif any(k in low for k in ["hi", "hii", "hiii", "yoo", "heyy", "oye", "gi"]):
        return "Haan bhai, bol kya haal chaal!"

    return "Haan bhai bol, sun raha hu!"

# 3. Client & Handlers
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_MEMORY = []

# Main Message Dispatcher (DMs + Groups)
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def message_dispatcher(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id

        # 1. Agar STICKER aaya ho -> Sticker se turant reply
        if message.sticker:
            if message.sticker.file_id:
                STICKER_MEMORY.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}]")

            try:
                await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.5))
            chosen = random.choice(STICKER_MEMORY) if STICKER_MEMORY else message.sticker.file_id
            await message.reply_sticker(sticker=chosen, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
            return

        # 2. Agar TEXT message aaya ho -> AI Hinglish Reply
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
    logging.info("🚀 AI Userbot is LIVE & 100% Ready 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
