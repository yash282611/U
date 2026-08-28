import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Active Model Auto-Connect
genai.configure(api_key=GEMINI_API_KEY)

def connect_best_model():
    priority_models = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash"
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
        logging.error(f"Model selection error: {e}")
    return genai.GenerativeModel("gemini-3.6-flash")

active_ai = connect_best_model()

# 2. Pure Dynamic AI Reply Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, casual Indian friend chatting on Telegram. Reply like an authentic real human in natural everyday Hinglish (Hindi words written in English alphabet).

Chat Guidelines:
1. Always understand chat short-forms & slang (e.g. 'kkrh' -> kya kar rahe ho, 'kidar h' -> kahan ho, 'kaisa h' -> kaisa hai, 'yo', 'oye', 'hmm').
2. Reply strictly based on what the user said in 1 short line.
3. NEVER repeat canned lines.
4. NEVER say you are an AI or bot.
5. If the user asks for a group, channel, or link, share: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI response error: {e}")
    return ""

# 3. Pyrogram Client & Live Sticker Pack Loader
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_CACHE = []

async def load_sticker_packs():
    popular_packs = ["Memes", "Animals", "AnimatedDog", "HotCherry", "DuckFlock"]
    for pack in popular_packs:
        try:
            st_set = await app.get_sticker_set(pack)
            for s in st_set.stickers:
                STICKER_CACHE.append(s.file_id)
        except Exception:
            continue
    logging.info(f"🎨 Total {len(STICKER_CACHE)} Stickers loaded successfully!")

# Text Messages Handler (100% Dynamic AI)
@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def on_text_message(client: Client, message: Message):
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

        await asyncio.sleep(random.uniform(1.2, 2.0))

        reply = await asyncio.to_thread(get_ai_reply, user_text, sender)
        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Messages Handler (100% Working Live Sticker Reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def on_sticker_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.8))

        if STICKER_CACHE:
            random_sticker = random.choice(STICKER_CACHE)
            await message.reply_sticker(sticker=random_sticker, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}]")
        else:
            # Fallback agar pack load na ho: same sticker reply
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)

    except Exception as e:
        logging.error(f"Sticker send error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs aur Sticker cache load ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=30):
            pass
    except Exception:
        pass

    await load_sticker_packs()
    logging.info("🚀 AI Human Bot is LIVE & Ready for Text + Stickers!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
