import time
import random
import logging
import os
import re
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
    system_prompt = f"""You are a real 19-year-old Indian guy chatting with your close friend on Telegram. 
You MUST act exactly like a normal human being. NEVER act like an AI, bot, or assistant.

Strict Rules for chatting:
1. Talk in casual everyday Hinglish (e.g., 'haan bhai', 'kya scene hai', 'kuch nahi yaar', 'tu bata').
2. Read the context and reply DIRECTLY to what the user just said. 
3. Keep it strictly to 1 short line (max 5-10 words). Real humans don't type long paragraphs.
4. NEVER repeat the same sentence. Think and give a fresh, natural reply every time.
5. CRITICAL: ONLY output the exact reply text. DO NOT output the speaker's name or any prefixes (Do not write '{sender_name}:' or 'Bot:'). Just give the answer.

If they ask for a group or channel link, share: {GROUP_LINK}"""

    history = chat_histories[chat_id]
    history.append({"role": "user", "content": f"{sender_name}: {user_text}"})

    if len(history) > 10:
        history.pop(0)

    messages = [{"role": "system", "content": system_prompt}] + list(history)

    try:
        # 1. API se models ki list nikaalo
        available_models = [m.id for m in groq_client.models.list().data]
        
        # 2. VIP LIST (Sirf wo models jo actual mein chatting ke liye best hain)
        priority_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "gemma2-9b-it"
        ]
        
        # 3. List mein se jo sabse pehla VIP model zinda mile, use utha lo
        target_model = None
        for pm in priority_models:
            if pm in available_models:
                target_model = pm
                break
        
        # Agar VIP list fail ho jaye, toh koi aur text model dhoondo par Llama-Guard / Deepseek bilkul mat uthao
        if not target_model:
            for m in available_models:
                m_lower = m.lower()
                if ("llama" in m_lower or "gemma" in m_lower or "mixtral" in m_lower) and \
                   "guard" not in m_lower and "vision" not in m_lower and "deepseek" not in m_lower and "r1" not in m_lower:
                    target_model = m
                    break

        if not target_model:
            return "Bhai Groq par koi chatting model zinda nahi hai."

        # Model chalana shuru karo
        response = groq_client.chat.completions.create(
            model=target_model, 
            messages=messages,
            temperature=0.8, 
            max_tokens=50
        )
        
        if response.choices:
            reply_text = response.choices[0].message.content.strip()
            
            # FINAL CLEANUP (Filters)
            reply_text = re.sub(r'<think>.*?</think>', '', reply_text, flags=re.DOTALL).strip()
            
            # Agar AI ne galti se saamne wale ka naam (SHINchan) chipka diya ho, toh use delete karo
            if sender_name in reply_text:
                reply_text = reply_text.replace(sender_name, "").replace(":", "").strip()
            if "Bot:" in reply_text or "User:" in reply_text:
                reply_text = reply_text.replace("Bot:", "").replace("User:", "").strip()
                
            reply_text = reply_text.replace('"', '').replace("'", "")

            # Agar naam delete karne ke baad message bilkul khali ho jaye (Fallback)
            if not reply_text or len(reply_text) < 2:
                fallbacks = ["haan bhai bol", "kya keh raha hai?", "hmm", "sahi hai"]
                reply_text = random.choice(fallbacks)

            history.append({"role": "assistant", "content": reply_text})
            return reply_text
            
        return "kya bol rha h yaar samajh nhi aara"
        
    except Exception as e:
        logging.error(f"Groq API error: {e}")
        return f"Bhai AI me error aa raha hai: {e}"

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

        try:
            if not message.outgoing:
                client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.5, 3.0))

        reply = get_ai_reply(chat_id, user_text, sender)
        if reply:
            message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Human Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

if __name__ == "__main__":
    logging.info("🚀 100% Real Human AI Userbot is Starting with VIP Models...")
    app.run()
