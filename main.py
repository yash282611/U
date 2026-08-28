import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw.functions.messages import GetAllStickers
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Active Model Setup
genai.configure(api_key=GEMINI_API_KEY)

def connect_best_model():
    priority_models = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest"
    ]
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in priority_models:
            for full_name in all_models:
                if target in full_name:
                    try:
                        m = genai.GenerativeModel(full_name)
                        m.generate_content("hi")
                        logging.info(f"🎯 AI Model Connected: {full_name}")
                        return m
                    except Exception:
                        continue
    except Exception as e:
        logging.error(f"Model error: {e}")
    return genai.GenerativeModel("gemini-3.6-flash")

active_ai = connect_best_model()

# 2. 100% Dynamic Human AI Reply Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, real Indian friend chatting casually on Telegram in natural Hinglish.

Guidelines:
1. Speak in natural everyday casual Hinglish (short, friendly, real human tone).
2. Understand slang/short-words (e.g. 'gf h teri', 'kidar gya', 'hu', 'kkrh', 'kaisa h', 'thik hb', 'oye', 'hh', 'vhv').
3. Keep answers to 1 short sentence.
4. NEVER repeat canned lines.
5. NEVER mention being an AI or bot.
6. If the user asks for a group, channel, or link, share: {GROUP_LINK}

Friend ({sender_name}): "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI response error: {e}")

    return "Haan bhai, sun raha hu bol!"

# 3. Pyrogram Client & User Account Stickers Sync
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

ACCOUNT_STICKERS = []

async def sync_account_stickers():
    global ACCOUNT_STICKERS
    try:
        # User account me add kiye hue sticker sets load karega
        result = await app.invoke(GetAllStickers(hash=0))
        if hasattr(result, "sets"):
            for s_set in result.sets:
                short_name = getattr(s_set, "short_name", None)
                if short_name:
                    try:
                        set_data = await app.get_sticker_set(short_name)
                        for s in set_data.stickers:
                            ACCOUNT_STICKERS.append(s.file_id)
                    except Exception:
                        continue
    except Exception as e:
        logging.warning(f"Account stickers sync notice: {e}")

    # Fallback agar account me 0 saved stickers ho
    if not ACCOUNT_STICKERS:
        for backup_pack in ["AnimatedDog", "HotCherry", "Animals"]:
            try:
                st_set = await app.get_sticker_set(backup_pack)
                for s in st_set.stickers:
                    ACCOUNT_STICKERS.append(s.file_id)
            except Exception:
                continue

    logging.info(f"🎨 Total {len(ACCOUNT_STICKERS)} Stickers loaded from your account!")

# Text Messages Handler
@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def handle_text(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Text [{sender}]: {user_text}")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.8))

        reply = await asyncio.to_thread(get_ai_reply, user_text, sender)
        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Messages Handler (Aapke ID ke Stickers se Reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def handle_sticker(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    # Har incoming sticker ko cache me save karega
    if message.sticker and message.sticker.file_id:
        ACCOUNT_STICKERS.append(message.sticker.file_id)

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.6))

        if ACCOUNT_STICKERS:
            chosen_sticker = random.choice(ACCOUNT_STICKERS)
            await message.reply_sticker(sticker=chosen_sticker, quote=True)
            logging.info(f"✅ Sent Account Sticker to [{sender}]")
        else:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)

    except Exception as e:
        logging.error(f"Sticker error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs aur Account Stickers sync ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=25):
            pass
    except Exception:
        pass

    await sync_account_stickers()
    logging.info("🚀 AI Userbot is LIVE & Ready 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
