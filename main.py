import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw.functions.messages import GetFeaturedStickers
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Active Model Connection
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
        logging.error(f"Model error: {e}")
    return genai.GenerativeModel("gemini-3.6-flash")

active_ai = connect_best_model()

# 2. 100% Pure Dynamic AI Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a cool, real Indian guy chatting casually on Telegram with a friend. Reply like an authentic human in casual Hinglish (Hindi written in English alphabets).

Strict Rules:
1. Speak in natural everyday conversational Hinglish (short, friendly & snappy).
2. Understand slang and chat short-forms (e.g. 'gf h teri', 'kidar gya', 'hu', 'kkrh', 'kaisa h', 'oye').
3. Keep answers to 1-2 short lines like a real mobile user typing.
4. NEVER repeat the same lines. Reply specifically to what was asked.
5. NEVER mention being an AI or bot.
6. If the user asks for a group, channel, or link, share: {GROUP_LINK}

Friend ({sender_name}): "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI generation error: {e}")
    return ""

# 3. Pyrogram Client & Auto Featured Sticker Sync
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_CACHE = []

async def sync_featured_stickers():
    global STICKER_CACHE
    try:
        # Telegram ke live trending sticker sets load karega
        featured = await app.invoke(GetFeaturedStickers(hash=0))
        for set_cover in featured.sets:
            try:
                s_set = await app.get_sticker_set(set_cover.set.short_name)
                for st in s_set.stickers:
                    STICKER_CACHE.append(st.file_id)
                if len(STICKER_CACHE) >= 60:
                    break
            except Exception:
                continue
        logging.info(f"🎨 Successfully loaded {len(STICKER_CACHE)} Live Stickers into Cache!")
    except Exception as e:
        logging.warning(f"Featured stickers load warning: {e}")

# Text Message Handler
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

        reply = await asyncio.wait_for(
            asyncio.to_thread(get_ai_reply, user_text, sender),
            timeout=8.0
        )

        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text handling error: {e}")

# Sticker Message Handler (100% Guaranteed Working Sticker Reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def on_sticker_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    # Auto-save incoming sticker to cache
    if message.sticker and message.sticker.file_id:
        STICKER_CACHE.append(message.sticker.file_id)

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
            logging.info(f"✅ Sent Sticker Reply to [{sender}]")
        else:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)

    except Exception as e:
        logging.error(f"Sticker reply error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs aur Live Stickers load ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=25):
            pass
    except Exception:
        pass

    await sync_featured_stickers()
    logging.info("🚀 AI Human Bot is LIVE & Ready for Text + Stickers!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
