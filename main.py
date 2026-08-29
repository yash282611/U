import pyrogram.utils

# 1. ROOT ENGINE FIX: 14-Digit Channel IDs Patch
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MAX_CHAT_ID = -1
pyrogram.utils.MIN_USER_ID = 0
pyrogram.utils.MAX_USER_ID = 999999999999999

def patched_get_peer_type(peer_id: int) -> str:
    if str(peer_id).startswith("-100"):
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

import pyrogram.client
import pyrogram.raw.functions.updates as raw_update_funcs
import pyrogram.raw.types.updates as raw_updates
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid, RPCError

# Channel Crash Suppressor (GetChannelDifference Fix)
orig_invoke = pyrogram.client.Client.invoke

async def bulletproof_invoke(self, query, *args, **kwargs):
    try:
        return await orig_invoke(self, query, *args, **kwargs)
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        if isinstance(query, raw_update_funcs.GetChannelDifference):
            return raw_updates.ChannelDifferenceEmpty(flags=0, final=True, pts=getattr(query, "pts", 0), timeout=0)
        return None
    except RPCError as e:
        if any(err in str(e) for err in ["CHANNEL_INVALID", "PEER_ID_INVALID", "CHANNEL_PRIVATE"]):
            if isinstance(query, raw_update_funcs.GetChannelDifference):
                return raw_updates.ChannelDifferenceEmpty(flags=0, final=True, pts=getattr(query, "pts", 0), timeout=0)
            return None
        raise e

pyrogram.client.Client.invoke = bulletproof_invoke

# 2. Main Bot Setup
import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
import google.generativeai as genai
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType

# Direct Config Import
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_KEY = str(GEMINI_API_KEY).strip()
MODELS_LIST = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]

# Gemini SDK Setup
ai_model = None
try:
    genai.configure(api_key=API_KEY)
    ai_model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    logging.warning(f"SDK init note: {e}")

# Pure Dynamic Human AI Generator
def get_natural_ai_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_type = "Telegram Group chat" if is_group else "1-on-1 private chat"

    prompt = (
        f"You are a young, cool Indian guy chatting casually on Telegram in a {chat_type}.\n"
        f"Strict Guidelines:\n"
        f"1. Reply strictly in 100% natural, casual everyday conversational Hinglish (Hindi written in English alphabets).\n"
        f"2. Act like a real human friend typing fast on mobile (words to use: haan, bhai, yaar, arey, mast, sahi hai, bilkul, tu bata, abhi, bol).\n"
        f"3. Directly answer the question contextually:\n"
        f"   - If asked food ('khana khya', 'lunch', 'dinner') -> say you just ate or ask them (e.g. 'haan bhai bas abhi khaya, tune khaya kya?')\n"
        f"   - If asked activity ('kkrh', 'kya kr rha h') -> say you're chilling (e.g. 'kuch nahi bhai bas phone chala raha hu, tu bata kya scene?')\n"
        f"   - If asked location ('kidar h', 'kahan ho') -> say at home (e.g. 'ghar pe hi hu bhai, bol kya plan hai?')\n"
        f"   - If greetings ('hi', 'hello', 'yoo', 'heyy', 'oye') -> friendly casual reply (e.g. 'aur bhai kya haal chaal?')\n"
        f"   - Any questions or casual talk -> reply smartly like a real friend.\n"
        f"4. Strictly 1 short, crisp sentence (never write long paragraphs).\n"
        f"5. NEVER repeat previous lines verbatim.\n"
        f"6. NEVER mention being an AI, bot, or assistant.\n"
        f"7. Only share this link if user specifically asks for group/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) says: \"{user_text}\"\n"
        f"Your fast Hinglish reply:"
    )

    # 1. Try SDK Call
    if ai_model:
        try:
            res = ai_model.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    # 2. Try REST API
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 70}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in MODELS_LIST:
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

    # 3. Dynamic Multi-Variant Fallbacks (Zero Repetition)
    low = user_text.lower().strip()
    if any(k in low for k in ["khana", "lunch", "dinner"]):
        return random.choice([
            "Haan bhai bas abhi khaya, tune khaya kya?",
            "Haan yaar ho gaya lunch, tu bata tera hua?",
            "Abhi nahi bhai, thodi der me khaunga. Tu bata?"
        ])
    elif any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
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
    elif any(k in low for k in ["hi", "hello", "oye", "yoo", "heyy", "mieew"]):
        return random.choice([
            "Aur bhai, kya haal chaal!",
            "Haan bhai bol, kya chal raha hai?",
            "Yo bhai! Sab badhiya?",
            "Haan bhai, bol kya scene hai?"
        ])

    return random.choice([
        "Haan bhai, bol kya chal raha hai?",
        "Sahi hai bhai, tu bata kya scene hai?",
        "Haan bhai bol, sun raha hu!"
    ])

# 3. Telegram Client Setup
app = Client(
    "group_human_userbot",
    api_id=int(API_ID),
    api_hash=str(API_HASH),
    session_string=str(SESSION_STRING)
)

STICKER_MEMORY = []

# Unified Message Dispatcher (DMs + ALL Groups)
@app.on_message(~filters.me)
async def message_dispatcher(client: Client, message: Message):
    try:
        # Bots ke messages ignore karein
        if message.from_user and message.from_user.is_bot:
            return

        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_title = message.chat.title if is_group else sender

        # STICKER MESSAGE
        if message.sticker:
            if message.sticker.file_id:
                STICKER_MEMORY.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker from [{sender}] in [{chat_title}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(0.8, 1.4))
            chosen = random.choice(STICKER_MEMORY) if STICKER_MEMORY else message.sticker.file_id
            await message.reply_sticker(sticker=chosen, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
            return

        # TEXT MESSAGE
        if message.text:
            user_text = message.text
            logging.info(f"📩 [{chat_title}] {sender}: {user_text}")

            try:
                if not is_group:
                    await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.6))
            reply = await asyncio.to_thread(get_natural_ai_reply, user_text, sender, is_group)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ AI Replied to [{sender}] in [{chat_label if 'chat_label' in locals() else chat_title}]: {reply}")

    except Exception as err:
        logging.error(f"Message Handler Error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE 24/7 for DM + ALL Groups!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
