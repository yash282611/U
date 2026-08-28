import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw.functions.messages import GetAllStickers, GetFavedStickers, GetRecentStickers
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Setup
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

# 2. Dynamic AI Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, casual Indian friend chatting on Telegram. Reply like an authentic human in natural everyday Hinglish (Hindi written in English alphabets).

Rules:
1. Speak in natural everyday conversational Hinglish (short, friendly & snappy).
2. Understand slang and chat short-forms (e.g. 'gf h teri', 'kidar gya', 'kkrh', 'kaisa h', 'oye').
3. Keep answers to 1-2 short lines like a real mobile user typing.
4. NEVER repeat canned lines.
5. NEVER say you are an AI or bot.
6. If the user asks for group/link, share: {GROUP_LINK}

Friend ({sender_name}): "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI generation error: {e}")
    return ""

# 3. Pyrogram Client & Account Stickers Loader
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

ACCOUNT_STICKERS = []

async def load_my_account_stickers():
    global ACCOUNT_STICKERS
    loaded_count = 0

    # 1. User ID ke Installed Sticker Sets load karein
    try:
        all_sets = await app.invoke(GetAllStickers(hash=0))
        if hasattr(all_sets, "sets"):
            for s_cover in all_sets.sets:
                short_name = getattr(s_cover.set, "short_name", None) if hasattr(s_cover, "set") else getattr(s_cover, "short_name", None)
                if short_name:
                    try:
                        st_set = await app.get_sticker_set(short_name)
                        for s in st_set.stickers:
                            ACCOUNT_STICKERS.append(s.file_id)
                            loaded_count += 1
                    except Exception:
                        continue
    except Exception as e:
        logging.warning(f"Installed stickers load note: {e}")

    # 2. Account ke Favorite Stickers load karein
    try:
        favs = await app.invoke(GetFavedStickers(hash=0))
        if hasattr(favs, "stickers"):
            for doc in favs.stickers:
                # Raw document se file_id fetch
                pass
    except Exception:
        pass

    logging.info(f"🎨 Aapki Telegram ID ke Total {len(ACCOUNT_STICKERS)} Stickers load ho chuke hain!")

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

        await asyncio.sleep(random.uniform(1.2, 2.0))

        reply = await asyncio.wait_for(
            asyncio.to_thread(get_ai_reply, user_text, sender),
            timeout=8.0
        )

        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Messages Handler (Aapki ID ke stickers se reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def handle_sticker(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    # Naya aane wala sticker bhi list me add ho jayega
    if message.sticker and message.sticker.file_id:
        ACCOUNT_STICKERS.append(message.sticker.file_id)

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.8))

        if ACCOUNT_STICKERS:
            my_sticker = random.choice(ACCOUNT_STICKERS)
            await message.reply_sticker(sticker=my_sticker, quote=True)
            logging.info(f"✅ Sent Account Sticker to [{sender}]")
        else:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)

    except Exception as e:
        logging.error(f"Sticker send error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Account ke Stickers sync ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=25):
            pass
    except Exception:
        pass

    await load_my_account_stickers()
    logging.info("🚀 Userbot LIVE hai - Aapke khud ke Stickers active hain!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
