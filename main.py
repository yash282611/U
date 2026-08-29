import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1. Gemini AI REST Engine
API_KEY = str(GEMINI_API_KEY).strip()
WORKING_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a young, cool Indian friend chatting on Telegram in casual Hinglish.\n"
        f"Rules:\n"
        f"1. Reply in 1 short, natural sentence in conversational Hinglish.\n"
        f"2. Understand chat slang & gibberish (e.g. 'kkrh', 'kidar hoo', 'gf h teri', 'hi', 'heyy', 'yooo', 'nenjhhisbs', 'gi').\n"
        f"3. Never say you are an AI or bot.\n"
        f"4. If asked for link/group, share: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}): \"{user_text}\"\n"
        f"Reply:"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 60}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for m in WORKING_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.5) as response:
                res = json.loads(response.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            continue

    # Fallback replies agar API me thoda bhi delay ho
    low = user_text.lower().strip()
    if any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
        return "Kuch nahi bhai, bas baitha tha. Tu bata kya scene?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya plan hai?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi bindass hain!"
    elif any(k in low for k in ["hi", "hii", "hiii", "yoo", "heyy", "oye", "hey"]):
        return "Haan bhai, bol kya haal chaal!"
    
    return "Haan bhai bol, sun raha hu!"

# 2. Telegram Userbot Setup
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_VAULT = []

# 3. Main Message Handler (Private Chats & Groups)
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def incoming_handler(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id

        # STICKER MESSAGE
        if message.sticker:
            if message.sticker.file_id:
                STICKER_VAULT.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(0.8, 1.4))

            chosen_sticker = random.choice(STICKER_VAULT) if STICKER_VAULT else message.sticker.file_id
            await message.reply_sticker(sticker=chosen_sticker, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
            return

        # TEXT MESSAGE
        if message.text:
            user_text = message.text
            logging.info(f"📩 Naya Message [{sender}]: {user_text}")

            try:
                await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.6))
            reply = await asyncio.to_thread(get_ai_reply, user_text, sender)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as err:
        logging.error(f"Execution Error: {err}")

if __name__ == "__main__":
    logging.info("🚀 AI Userbot is Starting...")
    app.run()
