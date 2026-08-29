# 1. ROOT LEVEL FIX: 64-Bit IDs & Unbreakable Update Loop
import pyrogram.utils
import pyrogram.client
import pyrogram.methods.advanced.resolve_peer
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerEmpty
import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
from pyrogram import Client, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MAX_CHAT_ID = -1
pyrogram.utils.MIN_USER_ID = 0
pyrogram.utils.MAX_USER_ID = 999999999999999

def patched_get_peer_type(peer_id: int) -> str:
    s = str(peer_id)
    if s.startswith("-100"):
        return "channel"
    elif peer_id < 0:
        return "chat"
    return "user"

def patched_get_channel_id(peer_id: int) -> int:
    s = str(peer_id)
    if s.startswith("-100"):
        return peer_id
    return int(f"-100{peer_id}")

pyrogram.utils.get_peer_type = patched_get_peer_type
pyrogram.utils.get_channel_id = patched_get_channel_id
pyrogram.methods.advanced.resolve_peer.utils.get_peer_type = patched_get_peer_type
pyrogram.methods.advanced.resolve_peer.utils.get_channel_id = patched_get_channel_id

# Safe Peer Resolver
_orig_resolve_peer = pyrogram.client.Client.resolve_peer

async def safe_resolve_peer(self, peer_id):
    try:
        return await _orig_resolve_peer(self, peer_id)
    except Exception:
        if isinstance(peer_id, int):
            s = str(peer_id)
            if s.startswith("-100"):
                return InputPeerChannel(channel_id=int(s[4:]), access_hash=0)
            elif peer_id < 0:
                return InputPeerChat(chat_id=-peer_id)
            else:
                return InputPeerUser(user_id=peer_id, access_hash=0)
        return InputPeerEmpty()

pyrogram.client.Client.resolve_peer = safe_resolve_peer
pyrogram.Client.resolve_peer = safe_resolve_peer

# Safe Update Loop Handler (Task termination preventer)
_orig_handle_updates = pyrogram.client.Client.handle_updates

async def safe_handle_updates(self, updates):
    try:
        await _orig_handle_updates(self, updates)
    except Exception:
        pass

pyrogram.client.Client.handle_updates = safe_handle_updates
pyrogram.Client.handle_updates = safe_handle_updates

# 2. Main Bot Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_KEY = str(GEMINI_API_KEY).strip()
WORKING_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

