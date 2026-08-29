import time
import random
import logging
import json
import urllib.request
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. AI Text Response Generator
def get_ai_response(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool Indian friend chatting on Telegram. Reply in 100% natural, casual Hinglish.

Rules:
1. Understand chat short-forms (kkrh, kaisa h, kidar h, mast, wrud, etc.).
2. Reply in 1 short, dynamic line like a real person typing on phone.
3. NEVER repeat fixed canned lines.
4. If asked for link/group, share: {GROUP_LINK}

User ({sender_name}) says: "{user_text}"
Your short Hinglish reply:"""

    active_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash"]

    for model_name in active_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.9, "maxOutputTokens": 70}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                reply = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if reply:
                    return reply
        except Exception:
            continue
    return ""

# Popular Telegram Stickers for direct sticker replies
STICKER_LIST = [
    "CAACAgIAAxkBAAEK1eBlvK9-h3V1Lh6DkgABw1b4a3kAAj0AA8G2wQgYjGfXW3wFHgQ",  # Thumbs up / Cool
    "CAACAgIAAxkBAAEK1eJlvK-KzP6b2hM4g9_ySgABG3kAAl0AA8G2wQjK_HwXlB0BHgQ",  # Laughing / Fun
    "CAACAgIAAxkBAAEK1eRlvK-W6Z4zQ4YxKjZtL-UAAkcAA8G2wQirF03mGgW5HgQ",      # Wink / Hi
    "CAACAgIAAxkBAAEK1eZlvK-f7uO0n8cQ5f7L3OQAAiEAA8G2wQjX_d8uT4QHHgQ"       # Namaste / Respect
]

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Handler 1: Jab koi TEXT message bheje
@app.on_message(filters.text & ~filters.me & ~filters.bot)
def handle_text_messages(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Text [{sender}]: {user_text}")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 1.8))
        reply_text = get_ai_response(user_text, sender)

        if reply_text:
            message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Text Replied to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Handler 2: Jab koi STICKER bheje
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
def handle_sticker_messages(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id
    sticker_emoji = message.sticker.emoji if message.sticker.emoji else "🙂"

    logging.info(f"🎨 Naya Sticker Aaya from [{sender}] with Emoji: {sticker_emoji}")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 2.0))

        # Random sticker reply ya contextual Hinglish response
        if random.random() < 0.6:
            # 60% chance: Palat kar dusra sticker bhejega
            random_sticker = random.choice(STICKER_LIST)
            message.reply_sticker(sticker=random_sticker, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
        else:
            # 40% chance: Sticker ke emoji ko samajh kar text me roast ya tareef karega
            ai_comment = get_ai_response(f"[Sent a sticker: {sticker_emoji}]", sender)
            if ai_comment:
                message.reply_text(text=ai_comment, quote=True)
                logging.info(f"✅ AI Replied to Sticker from [{sender}]: {ai_comment}")

    except Exception as e:
        logging.error(f"Sticker handler error: {e}")

if __name__ == "__main__":
    logging.info("🚀 AI Bot is LIVE & Ready for Text + Stickers!")
    app.run()
