import time
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Setup (Direct Active Model)
genai.configure(api_key=GEMINI_API_KEY)

working_model = None
try:
    available = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    logging.info(f"Available AI Models: {available}")
    
    # Priority: Connect to confirmed active model
    priority_list = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-pro-latest"]
    for p in priority_list:
        if p in available:
            try:
                m = genai.GenerativeModel(p)
                m.generate_content("test")
                working_model = m
                logging.info(f"🎯 Connected 100% to Active Model: {p}")
                break
            except Exception:
                continue
except Exception as e:
    logging.error(f"Model selection error: {e}")

if not working_model:
    working_model = genai.GenerativeModel("gemini-2.5-flash")

# 2. Dynamic Human AI Reply Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool Indian guy chatting with a friend on Telegram.
Reply in 100% natural, everyday casual Hinglish (Hindi written in English alphabets).

Chat Rules:
1. Understand chat short-forms and context:
   - "kkrh" / "kya kr rha h" -> tell what you are doing (e.g. 'kuch nahi bhai bas aese hi baitha tha, tu bata?')
   - "kidar h" -> tell where you are (e.g. 'ghar pe hi hu bhai, tu kidhar hai?')
   - "kaisa h" -> reply how you are (e.g. 'ekdum mast bhai, tu suna kaisa hai?')
   - "kya huau" / "kya hua" -> ask back (e.g. 'kuch nahi hua bhai sab badhiya, tu bata?')
   - "yoo" / "hi" / "oye" -> casual hello (e.g. 'aur bhai kaisa hai?')
2. Keep replies very short (1-2 lines max).
3. NEVER repeat the same answer for different questions.
4. NEVER say you are an AI or bot.
5. If someone asks for group/link, share: {GROUP_LINK}

Friend ({sender_name}) sent: "{user_text}"
Your Hinglish reply:"""

    try:
        res = working_model.generate_content(prompt)
        if res and res.text:
            return res.text.strip()
    except Exception as e:
        logging.error(f"AI Generation Error: {e}")

    # Smart Contextual Backup (Different for every question)
    text_low = user_text.lower().strip()
    if any(w in text_low for w in ["kkrh", "kya kr rha", "kya kar raha"]):
        return random.choice(["Kuch nahi bhai, bas phone chala raha hu. Tu bata?", "Aese hi baitha hu yaar, tu kya kar raha?"])
    elif any(w in text_low for w in ["kidar", "kahan"]):
        return random.choice(["Ghar pe hi hu bhai, bol kya plan?", "Room pe hu yaar, tu kidhar hai?"])
    elif any(w in text_low for w in ["kaisa", "kaisi", "haal"]):
        return random.choice(["Ekdam bindass bhai! Tu suna?", "Sab badhiya yaar, tu bata kaisa hai?"])
    elif any(w in text_low for w in ["kya hua", "kya huau"]):
        return random.choice(["Kuch nahi bhai sab mast hai, tu bol?", "Sab theek hai yaar, kya hua bata?"])
    elif any(w in text_low for w in ["hi", "hii", "hello", "oye", "yoo"]):
        return random.choice(["Aur bhai kaisa hai?", "Haan bol bhai kya scene?"])
    
    return "Haan bhai, sun raha hu bol!"

STICKERS = [
    "CAACAgIAAxkBAAEK1eBlvK9-h3V1Lh6DkgABw1b4a3kAAj0AA8G2wQgYjGfXW3wFHgQ",
    "CAACAgIAAxkBAAEK1eJlvK-KzP6b2hM4g9_ySgABG3kAAl0AA8G2wQjK_HwXlB0BHgQ",
    "CAACAgIAAxkBAAEK1eRlvK-W6Z4zQ4YxKjZtL-UAAkcAA8G2wQirF03mGgW5HgQ"
]

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Text Handler
@app.on_message(filters.text & ~filters.me & ~filters.bot)
def on_text(client: Client, message: Message):
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
        reply_text = get_ai_reply(user_text, sender)

        message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

    except Exception as err:
        logging.error(f"Text send error: {err}")

# Sticker Handler
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
def on_sticker(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    logging.info(f"🎨 Sticker Aaya from [{sender}]")

    try:
        try:
            client.read_chat_history(chat_id)
            client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        time.sleep(random.uniform(1.0, 1.6))
        message.reply_sticker(sticker=random.choice(STICKERS), quote=True)
        logging.info(f"✅ Replied Sticker to [{sender}]")

    except Exception as err:
        logging.error(f"Sticker send error: {err}")

if __name__ == "__main__":
    logging.info("🚀 AI Bot is LIVE...")
    app.run()