# Fast Dynamic AI Generator (DM + Group Friendly)
def fetch_gemini_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_context = "in a Telegram Group chat" if is_group else "in a private 1-on-1 chat"

    prompt_text = (
        f"You are a young, cool Indian guy chatting casually {chat_context}.\n"
        f"Strict Rules for replying:\n"
        f"1. Reply strictly in 100% natural, casual conversational everyday Hinglish (Hindi written in English alphabets).\n"
        f"2. Act like a real human friend typing fast on mobile (words to use: haan, bhai, yaar, arey, mast, sahi hai, bilkul, tu bata, abhi, bol).\n"
        f"3. Directly answer what the friend said contextually:\n"
        f"   - If greetings ('hi', 'hello', 'oye', 'yoo', 'heyy', 'hu', 'uhii', 'hpo', 'h8', 'hii'): friendly casual reply (e.g. 'aur bhai kya chal raha hai?', 'haan bhai bol kya haal?')\n"
        f"   - If food ('khana khya', 'lunch', 'dinner'): natural reply (e.g. 'haan bhai bas abhi khaya, tune khaya kya?', 'abhi nahi yaar thodi der me khaunga')\n"
        f"   - If activity ('kkrh', 'krh', 'kya kar raha hai'): natural reply (e.g. 'kuch nahi bhai bas phone chala raha hu, tu bata kya scene?')\n"
        f"   - If location ('kidhar hai', 'kahan ho'): natural reply (e.g. 'ghar pe hi hu bhai, bol kya plan hai?')\n"
        f"   - Any jokes, slang, gibberish or chat: reply with natural, fun friend-like banter.\n"
        f"4. Strictly 1 short, crisp sentence (never write long paragraphs).\n"
        f"5. Never say you are an AI or bot.\n"
        f"6. Only share this link if user specifically asks for group/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) said: \"{user_text}\"\n"
        f"Your quick Hinglish reply:"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 60}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in WORKING_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.5) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            continue

    # Multi-Variant Fallbacks (Zero Repetition)
    low = user_text.lower().strip()
    if any(k in low for k in ["khana", "lunch", "dinner"]):
        return random.choice([
            "Haan bhai bas abhi khaya, tune khaya kya?",
            "Haan yaar ho gaya lunch, tu bata tera hua?",
            "Abhi nahi bhai, thodi der me khaunga. Tu bata?"
        ])
    elif any(k in low for k in ["kkrh", "krh", "kya kr", "kya kar"]):
        return random.choice([
            "Kuch nahi bhai, bas phone chala raha hu. Tu bata kya scene?",
            "Bas chill kar raha hu yaar, tu bata kya chal raha?",
            "Kuch khas nahi bhai, aese hi baitha hu. Bol kya scene?"
        ])
    elif any(k in low for k in ["kidar", "kahan", "kidhar"]):
        return random.choice([
            "Ghar pe hi hu bhai, bol kya plan hai?",
            "Room pe hi hu yaar, bol kya baat?",
            "Ghar pe hi hu, bol kuch kaam tha kya?"
        ])
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi bindass hain!"
    elif any(k in low for k in ["hi", "hello", "oye", "yoo", "heyy", "hu", "uhii", "hpo", "h8", "hii"]):
        return random.choice([
            "Aur bhai, kya haal chaal!",
            "Haan bhai bol, kya chal raha hai?",
            "Yo bhai! Sab badhiya?",
            "Haan bhai, bol kya scene hai?"
        ])

    return random.choice([
        "Haan bhai, bol kya chal raha hai?",
        "Sahi hai bhai, tu bata kya scene?",
        "Haan bhai bol, sun raha hu!"
    ])

# 3. Telegram Client Setup
app = Client(
    "group_human_userbot",
    api_id=int(API_ID),
    api_hash=str(API_HASH),
    session_string=str(SESSION_STRING)
)

STICKER_VAULT = []

# Universal Clean Message Listener
@app.on_message()
async def universal_dispatcher(client: Client, message: Message):
    try:
        if not message:
            return
            
        # ⚠️ YAHAN DHYAN DE: Ye code tumhare khud ke bheje hue messages ko ignore karta hai
        # Taaki infinite spam loop na bane. Isliye testing ke liye dusre account se message bhejna padega.
        if message.outgoing:
            return
            
        # Ye bots aur khud ko ignore karne ke liye hai
        if message.from_user and (message.from_user.is_self or message.from_user.is_bot):
            return

        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_title = message.chat.title if is_group else sender

        # Instant Double-Tick (Mark as Read)
        try:
            await client.read_chat_history(chat_id)
        except Exception:
            pass

        # 1. STICKER MESSAGE
        if message.sticker:
            if message.sticker.file_id:
                STICKER_VAULT.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker from [{sender}] in [{chat_title}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(0.8, 1.4))
            chosen = random.choice(STICKER_VAULT) if STICKER_VAULT else message.sticker.file_id
            await message.reply_sticker(sticker=chosen, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
            return

        # 2. TEXT MESSAGE
        if message.text:
            user_text = message.text
            logging.info(f"📩 [{chat_title}] {sender}: {user_text}")

            try:
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.6))
            reply = await asyncio.to_thread(fetch_gemini_reply, user_text, sender, is_group)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ AI Replied to [{sender}] in [{chat_title}]: {reply}")

    except Exception as err:
        logging.error(f"Handler execution error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE 24/7 for DM + ALL Groups!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
