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
from collections import defaultdict

# Config file se sab import kar rahe hain
from config import API_ID, API_HASH, SESSION_STRING, GROQ_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==========================================
# Root Level Fix for Pyrogram Group Peers
# ==========================================
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
# Groq API Setup
# ==========================================
try:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    logging.info("🎯 Connected 100% to Groq Cloud API")
except Exception as e:
    logging.error(f"Groq connection error: {e}")

# ==========================================
# Chat History Memory 
# ==========================================
chat_histories = defaultdict(list)

def get_ai_reply(chat_id: int, user_text: str, sender_name: str) -> str:
    # Yahan AI ko bilkul insaan banne ki strict warning di gayi hai
    system_prompt = f"""You are a real 19-year-old Indian guy chatting with your close friend on Telegram. 
You MUST act exactly like a normal human being. NEVER act like an AI, bot, or assistant.

Strict Rules for chatting:
1. Talk in casual everyday Hinglish (e.g., 'haan bhai', 'kya scene hai', 'kuch nahi yaar', 'tu bata').
2. Read the context and reply DIRECTLY to what the user just said. 
   - Example: If user says "khana khaya?", reply like "haan bhai kha liya, tu bata" or "nahi yaar abhi khaunga".
3. Keep it strictly to 1 short line (max 5-10 words). Real humans don't type long paragraphs.
4. Don't use perfect grammar or capital letters unnecessarily. Type like a normal lazy teenager (e.g., "hmm", "ok", "kya?").
5. NEVER repeat the same sentence. Think and give a fresh, natural reply every time.
6. If they ask for a group or channel link, share: {GROUP_LINK}"""

    history = chat_histories[chat_id]
    history.append({"role": "user", "content": f"{sender_name}: {user_text}"})

    # Puraane 10 messages yaad rakhega, usse zyada delete kar dega taaki load na pade
    if len(history) > 10:
        history.pop(0)

    messages = [{"role": "system", "content": system_prompt}] + list(history)

    try:
        # ====================================================
        # YAHAN NAYA MODEL UPDATE KIYA HAI JO KABHI BAND NAHI HOGA
        # ====================================================
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.9, # 0.9 matlab ekdum natural aur creative sochega
            max_tokens=50
        )
        if response.choices:
            reply_text = response.choices[0].message.content.strip()
            
            # Bot ka diya hua jawab bhi history me save karenge
            history.append({"role": "assistant", "content": reply_text})
            return reply_text
    except Exception as e:
        logging.error(f"Groq response generation error: {e}")

    # Agar kabhi Groq ki API fail hui toh ye backup line aayegi
    return "kya bol rha h yaar samajh nhi aara"

# ==========================================
# Pyrogram Client Start
# ==========================================
app = Client(
    name="group_human_userbot",
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

        # Typing action dikhane ke liye
        try:
            if not message.outgoing:
                client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        # Ek normal insaan ki tarah type karne me thoda time (1.5 se 3 seconds)
        time.sleep(random.uniform(1.5, 3.0))

        reply = get_ai_reply(chat_id, user_text, sender)
        if reply:
            message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Human Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

if __name__ == "__main__":
    logging.info("🚀 100% Real Human AI Userbot is Starting with New Model...")
    app.run()
