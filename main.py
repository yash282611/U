import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType

# Direct Clean Import from config.py
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

API_KEY = str(GEMINI_API_KEY).strip()
MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]

# 1. Pure Fast REST AI Engine (DM + Group Friendly)
def generate_ai_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    context = "in a Telegram Group chat" if is_group else "in a private 1-on-1 chat"

    prompt_text = (
        f"You are a young, cool Indian guy chatting casually on Telegram {context}.\n"
        f"Rules:\n"
        f"1. Reply strictly in 100% natural conversational everyday Hinglish (Hindi written in English alphabets).\n"
        f"2. Reply naturally to the exact message:\n"
        f"   - 'khana khya' / 'khana khaya' -> haan bhai bas abhi khaya, tune khaya kya?\n"
        f"   - 'kkrh' / 'kya kr rha h' -> kuch nahi bhai bas chill kar raha hu, tu bata kya scene?\n"
        f"   - 'kidar h' / 'kahan ho' -> ghar pe hi hu bhai, bol kya plan hai?\n"
        f"   - 'hi' / 'hello' / 'yoo' / 'oye' / 'mieew' -> aur bhai, kya haal chaal?\n"
        f"   - Any banter or questions -> reply smartly and naturally like a real close friend.\n"
        f"3. Strictly 1 short, crisp sentence (never long paragraphs).\n"
        f"4. Never say you are an AI or bot.\n"
        f"5. Only share this link if user asks for group/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) says: \"{user_text}\"\n"
        f"Reply:"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 60}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in MODELS:
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

    # Instant Contextual Fallback agar internet drop ho
    low = user_text.lower().strip()
    if any(k in low for k in ["khana", "lunch", "dinner"]):
        return "Haan bhai bas abhi khaya, tune khana khaya kya?"
    elif any(k in low for k in ["kkrh", "kya kr", "kya kar"]):
        return "Kuch nahi bhai bas phone chala raha tha, tu bata kya chal raha?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya baat hui?"
    elif any(k in low for k in ["gf", "bandi"]):
        return "Nahi bhai, apan single hi mast hain!"
    elif any(k in low for k in ["hi", "hello", "oye", "yoo", "heyy", "mieew"]):
        return "Aur bhai, kya haal chaal!"

    return "Haan bhai bol, sun raha hu!"

# 2. Telegram Client Setup
app = Client(
    "group_human_userbot",
    api_id=int(API_ID),
    api_hash=str(API_HASH),
    session_string=str(SESSION_STRING)
)

STICKER_VAULT = []

# Unified Handler for DM + Groups
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def message_dispatcher(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_title = message.chat.title if is_group else sender

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
                if not is_group:
                    await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.6))
            reply = await asyncio.to_thread(generate_ai_reply, user_text, sender, is_group)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ AI Replied to [{sender}] in [{chat_title}]: {reply}")

    except Exception as err:
        logging.error(f"Handler error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is 100% LIVE for DM + All Groups (Direct Config)!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
