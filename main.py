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

# Direct Clean Import from config.py
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1. Gemini AI Dual Engine (SDK + REST Fallback)
API_KEY = str(GEMINI_API_KEY).strip()
MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]

# Configure SDK
try:
    genai.configure(api_key=API_KEY)
    ai_model = genai.GenerativeModel("gemini-2.5-flash")
except Exception:
    ai_model = None

def get_natural_ai_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_type = "Telegram Group chat" if is_group else "private 1-on-1 DM chat"
    
    prompt = (
        f"You are a young, cool Indian guy chatting casually on Telegram in a {chat_type}.\n"
        f"Strict Rules for replying:\n"
        f"1. Reply strictly in 100% natural conversational everyday Hinglish (Hindi written in English alphabets).\n"
        f"2. Act like a real human friend typing fast on a phone (use words like: haan, bhai, yaar, arey, mast, sahi hai, bilkul, tu bata).\n"
        f"3. Directly answer whatever the friend asked contextually:\n"
        f"   - 'khana khya' / 'khana khaya' -> haan bhai bas abhi khaya, tune khaya kya?\n"
        f"   - 'kkrh' / 'kya kr rha h' -> kuch nahi bhai bas aese hi baitha hu, tu bata kya scene?\n"
        f"   - 'kidar h' / 'kahan ho' -> ghar pe hi hu bhai, bol kya plan hai?\n"
        f"   - 'hi' / 'hello' / 'yoo' / 'heyy' / 'oye' -> aur bhai, kya haal chaal?\n"
        f"   - Any questions or fun banter -> reply smartly and naturally like a real friend.\n"
        f"4. Strictly 1 short, crisp sentence (never long paragraphs).\n"
        f"5. Never say you are an AI, bot, or assistant.\n"
        f"6. Only share this link if user specifically asks for group/link: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) says: \"{user_text}\"\n"
        f"Your fast Hinglish reply:"
    )

    # Method 1: Google GenAI SDK
    if ai_model:
        try:
            res = ai_model.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    # Method 2: High-Speed Direct REST API
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 70}
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

    # Method 3: Dynamic Multi-Variant Fallbacks (Zero Repetition)
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
            "Haan bhai, sun raha hu bol!"
        ])

    return random.choice([
        "Haan bhai, bol kya chal raha hai?",
        "Sahi hai bhai, tu bata kya scene hai?",
        "Haan bhai bol, sun raha hu!"
    ])

# 2. Telegram Userbot Setup
app = Client(
    "group_human_userbot",
    api_id=int(API_ID),
    api_hash=str(API_HASH),
    session_string=str(SESSION_STRING)
)

STICKER_CACHE = []

# 3. Unified Message Dispatcher (DMs + ALL Groups)
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def handle_all_messages(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_label = message.chat.title if is_group else sender

        # A. STICKER REPLY
        if message.sticker:
            if message.sticker.file_id:
                STICKER_CACHE.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}] in [{chat_label}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(0.8, 1.4))
            send_sticker = random.choice(STICKER_CACHE) if STICKER_CACHE else message.sticker.file_id
            await message.reply_sticker(sticker=send_sticker, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}] in [{chat_label}]")
            return

        # B. TEXT AI REPLY
        if message.text:
            user_text = message.text
            logging.info(f"📩 [{chat_label}] {sender}: {user_text}")

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
                logging.info(f"✅ AI Replied to [{sender}] in [{chat_label}]: {reply}")

    except Exception as err:
        logging.error(f"Message Processing Error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE & Ready for DM + ALL Groups 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
