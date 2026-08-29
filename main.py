import time
import random
import logging
import pyrogram.utils
import pyrogram.client
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerEmpty
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from openai import OpenAI
from config import API_ID, API_HASH, SESSION_STRING, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Root Level Fix for Pyrogram Group Peers
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

# ==========================================
# 🔑 APNI GROQ API KEY YAHAN DIRECT DAAL DO
# ==========================================
DIRECT_GROQ_KEY = "gsk_yah_apni_asli_groq_key_paste_kar_dena"

try:
    groq_client = OpenAI(
        api_key=DIRECT_GROQ_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    logging.info("🎯 Connected 100% to Groq Cloud API")
except Exception as e:
    logging.error(f"Grok connection error: {e}")

# 100% Human-Like Ultra-Natural Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    system_prompt = f"""You are a real 19-year-old college guy chatting casually with your close friend on Telegram. 
Talk like an absolute human, not a robot or AI assistant.

Strict Rules for Real Human Vibe:
1. Use natural Indian slang and everyday Hinglish (Hindi words in English letters, like "bhai", "kya re", "sahi hai", "arre", "dekh", "achha").
2. Keep replies short, casual, and conversational (1 short line, max 5-10 words usually).
3. Vary your tone! Sometimes reply with just a laughing emoji, sometimes a short question back, sometimes casual agreement.
4. NEVER use formal words, proper punctuation like a book, or robotic template replies.
5. NEVER say you are an AI, bot, or language model. Act completely human.
6. If the user asks for a group, channel, or link, share: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your natural human Hinglish reply:"""

    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=1.0,  # Thoda high temperature taaki har baar alag aur naya jhabardast reply de
            max_tokens=40
        )
        if response.choices:
            return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Groq response generation error: {e}")
    
    # Fallback agar kabhi API slow ho toh alag-alag casual lines me se ek uthayega
    fallbacks = ["bol bhai", "kya bol rha h", "hmm sun rha hu", "haan bata", "kya scene h"]
    return random.choice(fallbacks)

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

        # Insaan ki tarah thoda sochne ka delay (random 1.5 se 3 second tak)
        time.sleep(random.uniform(1.5, 3.0))

        reply = get_ai_reply(user_text, sender)
        if reply:
            # Bina kisi roboti emoji ke seedha normal text bhejo taaki asli lage
            message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Human-like Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

if __name__ == "__main__":
    logging.info("🚀 100% Human-Like AI Userbot is Starting...")
    app.run()
