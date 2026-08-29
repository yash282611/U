import time
import random
import logging
import os
import pyrogram.utils
import pyrogram.client
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerEmpty
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Credentials (Seedha Railway Variables se uthayega)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROUP_LINK = os.environ.get("GROUP_LINK", "https://t.me/your_group")

# 2. ROOT LEVEL FIX (Group Peer Errors ko hatane ke liye)
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MAX_CHAT_ID = -1
pyrogram.utils.MIN_USER_ID = 0
pyrogram.utils.MAX_USER_ID = 999999999999999

def patched_get_peer_type(peer_id: int) -> str:
    s = str(peer_id)
    if s.startswith("-100"): return "channel"
    elif peer_id < 0: return "chat"
    return "user"

def patched_get_channel_id(peer_id: int) -> int:
    s = str(peer_id)
    if s.startswith("-100"): return peer_id
    return int(f"-100{peer_id}")

pyrogram.utils.get_peer_type = patched_get_peer_type
pyrogram.utils.get_channel_id = patched_get_channel_id

_orig_resolve_peer = pyrogram.client.Client.resolve_peer
async def safe_resolve_peer(self, peer_id):
    try:
        return await _orig_resolve_peer(self, peer_id)
    except Exception:
        if isinstance(peer_id, int):
            s = str(peer_id)
            if s.startswith("-100"): return InputPeerChannel(channel_id=int(s[4:]), access_hash=0)
            elif peer_id < 0: return InputPeerChat(chat_id=-peer_id)
            else: return InputPeerUser(user_id=peer_id, access_hash=0)
        return InputPeerEmpty()

pyrogram.client.Client.resolve_peer = safe_resolve_peer

_orig_handle_updates = pyrogram.client.Client.handle_updates
async def safe_handle_updates(self, updates):
    try:
        await _orig_handle_updates(self, updates)
    except Exception:
        pass
pyrogram.client.Client.handle_updates = safe_handle_updates

# 3. Groq Cloud API Setup
try:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    logging.info("🎯 Connected 100% to Groq Cloud API")
except Exception as e:
    logging.error(f"Groq connection error: {e}")

# 4. Dynamic Groq Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    system_prompt = f"""You are a cool, casual Indian friend chatting on Telegram. Reply like an authentic real human in natural everyday Hinglish (Hindi words written in English alphabet).

Chat Guidelines:
1. Always understand chat short-forms & slang:
   - "kkrh" -> kya kar rahe ho
   - "kidar h" -> kahan ho
   - "kaisa h" -> kaisa hai
   - "yo" / "hi" / "oye" -> casual greeting
2. Reply strictly based on what the user said in 1 short line.
3. NEVER repeat fixed canned lines.
4. NEVER say you are an AI or bot.
5. If the user asks for a group, channel, or link, share: {GROUP_LINK}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Friend ({sender_name}) says: \"{user_text}\"\nYour Hinglish reply:"}
            ],
            temperature=0.85,
            max_tokens=60
        )
        if response.choices:
            return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Groq response generation error: {e}")
    return ""

STICKERS = [
    "CAACAgIAAxkBAAEK1eBlvK9-h3V1Lh6DkgABw1b4a3kAAj0AA8G2wQgYjGfXW3wFHgQ",
    "CAACAgIAAxkBAAEK1eJlvK-KzP6b2hM4g9_ySgABG3kAAl0AA8G2wQjK_HwXlB0BHgQ",
    "CAACAgIAAxkBAAEK1eRlvK-W6Z4zQ4YxKjZtL-UAAkcAA8G2wQirF03mGgW5HgQ",
    "CAACAgIAAxkBAAEK1eZlvK-f7uO0n8cQ5f7L3OQAAiEAA8G2wQjX_d8uT4QHHgQ"
]

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.bot)
def on_text_message(client: Client, message: Message):
    try:
        if message.text and message.text.startswith("🤖"):
            return

        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Naya Text [{sender}]: {user_text}")

        try:
            if not message.outgoing:
                client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 1.5))

        reply = get_ai_reply(user_text, sender)
        if reply:
            message.reply_text(text=f"🤖 {reply}", quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Groq Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

if __name__ == "__main__":
    logging.info("🚀 AI Human Bot is Starting with Groq llama3-70b-8192...")
    app.run()
