import pyrogram.utils
import pyrogram.client
import pyrogram.methods.advanced.resolve_peer
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerEmpty
import asyncio
import random
import logging
import json
import urllib.request
from pyrogram import Client, idle, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

# 1. ROOT LEVEL FIX: 64-Bit IDs & Unbreakable Update Loop
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

# 2. Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
API_KEY = str(GEMINI_API_KEY).strip()
WORKING_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

# AI Generator
def fetch_gemini_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_context = "in a Telegram Group chat" if is_group else "in a private 1-on-1 chat"
    prompt_text = (
        f"You are a young, cool Indian guy chatting casually {chat_context}.\n"
        f"Strict Rules:\n"
        f"1. Reply in 100% natural, casual Hinglish (Hindi in English font).\n"
        f"2. Act like a real human friend (use words: haan, bhai, yaar, sahi hai).\n"
        f"3. Strictly 1 short, crisp sentence.\n"
        f"4. Never say you are an AI.\n"
        f"Friend ({sender_name}) said: \"{user_text}\"\nYour reply:"
    )
    
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt_text}]}], "generationConfig": {"temperature": 0.85, "maxOutputTokens": 60}}
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in WORKING_MODELS:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}", data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4.0) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text: return text
        except Exception:
            continue
    return "Haan bhai, bol kya chal raha hai?"

app = Client("userbot", api_id=int(API_ID), api_hash=str(API_HASH), session_string=str(SESSION_STRING))

# 3. Message Handler (अब यह तुम्हारे खुद के मैसेज पर भी रिप्लाई करेगा!)
@app.on_message(filters.text & ~filters.bot)
async def universal_dispatcher(client: Client, message: Message):
    try:
        # अगर मैसेज के शुरू में 🤖 है, तो बोट इग्नोर करेगा (ताकि वो खुद को ही रिप्लाई करके इनफिनिट लूप ना बनाये)
        if message.text.startswith("🤖"):
            return

        # टेस्ट कमांड
        if message.text == ".test":
            await message.reply_text("✅ बोट एकदम मस्त चल रहा है!", quote=True)
            return

        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.5))
        reply = await asyncio.to_thread(fetch_gemini_reply, message.text, sender, is_group)

        if reply:
            # AI के रिप्लाई के आगे 🤖 लगा रहे हैं
            await message.reply_text(text=f"🤖 {reply}", quote=True, disable_web_page_preview=True)
            logging.info(f"AI Replied to {sender}: {reply}")

    except Exception as e:
        logging.error(f"Error: {e}")

async def main():
    await app.start()
    logging.info("🚀 Userbot is LIVE! (Now replies to your messages too)")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
