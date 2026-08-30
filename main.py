import time
import random
import logging
import re
import pyrogram.utils
import pyrogram.client
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerEmpty
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from openai import OpenAI
from collections import defaultdict

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
# MULTI-KEY SETUP
# ==========================================
raw_keys = str(GROQ_API_KEY).replace("\n", "").split(",")
api_keys_list = [k.strip() for k in raw_keys if len(k.strip()) > 10]
groq_clients = []

for key in api_keys_list:
    try:
        groq_clients.append(OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1"))
    except Exception:
        pass

logging.info(f"🎯 Total {len(groq_clients)} Working API Keys Loaded Successfully!")

# ==========================================
# Chat History Memory 
# ==========================================
chat_histories = defaultdict(list)

def get_ai_reply(chat_id: int, user_text: str, sender_name: str) -> str:
    system_prompt = f"""You are a close 19-year-old Indian guy chatting with your friend on Telegram in everyday Hinglish.
Reply directly, naturally, and contextually. If asked for a shayari, give a 2-line shayari.
Keep replies short (5-15 words). Never output usernames, prefixes, rules, or reasoning steps."""

    history = chat_histories[chat_id]
    history.append({"role": "user", "content": user_text})

    if len(history) > 8:
        history.pop(0)

    messages = [{"role": "system", "content": system_prompt}] + list(history)
    
    # Active Models List
    available_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-3b-preview"
    ]

    if not groq_clients:
        return "Bhai railway me API keys theek se nahi dali."

    # Har client aur model ko check karega
    for client in groq_clients:
        for model_name in available_models:
            try:
                response = client.chat.completions.create(
                    model=model_name, 
                    messages=messages,
                    temperature=0.8, 
                    max_tokens=70
                )
                
                if response.choices:
                    reply_text = response.choices[0].message.content.strip()
                    
                    # Cleanup reasoning or prefix leaks
                    reply_text = re.sub(r'<think>.*?</think>', '', reply_text, flags=re.DOTALL).strip()
                    reply_text = re.sub(r'^(Bot|User|Shinchan|Dost):\s*', '', reply_text, flags=re.IGNORECASE).strip()
                    reply_text = reply_text.replace('"', '').replace("'", "")

                    if reply_text:
                        history.append({"role": "assistant", "content": reply_text})
                        return reply_text
                        
            except Exception as e:
                logging.warning(f"Key/Model combination failed: {e}")
                continue

    return "bhai abhi network issue hai, 2 min baad try kar"

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
        chat_id = message.chat.id

        try:
            if not message.outgoing:
                client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.2, 2.5))

        reply = get_ai_reply(chat_id, message.text, sender)
        if reply:
            message.reply_text(text=reply, quote=True, disable_web_page_preview=True)

    except Exception as e:
        logging.error(f"Text error: {e}")

if __name__ == "__main__":
    app.run()
